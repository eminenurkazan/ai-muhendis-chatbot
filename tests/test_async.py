"""Asenkron düzen: olay döngüsü bloklanmaz, eşzamanlılık gerçektir, zaman aşımı ve sıra kapısı çalışır."""
import asyncio
import inspect
import time
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx

import api
import async_utils
import chat_service
import kb_api
import rag_service
from async_utils import Busy, Gate, StageTimeout, run_blocking, with_timeout
from request_replay import ReplayConflict, ReplayStore


def endpoints(routes):
    for route in routes:
        if hasattr(route, "endpoint"):
            yield route
        elif hasattr(route, "original_router"):
            yield from endpoints(route.original_router.routes)


class StructureTests(unittest.TestCase):
    def test_every_http_endpoint_and_auth_dependency_is_async(self):
        import admin_api
        import auth_api
        found = [r for r in endpoints(api.app.router.routes) if r.path not in {"/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"}]
        self.assertGreaterEqual(len(found), 19)
        blocking = [r.path for r in found if not inspect.iscoroutinefunction(r.endpoint)]
        self.assertEqual(blocking, [], "Eşzamanlı (def) uç noktalar kaldı")
        self.assertTrue(inspect.iscoroutinefunction(auth_api.require_user))
        self.assertTrue(inspect.iscoroutinefunction(admin_api.require_admin))


class RunBlockingTests(unittest.IsolatedAsyncioTestCase):
    async def test_blocking_call_does_not_block_the_event_loop(self):
        ticks = []

        async def heartbeat():
            for _ in range(8):
                ticks.append(time.perf_counter())
                await asyncio.sleep(0.02)

        started = time.perf_counter()
        await asyncio.gather(run_blocking(time.sleep, 0.3), heartbeat())
        self.assertGreaterEqual(len(ticks), 8)
        # Döngü bloklansaydı ilk iki tik arasında ~0,3 sn boşluk olurdu.
        self.assertLess(max(b - a for a, b in zip(ticks, ticks[1:])), 0.15)
        self.assertLess(time.perf_counter() - started, 0.6)

    async def test_calls_run_concurrently_not_serially(self):
        started = time.perf_counter()
        await asyncio.gather(*(run_blocking(time.sleep, 0.3) for _ in range(6)))
        self.assertLess(time.perf_counter() - started, 0.9)  # seri olsaydı >= 1,8 sn

    async def test_thread_limit_is_enforced(self):
        active, peak = [0], [0]
        import threading
        lock = threading.Lock()

        def work():
            with lock:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
            time.sleep(0.1)
            with lock:
                active[0] -= 1
        with patch.object(async_utils, "BLOCKING_THREADS", 3):
            async_utils._limiters.clear()
            await asyncio.gather(*(run_blocking(work) for _ in range(9)))
        async_utils._limiters.clear()
        self.assertLessEqual(peak[0], 3)

    async def test_exceptions_propagate_and_context_is_carried(self):
        import request_context
        request_context.begin_stages()

        def inner():
            with request_context.stage("embed"):
                pass
            raise ValueError("kaynak hatası")
        with self.assertRaises(ValueError):
            await run_blocking(inner)
        self.assertIn("embed", request_context.stages_snapshot())  # iş parçacığında yazılan ölçüm görünür


class TimeoutAndGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_names_the_stage(self):
        with self.assertRaises(StageTimeout) as error:
            await with_timeout("llm", asyncio.sleep(1), seconds=0.05)
        self.assertEqual(error.exception.stage, "llm")

    async def test_gate_limits_concurrency_and_releases_on_error(self):
        gate = Gate(size=2, wait_seconds=5)
        active, peak = [0], [0]

        async def job(fail=False):
            active[0] += 1
            peak[0] = max(peak[0], active[0])
            await asyncio.sleep(0.05)
            active[0] -= 1
            if fail:
                raise RuntimeError("model hatası")
            return "ok"
        results = await asyncio.gather(*(gate.run(lambda f=n == 1: job(f)) for n in range(6)), return_exceptions=True)
        self.assertEqual(peak[0], 2)
        self.assertEqual(sum(r == "ok" for r in results), 5)
        self.assertEqual(await gate.run(lambda: job()), "ok")  # hata sonrası yer serbest bırakıldı

    async def test_waiting_too_long_for_a_slot_is_busy(self):
        gate = Gate(size=1, wait_seconds=0.05)
        holder = asyncio.create_task(gate.run(lambda: asyncio.sleep(0.5)))
        await asyncio.sleep(0.02)
        with self.assertRaises(Busy):
            await gate.run(lambda: asyncio.sleep(0))
        holder.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await holder
        self.assertEqual(await gate.run(lambda: asyncio.sleep(0, "free")), "free")  # iptal yer bıraktı


