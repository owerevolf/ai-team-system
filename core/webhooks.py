"""
Webhooks - subscription and event processing.

Supported events:
- GitHub: push, pull_request, issues
- GitLab: push, merge_request, issue
- Generic: event

Each webhook has URL + secret + event list.
Incoming events are routed to registered handlers.
"""

import os
import json
import hashlib
import hmac
import time
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import deque
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent.parent
WEBHOOKS_DIR = BASE_DIR / "data" / "webhooks"
WEBHOOKS_DIR.mkdir(parents=True, exist_ok=True)
WEBHOOKS_FILE = WEBHOOKS_DIR / "webhooks.json"
WEBHOOKS_LOG = WEBHOOKS_DIR / "log.jsonl"


@dataclass
class WebhookSubscription:
    id: str
    name: str
    url: str
    secret: str
    events: List[str]
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_triggered: Optional[str] = None
    trigger_count: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "WebhookSubscription":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class WebhookEvent:
    id: str
    subscription_id: str
    event_type: str
    payload: Dict[str, Any]
    source_ip: str = ""
    received_at: str = field(default_factory=lambda: datetime.now().isoformat())
    processed: bool = False
    result: Optional[str] = None


class WebhookManager:
    def __init__(self):
        self.subscriptions: Dict[str, WebhookSubscription] = {}
        self.handlers: Dict[str, List[Callable]] = {}
        self._event_log: deque = deque(maxlen=100)
        self._load_subscriptions()

    def _load_subscriptions(self):
        if WEBHOOKS_FILE.exists():
            try:
                data = json.loads(WEBHOOKS_FILE.read_text(encoding="utf-8"))
                for sub_data in data.get("subscriptions", []):
                    sub = WebhookSubscription.from_dict(sub_data)
                    self.subscriptions[sub.id] = sub
                logger.info(f"Loaded {len(self.subscriptions)} webhook subscriptions")
            except Exception as e:
                logger.error(f"Failed to load webhooks: {e}")

    def _save_subscriptions(self):
        data = {"subscriptions": [s.to_dict() for s in self.subscriptions.values()]}
        WEBHOOKS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def create_subscription(self, name: str, url: str, events: List[str],
                            secret: str = None) -> str:
        sub_id = hashlib.md5(f"{name}:{url}:{time.time()}".encode()).hexdigest()[:12]
        if not secret:
            secret = hashlib.sha256(os.urandom(32)).hexdigest()[:32]
        sub = WebhookSubscription(id=sub_id, name=name, url=url, secret=secret, events=events)
        self.subscriptions[sub_id] = sub
        self._save_subscriptions()
        logger.info(f"Webhook subscription created: {name} ({sub_id})")
        return sub_id

    def delete_subscription(self, sub_id: str) -> bool:
        if sub_id in self.subscriptions:
            del self.subscriptions[sub_id]
            self._save_subscriptions()
            return True
        return False

    def get_subscriptions(self) -> List[Dict]:
        return [s.to_dict() for s in self.subscriptions.values()]

    def register_handler(self, event_type: str, handler: Callable):
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def verify_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        if not signature or not secret:
            return False
        if signature.startswith("sha256="):
            sig_hex = signature.split("=", 1)[1]
        else:
            sig_hex = signature
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig_hex, expected)

    def receive_event(self, sub_id: str, event_type: str, payload: Dict,
                      signature: str = None, source_ip: str = "") -> Dict:
        sub = self.subscriptions.get(sub_id)
        if not sub:
            return {"error": "Subscription not found"}
        if not sub.enabled:
            return {"error": "Subscription disabled"}
        if event_type not in sub.events:
            return {"error": f"Event '{event_type}' not subscribed"}

        event_id = hashlib.md5(f"{sub_id}:{event_type}:{time.time()}".encode()).hexdigest()[:16]
        event = WebhookEvent(
            id=event_id, subscription_id=sub_id, event_type=event_type,
            payload=payload, source_ip=source_ip,
        )

        sub.last_triggered = datetime.now().isoformat()
        sub.trigger_count += 1
        self._save_subscriptions()

        self._event_log.append(event)
        self._log_event(event)

        results = []
        for handler in self.handlers.get(event_type, []):
            try:
                result = handler(event)
                results.append(str(result))
            except Exception as e:
                logger.error(f"Webhook handler error: {e}")
                results.append(f"error: {e}")

        event.processed = True
        event.result = "; ".join(results) if results else "ok"
        return {"status": "received", "event_id": event_id, "results": results}

    def _log_event(self, event: WebhookEvent):
        try:
            with open(WEBHOOKS_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "id": event.id, "subscription_id": event.subscription_id,
                    "event_type": event.event_type, "source_ip": event.source_ip,
                    "received_at": event.received_at, "processed": event.processed,
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def get_recent_events(self, limit: int = 20) -> List[Dict]:
        return [
            {"id": e.id, "subscription_id": e.subscription_id, "event_type": e.event_type,
             "source_ip": e.source_ip, "received_at": e.received_at,
             "processed": e.processed, "result": e.result}
            for e in list(self._event_log)[-limit:]
        ]

    def get_stats(self) -> Dict:
        return {
            "subscriptions": len(self.subscriptions),
            "active": sum(1 for s in self.subscriptions.values() if s.enabled),
            "total_events": sum(s.trigger_count for s in self.subscriptions.values()),
            "recent_events": len(self._event_log),
        }


webhook_manager = WebhookManager()
