"""Circuit Breaker — حماية عند فشل الخدمات الخارجية"""
from datetime import datetime, timedelta
from collections import defaultdict

class CircuitBreaker:
    def __init__(self, fail_threshold=3, reset_seconds=60):
        self.threshold = fail_threshold
        self.reset_secs = reset_seconds
        self._failures: dict = defaultdict(list)
        self._open_until: dict = {}

    def is_open(self, service: str) -> bool:
        if service in self._open_until:
            if datetime.utcnow() < self._open_until[service]:
                return True
            else:
                del self._open_until[service]
                self._failures[service] = []
        return False

    def record_failure(self, service: str):
        now = datetime.utcnow()
        self._failures[service].append(now)
        recent = [t for t in self._failures[service]
                  if (now - t).total_seconds() < 120]
        self._failures[service] = recent
        if len(recent) >= self.threshold:
            self._open_until[service] = now + timedelta(seconds=self.reset_secs)

    def record_success(self, service: str):
        self._failures[service] = []
        self._open_until.pop(service, None)

    def status(self) -> dict:
        return {s: "open" if self.is_open(s) else "closed"
                for s in set(list(self._failures.keys()) + list(self._open_until.keys()))}

circuit_breaker = CircuitBreaker()
