"""Bounded replay protection for this single API process; no tokens stored."""
from copy import deepcopy
import hashlib
import json
from threading import Lock
import time


class ReplayConflict(Exception):
    pass


class ReplayBusy(Exception):
    pass


class ReplayStore:
    def __init__(self, capacity=128, ttl=600):
        self.capacity, self.ttl = capacity, ttl
        self.entries = {}
        self.lock = Lock()

    def run(self, owner, request_id, payload, operation):
        key = (str(owner), str(request_id))
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with self.lock:
            now = time.monotonic()
            for old_key, entry in list(self.entries.items()):
                if entry["done"] and now - entry["finished"] >= self.ttl:
                    del self.entries[old_key]
            if key in self.entries:
                entry = self.entries[key]
                if entry["fingerprint"] != fingerprint:
                    raise ReplayConflict("Aynı istek kimliği farklı bir soru için kullanılamaz.")
                if not entry["done"]:
                    raise ReplayConflict("Önceki istek hâlâ işleniyor. Biraz bekleyip tekrar deneyebilirsin.")
                return deepcopy(entry["result"])
            if len(self.entries) >= self.capacity:
                raise ReplayBusy("Yanıt hizmeti yoğun. Biraz bekleyip tekrar deneyebilirsin.")
            entry = {"fingerprint": fingerprint, "done": False}
            self.entries[key] = entry
        try:
            result = operation()
        except BaseException:
            with self.lock:
                self.entries.pop(key, None)
            raise
        with self.lock:
            entry.update(done=True, result=deepcopy(result), finished=time.monotonic())
        return result


replays = ReplayStore()
