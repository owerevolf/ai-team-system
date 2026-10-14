"""
Генератор правок: модель предлагает изменение, код его проверяет до применения.

Формат ответа модели (строгий JSON):
    {"changes": [{"path": "путь/файл.py", "find": "старый фрагмент", "replace": "новый"}]}

Почему так, а не «пришли новый файл целиком»: такую правку можно проверить —
старый фрагмент обязан встречаться в файле ровно один раз. Не нашёлся или
встречается дважды — изменение отклоняется с объяснением, а не применяется наугад.

Модуль ничего не пишет на диск: он возвращает проверенные изменения, а применять
их должен движок патчей после подтверждения человеком.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

PROMPT = """Ты вносишь минимальную правку в файлы проекта.

Верни СТРОГО JSON без пояснений:
{{"changes": [{{"path": "<путь>", "find": "<точный фрагмент из файла>", "replace": "<чем заменить>"}}]}}

Правила:
- фрагмент find должен встречаться в файле ровно один раз;
- не переписывай файл целиком;
- путь указывай относительно корня проекта.

Задача: {task}

Содержимое файлов:
{files}
"""


@dataclass
class FileChange:
    """Проверенное изменение одного файла."""

    path: str
    old_content: str
    new_content: str

    @property
    def changed_lines(self) -> int:
        return abs(
            len(self.new_content.splitlines()) - len(self.old_content.splitlines())
        )


@dataclass
class GenerationResult:
    changes: List[FileChange] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.changes) and not self.errors


def _extract_json(text: str) -> Optional[dict]:
    match = re.search(r"\{.*\}", text or "", re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def generate_changes(
    task: str,
    files: Dict[str, str],
    model_call: Callable[[str], str],
    max_files: int = 5,
) -> GenerationResult:
    """
    Просит модель о правке и проверяет её по фактическому содержимому файлов.

    `files`: путь → текущее содержимое (то, что разрешено менять контрактом задачи).
    `model_call`: функция «промпт → ответ модели».
    """
    result = GenerationResult()
    if not files:
        result.errors.append("нет файлов для правки")
        return result

    listing = "\n\n".join(
        f"### {path}\n{content}" for path, content in list(files.items())[:max_files]
    )
    prompt = PROMPT.format(task=task, files=listing)

    try:
        answer = model_call(prompt)
    except Exception as exc:  # noqa: BLE001 — сбой модели не должен ломать поток
        result.errors.append(f"модель недоступна: {type(exc).__name__}")
        return result

    data = _extract_json(answer or "")
    if not data:
        result.errors.append("модель вернула не JSON")
        return result

    for item in data.get("changes", []):
        path = str(item.get("path") or "").strip()
        find = item.get("find")
        replace = item.get("replace")

        if not path or find is None or replace is None:
            result.errors.append(f"изменение без обязательных полей: {path or '—'}")
            continue

        if path not in files:
            result.errors.append(f"{path}: файла нет в контексте задачи")
            continue

        content = files[path]
        occurrences = content.count(find)
        if occurrences != 1:
            result.errors.append(
                f"{path}: фрагмент встречается {occurrences} раз, ожидался один"
            )
            continue

        result.changes.append(
            FileChange(
                path=path,
                old_content=content,
                new_content=content.replace(find, replace),
            )
        )

    return result
