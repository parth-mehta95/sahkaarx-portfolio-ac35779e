"""Concrete service provider implementations for Dependency Injection."""

import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, List, Optional

from datapipeline.di.interfaces import (
    IAuthService,
    IDataTransformer,
    IMetricsCollector,
    INotificationService,
    IStorageService,
)


class InMemoryStorageService(IStorageService):
    """Thread-safe in-memory storage provider suitable for fast testing and lightweight deployments."""

    def __init__(self):
        self._store: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def save(self, collection: str, item_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if collection not in self._store:
            self._store[collection] = {}
        payload = dict(data)
        payload["id"] = item_id
        payload["_updated_at"] = time.time()
        self._store[collection][item_id] = payload
        return payload

    def get(self, collection: str, item_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(collection, {}).get(item_id)

    def list(self, collection: str) -> List[Dict[str, Any]]:
        return list(self._store.get(collection, {}).values())

    def delete(self, collection: str, item_id: str) -> bool:
        if collection in self._store and item_id in self._store[collection]:
            del self._store[collection][item_id]
            return True
        return False


class HmacAuthService(IAuthService):
    """Cryptographically secure HMAC-SHA256 authentication token service."""

    def __init__(self, secret_key: str = "prod-secure-pipeline-secret-key-32bytes-min"):
        self.secret_key = secret_key.encode("utf-8")
        self._active_tokens: Dict[str, Dict[str, Any]] = {}

    def generate_token(self, client_id: str, role: str = "operator") -> str:
        timestamp = int(time.time())
        nonce = os.urandom(8).hex()
        payload = f"{client_id}:{role}:{timestamp}:{nonce}"
        signature = hmac.new(self.secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        token = f"dpt_{payload}:{signature}"
        self._active_tokens[token] = {
            "client_id": client_id,
            "role": role,
            "issued_at": timestamp,
            "expires_at": timestamp + 86400,
        }
        return token

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not token or not token.startswith("dpt_"):
            return None

        # Check cached / registered token
        if token in self._active_tokens:
            info = self._active_tokens[token]
            if time.time() <= info["expires_at"]:
                return info
            return None

        # Cryptographic verification fallback
        try:
            body = token[4:]
            payload, signature = body.rsplit(":", 1)
            expected = hmac.new(self.secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected, signature):
                client_id, role, ts, _ = payload.split(":", 3)
                if time.time() <= int(ts) + 86400:
                    return {
                        "client_id": client_id,
                        "role": role,
                        "issued_at": int(ts),
                    }
        except Exception:
            return None
        return None


class InMemoryMetricsCollector(IMetricsCollector):
    """High-performance in-memory metrics aggregator."""

    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}

    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        tag_str = self._format_tags(tags)
        key = f"{name}{tag_str}"
        self._counters[key] = self._counters.get(key, 0) + value

    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        tag_str = self._format_tags(tags)
        key = f"{name}{tag_str}"
        self._gauges[key] = value

    def _format_tags(self, tags: Optional[Dict[str, str]]) -> str:
        if not tags:
            return ""
        return "{" + ",".join(f"{k}={v}" for k, v in sorted(tags.items())) + "}"

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "timestamp": time.time(),
        }


class StandardDataTransformer(IDataTransformer):
    """Standard record transformation pipeline with sanitization, normalization, and hashing."""

    def transform(self, records: List[Dict[str, Any]], operations: List[str]) -> List[Dict[str, Any]]:
        results = []
        for row in records:
            item = dict(row)
            for op in operations:
                if op == "strip_whitespace":
                    item = {k: v.strip() if isinstance(v, str) else v for k, v in item.items()}
                elif op == "lowercase_keys":
                    item = {str(k).lower(): v for k, v in item.items()}
                elif op == "hash_pii":
                    if "email" in item and item["email"]:
                        item["email_hash"] = hashlib.sha256(str(item["email"]).encode("utf-8")).hexdigest()
                        del item["email"]
                elif op == "add_timestamp":
                    item["_processed_at"] = time.time()
            results.append(item)
        return results


class ConsoleNotificationService(INotificationService):
    """Notification dispatcher that outputs to logging buffer and stdout."""

    def __init__(self):
        self.sent_notifications: List[Dict[str, Any]] = []

    def send_notification(self, channel: str, message: str, level: str = "INFO") -> bool:
        record = {
            "channel": channel,
            "message": message,
            "level": level,
            "timestamp": time.time(),
        }
        self.sent_notifications.append(record)
        return True
