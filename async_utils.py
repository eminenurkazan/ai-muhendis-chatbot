"""Asenkron kuralları: olay döngüsünü bloklamamak, sınırlı eşzamanlılık ve zaman aşımı.

Kurallar (uygulamanın tamamı için):
- Uç noktalar ``async def``; ağ/veritabanı/disk bekleyen eşzamanlı kod doğrudan çağrılmaz,
  ``run_blocking`` ile sınırlı bir iş parçacığı havuzunda çalıştırılır (pyodbc ve kayıtlı model oturumu
  kodu eşzamanlıdır; sürücüleri bu yüzden ``await`` edilemez).
- Bekleme süresi olan her aşamada zaman aşımı vardır; iptal (istemci kopması) ``CancelledError`` ile
  yayılır ve yutulmaz. Zaman aşımında iş parçacığı kendiliğinden durdurulamaz: sonucu atılır ve
  havuz sınırı bu işlerin sayısını sınırlar.
- Yavaş ve kotalı model çağrıları bir eşzamanlılık kapısından (``Gate``) geçer.
"""
from __future__ import annotations

import asyncio
import os
import weakref
from functools import partial
from typing import Awaitable, Callable, TypeVar

import anyio
from anyio import to_thread

T = TypeVar("T")


def _int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


BLOCKING_THREADS = _int_env("BLOCKING_THREADS", 32, 2, 256)
MAX_CONCURRENT_LLM = _int_env("RAG_MAX_CONCURRENT_LLM", 4, 1, 32)
GATE_WAIT_SECONDS = _int_env("RAG_QUEUE_WAIT_SECONDS", 30, 1, 300)
STAGE_TIMEOUTS = {
    "embed": _int_env("RAG_EMBED_TIMEOUT", 45, 5, 300),
    "retrieve": _int_env("RAG_RETRIEVE_TIMEOUT", 30, 5, 300),
    "llm": _int_env("RAG_LLM_TIMEOUT", 140, 10, 600),
}

_limiters: "weakref.WeakKeyDictionary[object, anyio.CapacityLimiter]" = weakref.WeakKeyDictionary()
_gates: "weakref.WeakKeyDictionary[object, asyncio.Semaphore]" = weakref.WeakKeyDictionary()


class StageTimeout(Exception):
    """Bir aşama süresini aştı; ``stage`` hangi aşama olduğunu söyler (kullanıcıya güvenli)."""

    def __init__(self, stage: str, seconds: float):
        super().__init__(f"{stage} aşaması {seconds:g} saniyede tamamlanamadı.")
        self.stage = stage
        self.seconds = seconds


class Busy(Exception):
    """Eşzamanlılık kapısında sıra beklenen süre aşıldı."""


def _loop_key():
    # Her olay döngüsünün kendi sınırlayıcısı vardır (testlerde döngü sık yenilenir).
    return asyncio.get_running_loop()


def _limiter() -> anyio.CapacityLimiter:
    key = _loop_key()
    if key not in _limiters:
        _limiters[key] = anyio.CapacityLimiter(BLOCKING_THREADS)
    return _limiters[key]


async def run_blocking(function: Callable[..., T], *args, **kwargs) -> T:
    """Eşzamanlı işlevi olay döngüsünü bloklamadan çalıştırır; bağlam (korelasyon kimliği) taşınır."""
    return await to_thread.run_sync(partial(function, *args, **kwargs), limiter=_limiter())


async def with_timeout(stage: str, awaitable: Awaitable[T], seconds: float | None = None) -> T:
    limit = STAGE_TIMEOUTS.get(stage, 60) if seconds is None else seconds
    try:
        async with asyncio.timeout(limit):
            return await awaitable
    except TimeoutError:
        raise StageTimeout(stage, limit) from None


class Gate:
    """Eşzamanlı çağrı sayısını sınırlar; sıra bekleyen istekler olay döngüsünü tutmaz."""

    def __init__(self, size: int | None = None, wait_seconds: float | None = None):
        self.size = size
        self.wait_seconds = wait_seconds

    def _semaphore(self) -> asyncio.Semaphore:
        key = _loop_key()
        if key not in _gates:
            _gates[key] = asyncio.Semaphore(self.size or MAX_CONCURRENT_LLM)
        return _gates[key]

    async def run(self, factory: Callable[[], Awaitable[T]]) -> T:
        semaphore = self._semaphore()
        try:
            async with asyncio.timeout(self.wait_seconds or GATE_WAIT_SECONDS):
                await semaphore.acquire()
        except TimeoutError:
            raise Busy("Yanıt hizmeti yoğun. Biraz bekleyip tekrar deneyebilirsin.") from None
        try:
            return await factory()
        finally:
            semaphore.release()


llm_gate = Gate()
