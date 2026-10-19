"""Проверка сборки целиком: то, что не видно по синтаксису одного файла.

Каждый тест — отдельная поломка, которую `compile()` пропускает: импорт
несуществующего имени, ссылка на отсутствующий файл, падающие тесты,
неприменённые правки из очереди подтверждений.
"""

from pathlib import Path

import pytest

from core.build_check import check_build


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    root = tmp_path / "demo"
    root.mkdir()
    _write(root, "src/__init__.py", "")
    _write(root, "src/calc.py", "def add(a, b):\n    return a + b\n")
    _write(root, "src/main.py", "from src.calc import add\n\n\ndef run():\n    return add(1, 2)\n")
    _write(root, "requirements.txt", "")
    _write(root, "index.html", '<html><body><script src="app.js"></script></body></html>')
    return root


def test_clean_project_passes(project: Path) -> None:
    report = check_build(project)

    assert report.ok, report.summary()
    assert report.entry == "src/main.py"
    # Ссылка на app.js ведёт в пустоту — это предупреждение, а не поломка сборки.
    assert any("app.js" in issue.text() for issue in report.warnings)


def test_missing_name_in_existing_file_is_an_error(project: Path) -> None:
    _write(project, "src/main.py", "from src.calc import add, divide\n\n\ndef run():\n    return divide(1, 2)\n")

    report = check_build(project)

    assert not report.ok
    assert any("импорт не сходится" in issue.text() for issue in report.errors)


def test_missing_local_module_is_an_error(project: Path) -> None:
    _write(project, "src/main.py", "from src.helpers import twice\n\n\ndef run():\n    return twice(1)\n")

    report = check_build(project)

    assert not report.ok
    assert any("не находит модуль" in issue.text() for issue in report.errors)


def test_declared_but_missing_package_is_only_a_warning(project: Path) -> None:
    _write(project, "requirements.txt", "leftpad==1.0\n")
    _write(project, "src/main.py", "import leftpad\n\n\ndef run():\n    return leftpad.pad('x')\n")

    report = check_build(project)

    assert report.ok, report.summary()
    assert any("requirements.txt, но не установлен" in issue.text() for issue in report.warnings)


def test_undeclared_missing_module_is_an_error(project: Path) -> None:
    _write(project, "src/main.py", "import leftpad\n\n\ndef run():\n    return leftpad.pad('x')\n")

    report = check_build(project)

    assert not report.ok
    assert any("нет ни в проекте, ни в requirements.txt" in issue.text() for issue in report.errors)


def test_syntax_error_points_to_the_line(project: Path) -> None:
    _write(project, "src/broken.py", "def broken(:\n    pass\n")

    report = check_build(project)

    assert not report.ok
    syntax = [issue for issue in report.errors if issue.check == "syntax"]
    assert syntax and syntax[0].line == 1
    assert syntax[0].file == "src/broken.py"


def test_proposed_files_are_checked_before_approval(project: Path) -> None:
    # Агент предложил calc.py, но человек ещё не нажал «Применить»: на диске файла нет.
    (project / "src" / "calc.py").unlink()
    overlay = {
        "src/calc.py": "def add(a, b):\n    return a + b\n",
    }

    report = check_build(project, overlay=overlay, run_tests=False)

    assert report.ok, report.summary()
    assert report.pending_files == 1


def test_broken_tests_make_the_build_red(project: Path) -> None:
    _write(project, "tests/test_calc.py", "from src.calc import add\n\n\ndef test_add():\n    assert add(2, 2) == 5\n")

    report = check_build(project)

    assert not report.ok
    assert report.tests["failed"] == 1
    assert any(issue.check == "tests" for issue in report.errors)


def test_project_api_lists_public_functions(project: Path) -> None:
    """Тестер должен видеть, что именно можно проверить."""
    report = check_build(project, run_tests=False)

    assert any(item.startswith("src/calc.py: add(a, b)") for item in report.api)
    assert any("run()" in item for item in report.api)
    assert all("test_" not in item for item in report.api)


def test_prompt_has_ready_import_line(tmp_path: Path) -> None:
    """Готовая строка импорта: без неё тест на модели падает с NameError."""
    root = tmp_path / "calc"
    root.mkdir()
    (root / "calculator.py").write_text(
        "def add(a, b):\n    return a + b\n\ndef sub(a, b):\n    return a - b\n",
        encoding="utf-8",
    )

    block = check_build(root, run_tests=False).as_prompt_block()

    assert "from calculator import add, sub" in block


def test_project_without_files_is_not_silently_green(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    report = check_build(empty)

    assert not report.ok
    assert any("нет файлов" in issue.text() for issue in report.errors)


def test_src_layout_without_init_is_not_a_false_alarm(tmp_path: Path) -> None:
    """`src/` без `__init__.py` — рабочий namespace-пакет, а не поломка."""
    root = tmp_path / "namespace"
    (root / "src").mkdir(parents=True)
    (root / "src" / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (root / "src" / "main.py").write_text(
        "from src.calc import add\n\n\ndef run():\n    return add(1, 2)\n", encoding="utf-8"
    )

    report = check_build(root, run_tests=False)

    assert report.ok, report.summary()
