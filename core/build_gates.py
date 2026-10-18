"""Пауза между агентами: сборка ждёт, пока человек нажмёт «Дальше».

Зачем: агенты бегут очередью, и человек не успевает ни прочитать объяснение,
ни спросить. Теперь после каждого агента лента останавливается, а продолжение —
только по нажатию. Это и есть разница между «учебной полкой» и очередной IDE.
"""

from __future__ import annotations

import asyncio
from typing import Dict

# Полчаса: человек может отойти к ребёнку, сборка не должна висеть вечно.
DEFAULT_TIMEOUT = 1800


class BuildGate:
    """Один шлюз на сборку: ждёт разрешения и помнит, кто стоит на паузе."""

    def __init__(self) -> None:
        self._events: Dict[str, asyncio.Event] = {}
        self.paused: Dict[str, str] = {}

    def _event(self, build_id: str) -> asyncio.Event:
        if build_id not in self._events:
            self._events[build_id] = asyncio.Event()
        return self._events[build_id]

    async def wait_for_continue(self, build_id: str, agent: str) -> bool:
        """Ставит сборку на паузу и ждёт «Дальше». False — человек не нажал вовремя."""
        event = self._event(build_id)
        event.clear()
        self.paused[build_id] = agent
        try:
            await asyncio.wait_for(event.wait(), timeout=DEFAULT_TIMEOUT)
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            self.paused.pop(build_id, None)

    def release(self, build_id: str) -> bool:
        """Продолжает сборку. False — такой сборки нет или она уже идёт."""
        event = self._events.get(build_id)
        if not event:
            return False
        event.set()
        return True


gate = BuildGate()
