"""
Агент истины: факты о репозитории вместо догадок.

Задача модуля — не «подумать», а найти. Он отвечает только тем, что реально есть в коде,
и всегда указывает `файл:строка`. Если факта нет — так и говорит, чтобы модель не выдумывала.

Три части:
* `CodeIndex` — индекс символов (классы, функции, методы, константы, маршруты) с адресами;
* `ask()` — поиск фактов по вопросу: возвращает список фактов со ссылками;
* `verify_text()` — проверка текста (например, ответа агента) на выдуманные имена.

Пример:
    index = CodeIndex(Path(".")).build()
    ask("где выбирается промпт агента по уровню?", index)
    verify_text("Вызови get_agent_prompt и FakeFunc()", index)
"""

import ast
import builtins
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

SKIP_DIRS = {
    ".git", ".venv", "venv", "venv_new", "__pycache__", "node_modules",
    ".cache", ".ai-team", ".pytest_cache", "kimi", "screenshots", "screenshots_new",
}

# Имена, которые не нужно считать выдуманными: стандартная библиотека и типовые пакеты
KNOWN_EXTERNAL = {
    "json", "os", "sys", "re", "ast", "time", "logging", "datetime", "pathlib", "typing",
    "subprocess", "shutil", "tempfile", "threading", "hashlib", "urllib", "dataclasses",
    "collections", "functools", "itertools", "asyncio", "sqlite3", "base64", "uuid", "random",
    "fastapi", "starlette", "pydantic", "uvicorn", "httpx", "openai", "anthropic", "ollama",
    "pytest", "dotenv", "loguru", "jinja2", "psutil", "sqlalchemy", "alembic", "rich", "click",
    "Path", "Optional", "Dict", "List", "Any", "str", "int", "float", "bool", "None", "True",
    "False", "print", "len", "range", "open", "list", "dict", "set", "tuple", "type",
}


@dataclass
class Symbol:
    """Один факт о коде: что это, где лежит и на какой строке."""

    name: str
    kind: str            # class | function | method | constant | route
    path: str            # путь относительно корня репозитория
    line: int
    parent: str = ""     # класс-владелец для методов

    def to_dict(self) -> Dict:
        return asdict(self)

    def source(self) -> str:
        return f"{self.path}:{self.line}"


@dataclass
class Fact:
    """Факт, найденный по вопросу."""

    symbol: Symbol
    reason: str = ""

    def to_dict(self) -> Dict:
        data = self.symbol.to_dict()
        data["reason"] = self.reason
        data["source"] = self.symbol.source()
        return data


@dataclass
class Issue:
    """Неподтверждённое имя в проверяемом тексте."""

    name: str
    position: int
    note: str = "в индексе репозитория такого имени нет"

    def to_dict(self) -> Dict:
        return asdict(self)