class AskPipelineTests(unittest.IsolatedAsyncioTestCase):
    MATCHES = [(0.9, {"issueid": "1007444.0"})]
    ANSWER = {"answer": "Ticket: 1007444.0", "used_ticket_ids": ["1007444.0"], "insufficient_context": False}

    def patches(self, **overrides):
        values = {"rag_provider.embed_question": MagicMock(return_value=[0.1]),
                  "rag_repository.search_matches": MagicMock(return_value=self.MATCHES),
                  "rag_provider.answer_from_matches": MagicMock(return_value=self.ANSWER)}
        values.update(overrides)
        stack = [patch(name, new=mock) for name, mock in values.items()]
        for item in stack:
            item.start()
            self.addCleanup(item.stop)
        return values

    async def test_same_result_as_sync_pipeline_with_stage_timings(self):
        self.patches()
        sync_result = rag_service.ask_question("  UAT sorusu  ", expertise_mode="windows_server")
        async_result = await rag_service.ask_question_async("  UAT sorusu  ", expertise_mode="windows_server")
        for key in ("answer", "used_ticket_ids", "retrieved_ticket_ids", "expertise_mode", "prompt_version", "sources"):
            self.assertEqual(async_result[key], sync_result[key])
        self.assertEqual(set(async_result["stage_ms"]), {"embed", "retrieve", "llm"})

    async def test_validation_happens_before_any_call(self):
        mocks = self.patches()
        for question, mode in (("  ", "service_desk"), ("x" * 2001, "service_desk"), ("soru", "bilinmeyen")):
            with self.assertRaises(ValueError):
                await rag_service.ask_question_async(question, expertise_mode=mode)
        mocks["rag_provider.embed_question"].assert_not_called()

    async def test_slow_stage_times_out_with_a_readable_503_message(self):
        self.patches(**{"rag_provider.embed_question": MagicMock(side_effect=lambda q: time.sleep(0.5) or [0.1])})
        with patch.dict(async_utils.STAGE_TIMEOUTS, {"embed": 0.05}):
            with self.assertRaises(rag_service.ServiceUnavailable) as error:
                await rag_service.ask_question_async("soru")
        self.assertIn("Soru embedding'i", str(error.exception))

    async def test_busy_gate_becomes_service_unavailable(self):
        self.patches()
        with patch.object(rag_service, "llm_gate", Gate(size=1, wait_seconds=0.05)):
            blocker = asyncio.create_task(rag_service.llm_gate.run(lambda: asyncio.sleep(0.5)))
            await asyncio.sleep(0.02)
            with self.assertRaises(rag_service.ServiceUnavailable):
                await rag_service.ask_question_async("soru")
            blocker.cancel()

    async def test_concurrent_questions_overlap(self):
        self.patches(**{"rag_provider.answer_from_matches": MagicMock(side_effect=lambda *a, **k: time.sleep(0.3) or self.ANSWER)})
        started = time.perf_counter()
        results = await asyncio.gather(*(rag_service.ask_question_async(f"soru {n}") for n in range(4)))
        self.assertEqual(len(results), 4)
        self.assertLess(time.perf_counter() - started, 0.9)  # 4 x 0,3 sn seri olsaydı >= 1,2 sn


class ReplayAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_second_call_returns_stored_result(self):
        store, calls = ReplayStore(), []

        async def operation():
            calls.append(1)
            return {"answer": "x"}
        first = await store.run_async("u", "r", {"q": 1}, operation)
        second = await store.run_async("u", "r", {"q": 1}, operation)
        self.assertEqual((first, second, len(calls)), ({"answer": "x"}, {"answer": "x"}, 1))
        with self.assertRaises(ReplayConflict):
            await store.run_async("u", "r", {"q": 2}, operation)

    async def test_failure_and_cancellation_do_not_leave_a_stuck_entry(self):
        store = ReplayStore()

        async def boom():
            raise RuntimeError("x")
        with self.assertRaises(RuntimeError):
            await store.run_async("u", "r1", {}, boom)
        task = asyncio.create_task(store.run_async("u", "r2", {}, lambda: asyncio.sleep(1)))
        await asyncio.sleep(0.02)
        with self.assertRaises(ReplayConflict):  # sürerken ikinci istek reddedilir
            await store.run_async("u", "r2", {}, lambda: asyncio.sleep(0))
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(await store.run_async("u", "r2", {}, lambda: asyncio.sleep(0, "again")), "again")
        self.assertEqual(await store.run_async("u", "r1", {}, lambda: asyncio.sleep(0, "retry")), "retry")


class AnswerChatAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_matches_sync_behaviour_and_releases_sql_during_generation(self):
        owner, chat, request = str(uuid4()), str(uuid4()), str(uuid4())
        events, saved = [], []

        class Repo:
            def turn_state(self, user, chat_id, request_id, lock=False):
                events.append("state-lock" if lock else "state")
                return {"session": {"expertise_mode": "oracle_db"}, "saved": [], "recent": [], "last_seq": 0}

            def save_turn(self, *args):
                saved.append(args)

        def fake_run(operation, *, write=False):
            events.append("sql-write" if write else "sql-read")
            return operation(Repo())

        async def generate(question, **options):
            events.append("generate")
            self.assertEqual(options["expertise_mode"], "oracle_db")
            return {"answer": "Yanıt", "used_source_ids": []}
        with patch.object(chat_service, "_run", side_effect=fake_run), patch.object(chat_service, "_generated_turns", ReplayStore()):
            result = await chat_service.answer_chat_async(owner, chat, "  Soru  ", request, generate)
        self.assertEqual(result["answer"], "Yanıt")
        self.assertEqual(saved[0][3], "Soru")
        # SQL okuma -> üretim -> yazma sırası; üretim sırasında bağlantı tutulmaz.
        self.assertEqual([e for e in events if e in {"sql-read", "generate", "sql-write"}], ["sql-read", "generate", "sql-write"])

    async def test_empty_question_is_rejected_before_sql(self):
        with patch.object(chat_service, "_run") as run, self.assertRaises(ValueError):
            await chat_service.answer_chat_async("u", "c", "   ", str(uuid4()), lambda *a, **k: None)
        run.assert_not_called()


class HttpConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_stays_fast_while_slow_questions_are_in_flight(self):
        api.app.dependency_overrides[api.require_user] = lambda: {"id": "u-1", "role": "user"}
        self.addCleanup(api.app.dependency_overrides.clear)
        answer = {"answer": "Ticket: 1", "used_ticket_ids": [], "insufficient_context": True}
        patches = [patch("rag_provider.embed_question", return_value=[0.1]),
                   patch("rag_repository.search_matches", return_value=[(0.9, {"issueid": "1"})]),
                   patch("rag_provider.answer_from_matches", side_effect=lambda *a, **k: time.sleep(0.5) or answer)]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        transport = httpx.ASGITransport(app=api.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=10) as client:
            started = time.perf_counter()
            slow = [asyncio.create_task(client.post("/ask", json={"question": f"soru {n}"})) for n in range(3)]
            await asyncio.sleep(0.1)
            health_started = time.perf_counter()
            health = await client.get("/health")
            health_time = time.perf_counter() - health_started
            responses = await asyncio.gather(*slow)
            total = time.perf_counter() - started
        self.assertEqual(health.json(), {"status": "ok"})
        self.assertLess(health_time, 0.25)
        self.assertEqual([r.status_code for r in responses], [200, 200, 200])
        self.assertLess(total, 1.3)  # 3 x 0,5 sn seri olsaydı >= 1,5 sn


class KnowledgeApproveConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_records_are_approved_in_parallel_batches_in_request_order(self):
        ids = [uuid4() for _ in range(6)]
        api.app.dependency_overrides[api.require_user] = lambda: {"id": str(uuid4()), "role": "admin"}
        self.addCleanup(api.app.dependency_overrides.clear)
        seen = []

        def slow_one(record_id):
            time.sleep(0.2)
            seen.append(record_id)
            return {"id": record_id, "status": "indexed", "message": ""}
        transport = httpx.ASGITransport(app=api.app)
        with patch.object(kb_api, "_approve_one", side_effect=slow_one):
            async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=10) as client:
                started = time.perf_counter()
                response = await client.post("/admin/kb/approve", json={"ids": [str(i) for i in ids]})
                elapsed = time.perf_counter() - started
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()["items"]], [str(i) for i in ids])
        self.assertLess(elapsed, 0.9)  # 6 x 0,2 sn seri >= 1,2 sn; 3'lü paralel ~0,4 sn


if __name__ == "__main__":
    unittest.main()
