"""Result TTL Cache"""
from datetime import datetime, timedelta
from typing import Optional

class TTLCache:
    def __init__(self, ttl_seconds: int = 3600):
        self._store: dict = {}
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[dict]:
        if key in self._store:
            item = self._store[key]
            if datetime.utcnow() < item["expires"]:
                return item["data"]
            del self._store[key]
        return None

    def set(self, key: str, data: dict, ttl: int = None):
        self._store[key] = {
            "data": data,
            "expires": datetime.utcnow() + timedelta(seconds=ttl or self.ttl),
            "created": datetime.utcnow()
        }

    def invalidate(self, key: str):
        self._store.pop(key, None)

    def cleanup(self):
        now = datetime.utcnow()
        expired = [k for k, v in self._store.items() if now >= v["expires"]]
        for k in expired:
            del self._store[k]
        return len(expired)

    def size(self) -> int:
        return len(self._store)

result_cache = TTLCache(ttl_seconds=3600)