class CodeIndex:
    """Индекс символов репозитория: строится по файлам Python и не требует запуска кода."""

    def __init__(self, root: Path, symbols: Optional[List[Symbol]] = None) -> None:
        self.root = Path(root).resolve()
        self.symbols: List[Symbol] = symbols or []

    # ── построение ────────────────────────────────────────────────────────────

    def build(self) -> "CodeIndex":
        symbols: List[Symbol] = []
        for path in sorted(self._python_files()):
            symbols.extend(self._symbols_from_file(path))
        self.symbols = symbols
        return self

    def _python_files(self) -> Iterable[Path]:
        for path in self.root.rglob("*.py"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            yield path

    def _symbols_from_file(self, path: Path) -> List[Symbol]:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError, OSError):
            return []

        relative = path.relative_to(self.root).as_posix()
        found: List[Symbol] = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                found.append(Symbol(node.name, "class", relative, node.lineno))
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        found.append(Symbol(child.name, "method", relative, child.lineno, node.name))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                kind = "route" if self._route_path(node) else "function"
                found.append(Symbol(node.name, kind, relative, node.lineno))
                route = self._route_path(node)
                if route:
                    found.append(Symbol(route, "route", relative, node.lineno, node.name))
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        found.append(Symbol(target.id, "constant", relative, node.lineno))

        return found

    @staticmethod
    def _route_path(node: ast.AST) -> str:
        """Возвращает путь маршрута, если функция оформлена декоратором @app/@router.get(...)."""
        for decorator in getattr(node, "decorator_list", []):
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                if decorator.func.attr in ("get", "post", "put", "delete", "patch"):
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        value = decorator.args[0].value
                        if isinstance(value, str):
                            return value
        return ""

    # ── поиск ────────────────────────────────────────────────────────────────

    def find(self, name: str, limit: int = 10) -> List[Symbol]:
        """Точное совпадение по имени (регистр не важен)."""
        needle = (name or "").strip().lower()
        return [s for s in self.symbols if s.name.lower() == needle][:limit]

    def search(self, query: str, limit: int = 10) -> List[Symbol]:
        """Поиск по части имени."""
        needle = (query or "").strip().lower()
        if not needle:
            return []
        return [s for s in self.symbols if needle in s.name.lower()][:limit]

    def routes(self) -> List[Symbol]:
        return [s for s in self.symbols if s.kind == "route"]

    # ── сохранение ───────────────────────────────────────────────────────────

    def save(self, path: Optional[Path] = None) -> Path:
        target = Path(path) if path else self.root / ".cache" / "truth_index.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "root": str(self.root),
            "count": len(self.symbols),
            "symbols": [s.to_dict() for s in self.symbols],
        }
        target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: Path) -> "CodeIndex":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        index = cls(Path(data.get("root", ".")))
        index.symbols = [Symbol(**item) for item in data.get("symbols", [])]
        return index


def ask(question: str, index: CodeIndex, limit: int = 5) -> List[Fact]:
    """
    Ищет в индексе факты по вопросу.

    Пустой результат — честный ответ «в коде этого нет»: вызывающий код обязан
    так и сказать пользователю, а не додумывать.
    """
    words = [w.strip(".,?!:;()[]{}\"'`") for w in (question or "").split()]
    candidates = [w for w in words if len(w) >= 4]

    facts: List[Fact] = []
    seen = set()

    for name in candidates:
        for symbol in index.find(name):
            key = (symbol.name, symbol.path, symbol.line)
            if key not in seen:
                seen.add(key)
                facts.append(Fact(symbol, reason=f"точное совпадение по слову «{name}»"))

    for name in candidates:
        for symbol in index.search(name, limit=limit):
            key = (symbol.name, symbol.path, symbol.line)
            if key not in seen:
                seen.add(key)
                facts.append(Fact(symbol, reason=f"частичное совпадение по слову «{name}»"))

    return facts[:limit]


def _candidate_identifiers(text: str) -> List[tuple]:
    """Вытаскивает из текста имена, которые можно проверить по индексу."""
    import re

    patterns = [
        r"`([A-Za-z_][A-Za-z0-9_\.]{2,})`",          # `имя` в обратных кавычках
        r"\b([A-Za-z_][A-Za-z0-9_]{3,})\s*\(",        # вызов функции
        r"\b([A-Z][A-Za-z0-9]+[A-Z][A-Za-z0-9]+)\b",  # CamelCase
    ]
    found: List[tuple] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            name = match.group(1).split(".")[-1]
            found.append((name, match.start()))
    return found


def verify_text(text: str, index: CodeIndex, limit: int = 20) -> List[Issue]:
    """
    Проверяет текст на имена, которых нет в репозитории.

    Ловит выдуманные функции и классы (частая ошибка моделей). Не ловит неверные
    утверждения о существующих файлах — для них нужна смысловая проверка человеком.
    """
    known = {s.name.lower() for s in index.symbols}
    external = {name.lower() for name in KNOWN_EXTERNAL}
    builtin_names = {name.lower() for name in dir(builtins)}

    issues: List[Issue] = []
    seen = set()
    for name, position in _candidate_identifiers(text):
        low = name.lower()
        if low in known or low in external or low in builtin_names or low in seen:
            continue
        seen.add(low)
        issues.append(Issue(name=name, position=position))
        if len(issues) >= limit:
            break
    return issues
