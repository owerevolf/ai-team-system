"""Проверка готового проекта: компилируется ли каждый Python-файл.

Запуск:
    python scripts/check_project.py "C:\\Users\\...\\ai-team-projects\\<проект>"

Нужно, чтобы «сделано» проверялось фактом, а не на слово: если хотя бы один файл
не компилируется, это видно сразу — с путём и причиной.
"""

import pathlib
import py_compile
import sys

if len(sys.argv) < 2:
    raise SystemExit("Укажи папку проекта: python scripts/check_project.py <папка>")

root = pathlib.Path(sys.argv[1])
if not root.exists():
    raise SystemExit(f"Папки нет: {root}")

ok = 0
failed = 0
for path in sorted(root.rglob("*.py")):
    try:
        py_compile.compile(str(path), doraise=True)
        ok += 1
    except py_compile.PyCompileError as exc:
        failed += 1
        print(f"СБОЙ: {path.relative_to(root)} — {str(exc)[:220]}")

print(f"файлов проверено: {ok + failed}, ошибок: {failed}")
raise SystemExit(1 if failed else 0)
