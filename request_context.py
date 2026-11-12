"""İstek başına korelasyon kimliği ve aşama süreleri (embedding, arama, model).

ContextVar kullanır: eşzamanlı isteklerin değerleri birbirine karışmaz ve iş parçacığı havuzuna
çalışırken bağlam kopyalanır. Zaman aşımı gibi gecikme sorunlarını aşama aşama ayırmak içindir.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4

_correlation: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_stages: ContextVar[dict | None] = ContextVar("stage_ms", default=None)


def new_correlation() -> str:
    value = str(uuid4())
    _correlation.set(value)
    return value


def correlation_id() -> str:
    return _correlation.get() or new_correlation()


def begin_stages() -> None:
    """Yeni bir aşama ölçümü başlatır; sözlük paylaşıldığı için alt çağrılar aynı sözlüğe yazar."""
    _stages.set({})


def stages_snapshot() -> dict:
    return dict(_stages.get() or {})


@contextmanager
def stage(name: str):
    started = time.perf_counter()
    try:
        yield
    finally:
        record = _stages.get()
        if record is not None:
            record[name] = record.get(name, 0) + round((time.perf_counter() - started) * 1000)
