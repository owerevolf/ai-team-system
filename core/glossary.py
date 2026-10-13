"""
Глоссарий терминов: данные и поиск.

Термины лежат в `config/glossary.ru.json` — их можно править и расширять без изменения кода.
Модуль умеет искать термин, находить термины в тексте (для подсветки и подсказок новичку)
и отдавать короткое объяснение.

Использование:
    from core.glossary import explain, find_terms_in_text

    explain("коммит")                          # «коммит — Сохранённая точка в истории…»
    find_terms_in_text(ответ_агента)           # какие термины объяснить в этом ответе
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
GLOSSARY_FILE = BASE_DIR / "config" / "glossary.ru.json"

_REQUIRED_FIELDS = ("term", "simple")
_cache: Optional[List[Dict]] = None


def load_terms(force: bool = False) -> List[Dict]:
    """Читает глоссарий из файла. Результат кэшируется, force=True перечитывает."""
    global _cache
    if _cache is not None and not force:
        return _cache

    if not GLOSSARY_FILE.exists():
        _cache = []
        return _cache

    data = json.loads(GLOSSARY_FILE.read_text(encoding="utf-8"))
    terms: List[Dict] = []
    for item in data.get("terms", []):
        if not all(item.get(field) for field in _REQUIRED_FIELDS):
            continue
        terms.append(item)

    _cache = terms
    return terms


def list_terms() -> List[Dict]:
    """Полный список терминов — для панели «Словарь»."""
    return list(load_terms())


def _names(item: Dict) -> List[str]:
    return [item["term"]] + [str(a) for a in (item.get("aliases") or [])]


def find_term(query: str) -> Optional[Dict]:
    """Ищет термин по названию или синониму (регистр не важен)."""
    if not query:
        return None
    needle = query.strip().lower()
    for item in load_terms():
        if needle in [name.lower() for name in _names(item)]:
            return item
    return None


def _pattern_for(names: List[str]) -> re.Pattern:
    """Регэксп с границами слов: длинные варианты идут первыми."""
    escaped = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.compile(rf"(?<!\w)({escaped})(?!\w)", re.IGNORECASE)


def find_terms_in_text(text: str, limit: int = 5) -> List[Dict]:
    """
    Находит в тексте термины глоссария — для подсветки и подсказок новичку.

    Порядок — по первому появлению в тексте, повторов нет.
    """
    if not text:
        return []

    found: List[tuple] = []
    for item in load_terms():
        match = _pattern_for(_names(item)).search(text)
        if match:
            found.append((match.start(), item))

    found.sort(key=lambda pair: pair[0])
    return [item for _, item in found[:limit]]


def explain(query: str) -> str:
    """Короткая строка-объяснение: «термин — простыми словами …»."""
    item = find_term(query)
    if not item:
        return ""
    return f"{item['term']} — {item['simple']}"
