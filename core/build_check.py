"""Проверка сборки целиком: проект как система, а не набор файлов.

Зачем это нужно
---------------
Раньше проверялся только синтаксис каждого файла: `compile()` на файл — и всё.
Такой проверке не видно главного: `app.py` импортирует `calculate` из
`calculator.py`, а функции там нет; `index.html` подключает `app.js`, которого
не существует; точка входа падает при импорте. Формально «синтаксис в порядке»,
а программа не работает.

Что проверяется
---------------
1. `syntax` — каждый .py компилируется;
2. `import` — каждый модуль импортируется по-настоящему, в отдельном процессе:
   ловится и отсутствующий файл, и отсутствующее имя в существующем файле;
3. `entry`  — есть ли точка входа и импортируется ли она;
4. `assets` — существуют ли файлы, на которые ссылается HTML;
5. `deps`   — хватает ли requirements.txt для внешних импортов;
6. `tests`  — проходят ли тесты (pytest), если они есть.

Важно про очередь подтверждений
-------------------------------
Агенты не пишут на диск: правка ложится в очередь «Подтверждения». Поэтому
проверка принимает `overlay` — предложенные, но ещё не подтверждённые файлы —
и работает с копией проекта, где эти файлы уже лежат. Проверяется то, что
человеку предлагают, а не только то, что он успел подтвердить.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Служебные папки: их содержимое — не сборка проекта.
SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "node_modules", "venv", ".venv", "venv_new", "env",
    "dist", "build", ".idea", ".vscode", ".cache", ".ai-team",
}
# Служебные файлы проекта: это не код сборки.
SKIP_FILES = {"_truth.json"}

# Порядок важен: первый существующий файл считается точкой входа.
ENTRY_CANDIDATES = (
    "main.py", "app.py", "run.py", "server.py", "manage.py", "wsgi.py",
    "src/main.py", "src/app.py", "app/main.py", "backend/main.py",
)

# Сколько модулей импортировать и сколько файлов копировать: сборка учебная,
# а проверка не должна занимать минуты.
MAX_MODULES = 200
MAX_FILES = 600
IMPORT_TIMEOUT = 60
TESTS_TIMEOUT = 120
PROMPT_LIMIT = 1600

_IMPORT_SCRIPT = r'''
import importlib, json, os, sys

payload = json.loads(sys.stdin.read() or "{}")
os.chdir(payload["root"])
sys.path[:0] = payload["roots"]

out = []
for item in payload["modules"]:
    errors = []
    imported = False
    for name in item["names"]:
        try:
            importlib.import_module(name)
            imported = True
            break
        except BaseException as exc:  # noqa: BLE001 — падение модуля и есть результат
            errors.append({
                "status": type(exc).__name__,
                "message": str(exc)[:300],
                "missing": getattr(exc, "name", "") or "",
                "name": name,
            })
    if imported:
        out.append({"file": item["file"], "status": "ok"})
    else:
        # Последняя попытка — имя как в файле, оно и понятнее человеку.
        last = errors[-1] if errors else {"status": "ImportError", "message": "не импортируется"}
        last["file"] = item["file"]
        out.append(last)
sys.stdout.write("\n<<<BUILD_CHECK>>>" + json.dumps(out, ensure_ascii=False))
'''

# pytest запускается обёрткой: в некоторых сборках Python текущая папка не
# попадает в sys.path, и тесты падают на «No module named» ещё до старта.
_PYTEST_SCRIPT = (
    "import os, sys; "
    "here = os.getcwd(); "
    "sys.path[:0] = [p for p in [here] + [os.path.join(here, d) for d in "
    "('src', 'app', 'backend')] if os.path.isdir(p)]; "
    "import pytest; "
    "raise SystemExit(pytest.main(sys.argv[1:]))"
)

_ASSET_RE = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


@dataclass
class Issue:
    """Одна находка проверки: где и что не так."""

    check: str          # syntax | import | entry | assets | deps
    severity: str       # error | warning
    message: str
    file: str = ""
    line: Optional[int] = None

    def text(self) -> str:
        if self.file and self.line:
            return f"{self.file}:{self.line} — {self.message}"
        if self.file:
            return f"{self.file} — {self.message}"
        return self.message


@dataclass
class BuildReport:
    """Итог проверки: файлы, находки, тесты, точка входа."""

    project_path: Path
    files: List[str] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)
    tests: Dict[str, Any] = field(default_factory=dict)
    # Публичные функции и классы проекта: без них Тестер гадает, что проверять.
    api: List[str] = field(default_factory=list)
    # Готовые строки импорта для тестов.
    import_lines: List[str] = field(default_factory=list)
    entry: str = ""
    pending_files: int = 0
    duration_ms: int = 0
    checked_at: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )

    @property
    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary(self, limit: int = 4) -> str:
        """Короткая строка для человека — без внутренних кодов."""
        return _summary(self, limit)

    def as_prompt_block(self) -> str:
        """Факты для Тестера: коротко, чтобы 8B-модель не утонула."""
        return _prompt_block(self)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "project": str(self.project_path),
            "files": len(self.files),
            "pending": self.pending_files,
            "entry": self.entry,
            "errors": [i.text() for i in self.errors][:20],
            "warnings": [i.text() for i in self.warnings][:20],
            # output_tail остаётся в отчёте для журнала, но не едет в интерфейс:
            # это сотни символов сырого вывода pytest с временными путями.
            "tests": {k: v for k, v in self.tests.items() if k != "output_tail"},
            "summary": self.summary(),
            "duration_ms": self.duration_ms,
            "checked_at": self.checked_at,
        }


class BuildCheck:
    """Проверка проекта целиком. `overlay` — предложенные, но не применённые файлы."""

    def __init__(
        self,
        project_path: Path,
        overlay: Optional[Dict[str, str]] = None,
        pending_files: int = 0,
    ) -> None:
        self.project_path = Path(project_path)
        self.overlay = dict(overlay or {})
        self.pending_files = pending_files
        self._temp_root: Optional[Path] = None
        self._work_root = self.project_path
        self._stems: set = set()

    # ── публичный вход ────────────────────────────────────────────────

    def run(self, run_tests: bool = True) -> BuildReport:
        started = time.monotonic()
        report = BuildReport(
            project_path=self.project_path, pending_files=self.pending_files
        )

        try:
            self._work_root = self._materialize()
            py_files = self._collect_python(report)
            if not report.files:
                report.issues.append(
                    Issue("files", "error", "в папке проекта нет файлов — проверять нечего")
                )
                return report

            self._check_syntax(py_files, report)
            self._check_imports(py_files, report)
            report.api, report.import_lines = self._project_api(py_files)
            self._check_structure(report)
            self._check_entry(report)
            self._check_assets(report)
            self._check_requirements(py_files, report)
            if run_tests:
                self._check_tests(report)
        except Exception as exc:  # noqa: BLE001 — проверка не должна ронять сборку
            report.issues.append(Issue("check", "error", f"проверка не выполнена: {exc}"))
        finally:
            self._cleanup()
            report.duration_ms = int((time.monotonic() - started) * 1000)

        return report

    # ── копия проекта с предложенными файлами ─────────────────────────

    def _materialize(self) -> Path:
        if not self.overlay:
            return self.project_path

        self._temp_root = Path(tempfile.mkdtemp(prefix="ai_team_check_"))
        target = self._temp_root / "project"
        shutil.copytree(
            self.project_path,
            target,
            ignore=shutil.ignore_patterns(*SKIP_DIRS, "*.pyc"),
            dirs_exist_ok=False,
        )

        root = target.resolve()
        for rel, content in self.overlay.items():
            rel_path = str(rel).replace("\\", "/").lstrip("/")
            if not rel_path or ".." in Path(rel_path).parts:
                continue
            dest = (target / rel_path).resolve()
            if root != dest and root not in dest.parents:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

        return target

    def _cleanup(self) -> None:
        if self._temp_root is not None and self._temp_root.exists():
            shutil.rmtree(self._temp_root, ignore_errors=True)
        self._temp_root = None

    # ── сбор файлов ───────────────────────────────────────────────────

    def _collect_python(self, report: BuildReport) -> List[Path]:
        root = self._work_root
        py_files: List[Path] = []
        for path in sorted(root.rglob("*")):
            if len(report.files) >= MAX_FILES:
                report.issues.append(
                    Issue(
                        "files",
                        "warning",
                        f"файлов больше {MAX_FILES}: проверены первые {MAX_FILES}",
                    )
                )
                break
            if not path.is_file():
                continue
            rel_parts = path.relative_to(root).parts
            if any(part in SKIP_DIRS for part in rel_parts[:-1]):
                continue
            if path.name in SKIP_FILES:
                continue
            report.files.append("/".join(rel_parts))
            if path.suffix.lower() == ".py":
                py_files.append(path)

        self._stems = {p.stem for p in py_files}
        return py_files

    # ── 1. синтаксис ──────────────────────────────────────────────────

    def _check_syntax(self, py_files: Iterable[Path], report: BuildReport) -> None:
        for path in py_files:
            rel = self._rel(path)
            try:
                # utf-8-sig: файл с BOM — это нормальный UTF-8, а не SyntaxError.
                source = path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                report.issues.append(
                    Issue("syntax", "error", "файл не читается как UTF-8", rel)
                )
                continue
            try:
                compile(source, rel, "exec")
            except SyntaxError as exc:
                report.issues.append(
                    Issue("syntax", "error", f"SyntaxError: {exc.msg}", rel, exc.lineno)
                )

    # ── 2. импорты ────────────────────────────────────────────────────

    def _check_imports(self, py_files: List[Path], report: BuildReport) -> None:
        entries, roots = self._module_entries(py_files)
        if not entries:
            return

        payload = {
            "root": str(self._work_root.resolve()),
            "roots": [str(r.resolve()) for r in roots],
            "modules": entries[:MAX_MODULES],
        }

        try:
            completed = subprocess.run(
                [sys.executable, "-c", _IMPORT_SCRIPT],
                input=json.dumps(payload, ensure_ascii=False),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(self._work_root),
                timeout=IMPORT_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            report.issues.append(
                Issue(
                    "import",
                    "warning",
                    f"проверка импортов не уложилась в {IMPORT_TIMEOUT} с: "
                    "похоже, файл запускает сервер или ждёт ввода при импорте",
                )
            )
            return

        marker = "<<<BUILD_CHECK>>>"
        stdout = completed.stdout or ""
        if marker not in stdout:
            tail = (completed.stderr or "").strip().splitlines()[-2:]
            report.issues.append(
                Issue(
                    "import",
                    "warning",
                    "проверка импортов не запустилась: " + (" / ".join(tail) or "нет вывода"),
                )
            )
            return

        try:
            raw = json.loads(stdout.rsplit(marker, 1)[-1])
        except json.JSONDecodeError:
            report.issues.append(
                Issue("import", "warning", "ответ проверки импортов не разобран")
            )
            return

        for item in raw:
            status = item.get("status")
            if status == "ok":
                continue
            rel = str(item.get("file", ""))
            message = self._clean_paths(str(item.get("message", "")).strip())
            missing = str(item.get("missing", "")).strip()

            if status == "ModuleNotFoundError":
                head = missing.split(".")[0]
                if self._looks_local(head):
                    report.issues.append(
                        Issue(
                            "import",
                            "error",
                            f"импорт не находит модуль `{missing}` в проекте "
                            "(нет файла или папки с `__init__.py`)",
                            rel,
                        )
                    )
                elif head.replace("-", "_").lower() in self._declared_requirements():
                    report.issues.append(
                        Issue(
                            "import",
                            "warning",
                            f"пакет `{head}` есть в requirements.txt, но не установлен",
                            rel,
                        )
                    )
                else:
                    report.issues.append(
                        Issue(
                            "import",
                            "error",
                            f"модуля `{head}` нет ни в проекте, ни в requirements.txt "
                            "(опечатка или пропущенная зависимость)",
                            rel,
                        )
                    )
            elif status == "ImportError":
                report.issues.append(
                    Issue("import", "error", f"импорт не сходится: {message}", rel)
                )
            elif status == "SyntaxError":
                report.issues.append(
                    Issue("import", "error", f"SyntaxError: {message}", rel)
                )
            elif status == "SystemExit":
                report.issues.append(
                    Issue(
                        "import",
                        "warning",
                        "модуль завершает работу при импорте (sys.exit) — запускать нельзя",
                        rel,
                    )
                )
            else:
                report.issues.append(
                    Issue("import", "warning", f"при импорте падает {status}: {message}", rel)
                )

    def _module_entries(self, py_files: List[Path]) -> Tuple[List[Dict[str, Any]], List[Path]]:
        """Имена, под которыми модуль можно импортировать, и корни sys.path.

        Одно и то же имя не бывает единственно верным: `src/calculator.py`
        импортируется и как `calculator` (если `src` — корень), и как
        `src.calculator` (namespace-пакет без `__init__.py`). Проверяем оба
        варианта, чтобы не ругаться на рабочий проект.
        """
        root = self._work_root
        entries: List[Dict[str, Any]] = []
        roots: set = {root}

        for path in py_files:
            rel = path.relative_to(root)
            if rel.name in {"setup.py", "conftest.py"}:
                continue

            parts = list(rel.parts)
            if parts[-1] == "__init__.py":
                parts = parts[:-1]
            else:
                parts[-1] = Path(parts[-1]).stem
            if not parts or "tests" in parts or parts[-1].startswith("test_"):
                continue
            if not all(part.isidentifier() for part in parts):
                continue

            full = ".".join(parts)
            module_root = root
            short_parts = list(parts)
            while len(short_parts) > 1 and not (
                module_root / short_parts[0] / "__init__.py"
            ).exists():
                module_root = module_root / short_parts[0]
                short_parts = short_parts[1:]

            names = []
            if short_parts:
                short = ".".join(short_parts)
                if short != full:
                    names.append(short)
            names.append(full)

            entries.append({"file": "/".join(rel.parts), "names": names})
            roots.add(module_root)

        # Стабильный порядок: родительские пакеты импортируются раньше детей.
        ordered = sorted(
            entries, key=lambda item: (item["names"][-1].count("."), item["names"][-1])
        )
        return ordered, sorted(roots)

    def _looks_local(self, missing: str) -> bool:
        if not missing:
            return False
        head = missing.split(".")[0]
        if head in self._stems:
            return True
        return (self._work_root / head).exists()

    def _declared_requirements(self) -> set:
        """Имена пакетов из requirements.txt — без версий и комментариев."""
        cached = getattr(self, "_declared", None)
        if cached is not None:
            return cached

        declared: set = set()
        path = self._work_root / "requirements.txt"
        if path.is_file():
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith(("#", "-", "git+", "http")):
                    continue
                name = re.split(r"[\[=<>!~;\s]", line, maxsplit=1)[0]
                declared.add(name.replace("-", "_").lower())

        self._declared = declared
        return declared

    # ── 3. точка входа ────────────────────────────────────────────────

    def _check_structure(self, report: BuildReport) -> None:
        """Есть ли в проекте что тестировать.

        Скрипт с `while True: input()` формально работает, но проверить его нечем:
        Тестер начинает выдумывать имена функций, которых нет. Лучше сказать это
        прямо и отправить Backend вынести логику в функции.
        """
        code_files = [
            name for name in report.files
            if name.endswith(".py")
            and not name.startswith("tests/")
            and not Path(name).name.startswith("test_")
        ]
        if not code_files or report.api:
            return
        report.issues.append(
            Issue(
                "structure",
                "error",
                "в коде нет ни одной функции — тестировать нечего. "
                "Вынеси вычисления в функции (например, add(a, b)) в отдельный модуль, "
                "а запуск и ввод оставь в main.py",
            )
        )

    def _check_entry(self, report: BuildReport) -> None:
        for candidate in ENTRY_CANDIDATES:
            if (self._work_root / candidate).is_file():
                report.entry = candidate
                return
        report.issues.append(
            Issue(
                "entry",
                "warning",
                "нет точки входа (main.py/app.py) — непонятно, что запускать",
            )
        )

    # ── 4. ссылки из HTML ────────────────────────────────────────────

    def _check_assets(self, report: BuildReport) -> None:
        root = self._work_root
        for rel in report.files:
            if not rel.lower().endswith((".html", ".htm")):
                continue
            path = root / rel
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for raw in _ASSET_RE.findall(content):
                link = raw.strip()
                low = link.lower()
                if (
                    not link
                    or low.startswith(("http://", "https://", "//", "data:", "#",
                                       "mailto:", "javascript:", "tel:"))
                    or "{{" in link or "{%" in link or "<%" in link
                ):
                    continue
                clean = link.split("?")[0].split("#")[0]
                candidates = [path.parent / clean, root / clean.lstrip("/")]
                if not any(candidate.is_file() for candidate in candidates):
                    report.issues.append(
                        Issue("assets", "warning", f"нет файла `{link}`", rel)
                    )

    # ── 5. зависимости ───────────────────────────────────────────────

    def _check_requirements(self, py_files: List[Path], report: BuildReport) -> None:
        imported: Dict[str, str] = {}
        for path in py_files:
            rel = self._rel(path)
            try:
                tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported.setdefault(alias.name.split(".")[0], rel)
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    imported.setdefault(node.module.split(".")[0], rel)

        stdlib = getattr(sys, "stdlib_module_names", set())
        local = set(self._stems) | {
            part.split(".")[0] for part in list(imported) if (self._work_root / part).exists()
        }
        external = {
            name: rel
            for name, rel in imported.items()
            if name not in stdlib and name not in local and not name.startswith("_")
        }
        if not external:
            return

        requirements = self._work_root / "requirements.txt"
        if not requirements.is_file():
            shown = ", ".join(sorted(external)[:6])
            report.issues.append(
                Issue(
                    "deps",
                    "warning",
                    f"используются внешние пакеты ({shown}), а requirements.txt нет",
                )
            )
            return

        declared = self._declared_requirements()

        for name, rel in sorted(external.items()):
            if name.replace("-", "_").lower() not in declared:
                report.issues.append(
                    Issue("deps", "warning", f"пакет `{name}` не указан в requirements.txt", rel)
                )

    # ── 6. тесты ─────────────────────────────────────────────────────

    def _check_tests(self, report: BuildReport) -> None:
        root = self._work_root
        has_tests = (root / "tests").is_dir() or any(
            Path(rel).name.startswith("test_") and rel.endswith(".py")
            for rel in report.files
        )
        if not has_tests:
            report.tests = {"ran": False, "reason": "тестов нет"}
            report.issues.append(
                Issue("tests", "warning", "тестов нет — запуском ничего не проверено")
            )
            return

        try:
            completed = subprocess.run(
                [
                    sys.executable, "-c", _PYTEST_SCRIPT,
                    "-q", "--tb=line", "-p", "no:cacheprovider",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(root),
                timeout=TESTS_TIMEOUT,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
        except subprocess.TimeoutExpired:
            report.tests = {"ran": False, "reason": f"дольше {TESTS_TIMEOUT} с"}
            report.issues.append(
                Issue("tests", "warning", f"тесты не уложились в {TESTS_TIMEOUT} с")
            )
            return

        output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
        if "No module named 'pytest'" in output or "No module named pytest" in output:
            report.tests = {"ran": False, "reason": "pytest не установлен"}
            report.issues.append(
                Issue("tests", "warning", "pytest не установлен — тесты не запускались")
            )
            return

        passed = _count(output, "passed")
        failed = _count(output, "failed")
        errors = _count(output, "error") + _count(output, "errors")

        if completed.returncode == 5 or "no tests ran" in output:
            report.tests = {"ran": False, "reason": "pytest не нашёл тестов"}
            report.issues.append(
                Issue("tests", "warning", "pytest не нашёл тестов — проверять нечего")
            )
            return

        report.tests = {
            "ran": True,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "returncode": completed.returncode,
            "failures": [self._clean_paths(line) for line in _failure_lines(output)[:3]],
            "output_tail": output[-800:],
        }

        if completed.returncode != 0:
            if failed == 0 and errors == 0:
                # Сбор тестов упал (например, тест импортирует несуществующий модуль):
                # «0 упало, 0 ошибок» звучит как «всё хорошо» — так нельзя.
                tail = output.strip().splitlines()[-1][:160] if output.strip() else ""
                detail = "тесты не запустились (ошибка сбора тестов)" + (f": {tail}" if tail else "")
            elif failed == 0:
                detail = f"тесты не запустились: {errors} ошибок сбора"
            else:
                detail = f"тесты падают: {failed} упало, {errors} ошибок"
            first = [self._clean_paths(line) for line in _failure_lines(output)[:1]]
            report.issues.append(
                Issue("tests", "error", detail + (f" ({first[0]})" if first else ""))
            )

    # ── служебное ────────────────────────────────────────────────────

    def _rel(self, path: Path) -> str:
        try:
            return "/".join(path.relative_to(self._work_root).parts)
        except ValueError:
            return str(path)

    def _project_api(self, py_files: List[Path]) -> tuple:
        """Публичные функции и классы проекта — чтобы Тестер проверял то, что есть.

        Возвращает (список для человека, готовые строки импорта для тестов).
        """
        items: List[str] = []
        imports: List[str] = []
        for path in py_files:
            rel = self._rel(path)
            if rel.startswith("tests/") or path.name.startswith("test_"):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue

            shown: List[str] = []
            bare: List[str] = []
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("_"):
                        continue
                    args = [arg.arg for arg in node.args.args][:4]
                    shown.append(f"{node.name}({', '.join(args)})")
                    bare.append(node.name)
                elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                    shown.append(node.name)

            if not shown:
                continue
            items.append(f"{rel}: " + ", ".join(shown[:6]))
            if "/" not in rel and rel.endswith(".py") and bare:
                imports.append(f"from {rel[:-3]} import {', '.join(bare[:4])}")

        return items[:10], imports[:2]

    def _clean_paths(self, text: str) -> str:
        """Убирает из сообщений временные абсолютные пути — они шумят в промпте."""
        for prefix in (
            str(self._work_root), str(self._work_root.resolve()),
            str(self.project_path), str(self.project_path.resolve()),
        ):
            for sep in ("\\", "/"):
                text = text.replace(prefix + sep, "")
            text = text.replace(prefix, "")
        text = text.replace("\\", "/")
        while "//" in text:
            text = text.replace("//", "/")
        return text.strip()


def check_build(
    project_path: Path,
    approvals: Any = None,
    overlay: Optional[Dict[str, str]] = None,
    run_tests: bool = True,
) -> BuildReport:
    """Проверяет сборку, включая правки, ждущие подтверждения.

    `approvals` — очередь подтверждений (`ApprovalRuntime`). Её содержимое
    накладывается поверх папки проекта: человеку показывают именно то, что
    получится после «Применить».
    """
    if overlay is None and approvals is not None:
        overlay = pending_overlay(project_path, approvals)

    pending = len(overlay or {})
    check = BuildCheck(project_path, overlay=overlay, pending_files=pending)
    return check.run(run_tests=run_tests)


def pending_overlay(project_path: Path, approvals: Any) -> Dict[str, str]:
    """Собирает предложенные файлы проекта: путь внутри проекта → содержимое."""
    overlay: Dict[str, str] = {}
    try:
        requests = approvals.get_pending()
    except Exception:  # noqa: BLE001 — без очереди проверяем то, что на диске
        return overlay

    root = Path(project_path).resolve()
    for request in requests:
        for raw_path, content in (getattr(request, "files_content", None) or {}).items():
            try:
                rel = Path(raw_path).resolve().relative_to(root)
            except (ValueError, OSError):
                continue
            overlay["/".join(rel.parts)] = content
    return overlay


# ── текст для человека и для модели ─────────────────────────────────


def _count(text: str, word: str) -> int:
    match = re.search(rf"(\d+)\s+{word}\b", text)
    return int(match.group(1)) if match else 0


def _failure_lines(output: str) -> List[str]:
    """Строки вида `tests/test_x.py:12: AssertionError: ...` из pytest --tb=line."""
    lines = []
    for line in output.splitlines():
        stripped = line.strip()
        if re.match(r"^[A-Za-z]:?[\\/].+?:\d+: ", stripped) or re.match(
            r"^[\w./\\-]+\.py:\d+: ", stripped
        ):
            if "Warning" in stripped or "warning" in stripped:
                continue
            lines.append(stripped[:220])
    return lines


def _plural_ru(number: int, one: str, few: str, many: str) -> str:
    if number % 10 == 1 and number % 100 != 11:
        return one
    if 2 <= number % 10 <= 4 and not 12 <= number % 100 <= 14:
        return few
    return many


def _summary(report: BuildReport, limit: int) -> str:
    errors, warnings = len(report.errors), len(report.warnings)
    tests = report.tests or {}
    files = len(report.files)

    parts = [
        f"Проверка сборки: {files} {_plural_ru(files, 'файл', 'файла', 'файлов')}",
        f"ошибок {errors}",
        f"предупреждений {warnings}",
    ]
    head = ", ".join(parts) + "."
    if tests.get("ran"):
        head += (
            f" Тесты: {tests.get('passed', 0)} прошло, "
            f"{tests.get('failed', 0)} упало."
        )
    elif tests:
        head += f" Тесты: не запускались ({tests.get('reason', '')})."
    if report.pending_files:
        head += (
            f" Учтено {report.pending_files} предложенных файлов — ещё ждут подтверждения."
        )
    if not errors and not warnings:
        head += " Поломок не найдено."

    lines = [head]
    for issue in (report.errors + report.warnings)[:limit]:
        label = "Ошибка" if issue.severity == "error" else "Предупреждение"
        lines.append(f"• {label}: {issue.text()}")
    hidden = len(report.errors) + len(report.warnings) - limit
    if hidden > 0:
        lines.append(f"• и ещё {hidden}")
    return "\n".join(lines)


def _prompt_block(report: BuildReport) -> str:
    errors, warnings = len(report.errors), len(report.warnings)
    tests = report.tests or {}
    files = len(report.files)

    lines = [
        "ПРОВЕРКА СБОРКИ ЦЕЛИКОМ (факты от машины, не догадки):",
        f"Файлов: {files}. Ошибок: {errors}. Предупреждений: {warnings}.",
    ]
    if tests.get("ran"):
        lines.append(
            f"Тесты: {tests.get('passed', 0)} прошло, {tests.get('failed', 0)} упало."
        )
    elif tests:
        lines.append(f"Тесты: не запускались ({tests.get('reason', '')}).")
    if report.pending_files:
        lines.append(f"В проверке учтено предложенных файлов: {report.pending_files}.")
    if report.api:
        lines.append("Что уже есть в проекте:")
        lines += [f"- {item}" for item in report.api[:8]]

    # Готовая строка импорта: модель уверенно копирует её, а без импорта
    # тест падает с NameError и ничего не проверяет.
    if report.import_lines:
        lines.append("Первая строка теста — импорт:")
        lines += [f"  {line}" for line in report.import_lines]
    if report.errors:
        lines.append("Ошибки:")
        lines += [f"{i}. {issue.text()}" for i, issue in enumerate(report.errors[:6], 1)]
    # Зависимости в подсказку Тестеру не идём: иначе он пишет тест «установлен ли пакет»
    # вместо теста поведения. Человеку в сводке они остаются.
    testable_warnings = [issue for issue in report.warnings if issue.check != "deps"]
    if testable_warnings:
        lines.append("Предупреждения:")
        lines += [f"{i}. {issue.text()}" for i, issue in enumerate(testable_warnings[:4], 1)]

    lines.append(
        "Сначала напиши тест, который падает на этой поломке: сейчас красный, после починки зелёный. "
        "Не пересказывай список — докажи его тестами. "
        "Проверяй поведение функций проекта, а не наличие пакетов или файлов."
        if report.errors
        else "Ошибок импорта нет. Проверь тестами главные функции и один плохой ввод. "
             "Проверяй поведение, а не наличие пакетов."
    )
    return _clip("\n".join(lines))


def _clip(text: str) -> str:
    if len(text) <= PROMPT_LIMIT:
        return text
    return text[: PROMPT_LIMIT - 1].rstrip() + "…"
