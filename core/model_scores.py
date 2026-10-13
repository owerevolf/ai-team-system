"""
Скоринг моделей: кто справляется с задачами и сколько времени тратит.

Бенчмарк намеренно короткий — несколько маленьких задач, чтобы прогон на слабом железе
не занимал полчаса. Результат складывается в `.cache/model_scores.json`, и по нему можно
выбрать модель под тип задачи: код, исправление, объяснение.

Запуск на локальной модели (нужна работающая Ollama):
    python -m core.model_scores --model qwen3:8b
"""

import argparse
import json
import os
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
SCORES_FILE = BASE_DIR / ".cache" / "model_scores.json"


@dataclass
class BenchTask:
    """Одна задача бенчмарка: что спросить и как проверить ответ."""

    id: str
    kind: str                        # code | fix | explain
    prompt: str
    check: Callable[[str], bool]


def _has_all(*needles: str) -> Callable[[str], bool]:
    def check(text: str) -> bool:
        low = (text or "").lower()
        return all(needle in low for needle in needles)

    return check


def _has_any(*needles: str) -> Callable[[str], bool]:
    def check(text: str) -> bool:
        low = (text or "").lower()
        return any(needle in low for needle in needles)

    return check


def _listdir_check(text: str) -> bool:
    low = (text or "").lower()
    return "print" in low and any(name in low for name in ("listdir", "glob", "iterdir", "scandir"))


TASKS: List[BenchTask] = [
    BenchTask("sum_two", "code", "Напиши функцию на Python, которая возвращает сумму двух чисел. Только код.", _has_all("def", "return", "+")),
    BenchTask("fix_print", "fix", "В строке кода ошибка: prnt('hello'). Напиши исправленный вариант.", _has_all("print")),
    BenchTask("explain_json", "explain", "Объясни одним предложением, что такое JSON.", lambda text: len((text or "").strip()) > 20),
    BenchTask("list_files", "code", "Напиши на Python одну строку, которая печатает имена файлов в текущей папке.", _listdir_check),
    BenchTask("explain_test", "explain", "Объясни простыми словами, зачем нужен автотест.", _has_any("провер", "ошиб", "работ")),
]


def run_benchmark(model_call: Callable[[str], str], tasks: Optional[List[BenchTask]] = None) -> Dict:
    """Прогоняет задачи через переданную функцию вызова модели."""
    tasks = tasks or TASKS
    results: List[Dict] = []

    for task in tasks:
        started = time.perf_counter()
        answer, error, passed = "", "", False
        try:
            answer = model_call(task.prompt) or ""
        except Exception as exc:  # noqa: BLE001 — сбой модели не должен ломать прогон
            error = f"{type(exc).__name__}"
        elapsed = int((time.perf_counter() - started) * 1000)

        if not error:
            try:
                passed = bool(task.check(answer))
            except Exception:  # noqa: BLE001
                passed = False

        results.append({
            "id": task.id,
            "kind": task.kind,
            "passed": passed,
            "ms": elapsed,
            "error": error,
            "answer_preview": answer[:120],
        })

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "tasks": results,
    }


def score_from_results(run: Dict) -> float:
    """Доля пройденных задач: 0.0 … 1.0."""
    total = run.get("total") or 0
    if not total:
        return 0.0
    return round((run.get("passed") or 0) / total, 3)


def load_scores(path: Optional[Path] = None) -> Dict[str, Dict]:
    """Загружает оценки всех прогонов: модель → результат."""
    target = Path(path) if path else SCORES_FILE
    if not target.exists():
        return {}
    return json.loads(target.read_text(encoding="utf-8"))


def record_run(model_name: str, run: Dict, path: Optional[Path] = None) -> Path:
    """Сохраняет результат прогона в общий файл оценок."""
    target = Path(path) if path else SCORES_FILE
    data = load_scores(target)
    data[model_name] = {**run, "score": score_from_results(run)}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _kind_stats(run: Dict, kind: str) -> tuple:
    """Доля успеха и среднее время по задачам одного типа."""
    tasks = [t for t in run.get("tasks", []) if t.get("kind") == kind]
    if not tasks:
        return 0.0, 0
    passed = sum(1 for t in tasks if t.get("passed"))
    avg_ms = int(sum(t.get("ms", 0) for t in tasks) / len(tasks))
    return passed / len(tasks), avg_ms


def best_model(task_kind: str, scores: Optional[Dict[str, Dict]] = None,
               available: Optional[List[str]] = None) -> Optional[str]:
    """
    Лучшая модель под тип задачи: сначала по доле успеха, при равенстве — по скорости.

    `available` — список доступных сейчас моделей; если он передан, остальные не рассматриваются.
    """
    scores = scores if scores is not None else load_scores()
    if not scores:
        return None

    best_name, best_rank = None, None
    for model_name, run in scores.items():
        if available is not None and model_name not in available:
            continue
        passed_ratio, avg_ms = _kind_stats(run, task_kind)
        if passed_ratio == 0.0:
            continue
        rank = (-passed_ratio, avg_ms)
        if best_rank is None or rank < best_rank:
            best_name, best_rank = model_name, rank

    return best_name


def _ollama_call(prompt: str, model: str, base_url: str, timeout: int = 180) -> str:
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8")).get("response", "")


def main() -> None:
    parser = argparse.ArgumentParser(description="Короткий бенчмарк модели (по умолчанию — локальная Ollama)")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "qwen3:8b"))
    parser.add_argument("--base-url", default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    args = parser.parse_args()

    print(f"Модель: {args.model} ({args.base_url}) — {len(TASKS)} задач")
    run = run_benchmark(lambda prompt: _ollama_call(prompt, args.model, args.base_url))

    for task in run["tasks"]:
        mark = "OK " if task["passed"] else "-- "
        print(f"  {mark}{task['id']:12} {task['ms']:6} мс  {task['error'] or ''}")

    print(f"\nИтог: {run['passed']} из {run['total']} (оценка {score_from_results(run)})")
    print(f"Сохранено: {record_run(args.model, run)}")


if __name__ == "__main__":
    main()
