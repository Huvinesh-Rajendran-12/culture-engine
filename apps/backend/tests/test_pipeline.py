"""Tests for the Mind delegation pipeline."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from backend.mind.config import MAX_STREAM_EVENTS, MAX_TEXT_DELTA_EVENTS
from backend.mind.memory import MemoryManager
from backend.mind.schema import MindProfile
from backend.mind.store import MindStore


def _create_stores(tmp_dir: str):
    db_path = Path(tmp_dir) / "test.db"
    store = MindStore(db_path)
    mem = MemoryManager(db_path)
    return store, mem


def _create_mind(store: MindStore, name: str = "TestMind") -> MindProfile:
    mind = MindProfile(name=name, personality="helpful")
    store.save_mind(mind)
    return mind


async def _collect(agen):
    events = []
    async for event in agen:
        events.append(event)
    return events


# ---------------------------------------------------------------------------
# Fake run_agent generators
# ---------------------------------------------------------------------------


def _make_fake_run_agent(events):
    """Return a fake run_agent that yields the given event dicts."""

    async def fake_run_agent(prompt, system_prompt, workspace_dir, team, **kwargs):
        for e in events:
            yield e

    return fake_run_agent


def _make_fake_run_agent_raises(events_before, exc):
    """Return a fake run_agent that yields some events then raises."""

    async def fake_run_agent(prompt, system_prompt, workspace_dir, team, **kwargs):
        for e in events_before:
            yield e
        raise exc

    return fake_run_agent


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestDelegateHappyPath(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store, self.mem = _create_stores(self.tmp)
        self.mind = _create_mind(self.store)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    @patch("backend.mind.pipeline.run_agent")
    @patch("backend.mind.pipeline.create_mind_tools", return_value=[])
    async def test_happy_path(self, _mock_tools, mock_run_agent):
        mock_run_agent.side_effect = _make_fake_run_agent(
            [
                {"type": "text", "content": "Hello from mind"},
                {
                    "type": "result",
                    "content": {
                        "subtype": "completed",
                        "final_text": "Task done",
                        "stop_reason": "end_turn",
                        "error_message": None,
                        "cost_usd": 0,
                        "usage": None,
                    },
                },
            ]
        )

        from backend.mind.pipeline import delegate_to_mind

        events = await _collect(
            delegate_to_mind(
                mind_store=self.store,
                memory_manager=self.mem,
                mind_id=self.mind.id,
                description="Do something",
            )
        )

        types = [e["type"] for e in events]
        self.assertEqual(types[0], "task_started")
        self.assertEqual(types[1], "memory_context")
        self.assertIn("tool_registry", types)
        self.assertIn("text", types)
        self.assertIn("result", types)

        # task_result and mind_insight auto-saved
        memory_saved_events = [e for e in events if e["type"] == "memory_saved"]
        categories = [e["content"]["category"] for e in memory_saved_events]
        self.assertIn("task_result", categories)
        self.assertIn("mind_insight", categories)

        # task_finished is last
        self.assertEqual(types[-1], "task_finished")
        finish = events[-1]
        self.assertEqual(finish["content"]["status"], "completed")

        # Task persisted in store
        task_id = events[0]["content"]["task_id"]
        persisted = self.store.load_task(self.mind.id, task_id)
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.status, "completed")

        # Trace persisted
        trace = self.store.load_task_trace(self.mind.id, task_id)
        self.assertIsNotNone(trace)
        self.assertGreater(len(trace["events"]), 0)


# ---------------------------------------------------------------------------
# Agent error result
# ---------------------------------------------------------------------------


class TestDelegateAgentErrorResult(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store, self.mem = _create_stores(self.tmp)
        self.mind = _create_mind(self.store)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    @patch("backend.mind.pipeline.run_agent")
    @patch("backend.mind.pipeline.create_mind_tools", return_value=[])
    async def test_error_result_sets_failed(self, _mock_tools, mock_run_agent):
        mock_run_agent.side_effect = _make_fake_run_agent(
            [
                {
                    "type": "result",
                    "content": {
                        "subtype": "error",
                        "error_message": "something broke",
                        "final_text": None,
                        "stop_reason": "error",
                        "cost_usd": 0,
                        "usage": None,
                    },
                },
            ]
        )

        from backend.mind.pipeline import delegate_to_mind

        events = await _collect(
            delegate_to_mind(
                mind_store=self.store,
                memory_manager=self.mem,
                mind_id=self.mind.id,
                description="Failing task",
            )
        )

        types = [e["type"] for e in events]
        self.assertEqual(types[-1], "task_finished")
        self.assertEqual(events[-1]["content"]["status"], "failed")

        # Avoid double error signaling when result subtype=error already emitted.
        error_events = [e for e in events if e["type"] == "error"]
        self.assertEqual(len(error_events), 0)

        result_error_events = [
            e
            for e in events
            if e["type"] == "result"
            and isinstance(e.get("content"), dict)
            and e["content"].get("subtype") == "error"
        ]
        self.assertEqual(len(result_error_events), 1)

        # Insight still saved on failure
        insight_events = [
            e
            for e in events
            if e["type"] == "memory_saved"
            and e["content"]["category"] == "mind_insight"
        ]
        self.assertEqual(len(insight_events), 1)

        # Task persisted as failed
        task_id = events[0]["content"]["task_id"]
        persisted = self.store.load_task(self.mind.id, task_id)
        self.assertEqual(persisted.status, "failed")


# ---------------------------------------------------------------------------
# Agent exception
# ---------------------------------------------------------------------------


class TestDelegateAgentException(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store, self.mem = _create_stores(self.tmp)
        self.mind = _create_mind(self.store)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    @patch("backend.mind.pipeline.run_agent")
    @patch("backend.mind.pipeline.create_mind_tools", return_value=[])
    async def test_exception_sets_failed_and_traces(self, _mock_tools, mock_run_agent):
        mock_run_agent.side_effect = _make_fake_run_agent_raises(
            [{"type": "text", "content": "partial output"}],
            RuntimeError("LLM connection lost"),
        )

        from backend.mind.pipeline import delegate_to_mind

        events = await _collect(
            delegate_to_mind(
                mind_store=self.store,
                memory_manager=self.mem,
                mind_id=self.mind.id,
                description="Exploding task",
            )
        )

        types = [e["type"] for e in events]
        self.assertEqual(types[-1], "task_finished")
        self.assertEqual(events[-1]["content"]["status"], "failed")
        self.assertIn("error", types)

        # Trace still persisted
        task_id = events[0]["content"]["task_id"]
        trace = self.store.load_task_trace(self.mind.id, task_id)
        self.assertIsNotNone(trace)
        self.assertGreater(len(trace["events"]), 0)


# ---------------------------------------------------------------------------
# Event limit enforcement
# ---------------------------------------------------------------------------


class TestDelegateEventLimit(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store, self.mem = _create_stores(self.tmp)
        self.mind = _create_mind(self.store)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    @patch("backend.mind.pipeline.run_agent")
    @patch("backend.mind.pipeline.create_mind_tools", return_value=[])
    async def test_stream_event_limit(self, _mock_tools, mock_run_agent):
        # tool_registry is yielded by execute_task before run_agent events,
        # and counts toward non-text-delta events. So we need enough
        # non-text-delta events from run_agent to push over the limit.
        over_limit = [
            {"type": "tool_use", "content": {"tool": "t", "input": {}}}
            for _ in range(MAX_STREAM_EVENTS + 1)
        ]
        mock_run_agent.side_effect = _make_fake_run_agent(over_limit)

        from backend.mind.pipeline import delegate_to_mind

        events = await _collect(
            delegate_to_mind(
                mind_store=self.store,
                memory_manager=self.mem,
                mind_id=self.mind.id,
                description="Overflow task",
            )
        )

        types = [e["type"] for e in events]
        self.assertEqual(types[-1], "task_finished")
        self.assertEqual(events[-1]["content"]["status"], "failed")

        error_events = [e for e in events if e["type"] == "error"]
        error_texts = " ".join(e["content"] for e in error_events)
        self.assertIn("Event limit reached", error_texts)


# ---------------------------------------------------------------------------
# Text delta limit enforcement
# ---------------------------------------------------------------------------


class TestDelegateTextDeltaLimit(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store, self.mem = _create_stores(self.tmp)
        self.mind = _create_mind(self.store)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    @patch("backend.mind.pipeline.run_agent")
    @patch("backend.mind.pipeline.create_mind_tools", return_value=[])
    async def test_text_delta_limit(self, _mock_tools, mock_run_agent):
        over_limit = [
            {"type": "text_delta", "content": "x"}
            for _ in range(MAX_TEXT_DELTA_EVENTS + 1)
        ]
        mock_run_agent.side_effect = _make_fake_run_agent(over_limit)

        from backend.mind.pipeline import delegate_to_mind

        events = await _collect(
            delegate_to_mind(
                mind_store=self.store,
                memory_manager=self.mem,
                mind_id=self.mind.id,
                description="Delta overflow",
            )
        )

        types = [e["type"] for e in events]
        self.assertEqual(types[-1], "task_finished")
        self.assertEqual(events[-1]["content"]["status"], "failed")

        error_events = [e for e in events if e["type"] == "error"]
        error_texts = " ".join(e["content"] for e in error_events)
        self.assertIn("Text delta limit reached", error_texts)


# ---------------------------------------------------------------------------
# Mind not found
# ---------------------------------------------------------------------------


class TestDelegateMindNotFound(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store, self.mem = _create_stores(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    async def test_nonexistent_mind(self):
        from backend.mind.pipeline import delegate_to_mind

        events = await _collect(
            delegate_to_mind(
                mind_store=self.store,
                memory_manager=self.mem,
                mind_id="does-not-exist",
                description="Whatever",
            )
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "error")
        self.assertIn("not found", events[0]["content"])


# ---------------------------------------------------------------------------
# Drone trace persistence on failure
# ---------------------------------------------------------------------------


class TestDroneTraceOnFailure(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store, self.mem = _create_stores(self.tmp)
        self.mind = _create_mind(self.store)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    @patch("backend.mind.pipeline.run_agent")
    @patch("backend.mind.pipeline.create_mind_tools")
    async def test_drone_trace_saved_on_failure(
        self, mock_create_mind_tools, mock_run_agent
    ):
        """When a spawned drone run raises, its trace and failed status are still saved."""
        captured_spawn_agent = None
        main_spawn_calls = 0

        def fake_create_mind_tools(*, spawn_agent_fn, include_spawn_agent, **kwargs):
            nonlocal captured_spawn_agent
            if include_spawn_agent:
                captured_spawn_agent = spawn_agent_fn
            return []

        async def fake_run_agent(prompt, system_prompt, workspace_dir, team, **kwargs):
            nonlocal main_spawn_calls

            if prompt.startswith("[Drone Objective]"):
                yield {"type": "text", "content": "drone partial"}
                raise RuntimeError("drone exploded")

            if captured_spawn_agent is None:
                raise AssertionError("spawn_agent callback was not captured")
            main_spawn_calls += 1
            drone_result = await captured_spawn_agent("sub task", 3)
            self.assertIn("Drone failed: drone exploded", drone_result)

            yield {
                "type": "result",
                "content": {
                    "subtype": "completed",
                    "final_text": "main result",
                    "stop_reason": "end_turn",
                    "error_message": None,
                    "cost_usd": 0,
                    "usage": None,
                },
            }

        mock_create_mind_tools.side_effect = fake_create_mind_tools
        mock_run_agent.side_effect = fake_run_agent

        from backend.mind.pipeline import delegate_to_mind

        events = await _collect(
            delegate_to_mind(
                mind_store=self.store,
                memory_manager=self.mem,
                mind_id=self.mind.id,
                description="Main task with failing drone",
            )
        )

        self.assertEqual(main_spawn_calls, 1)
        task_id = events[0]["content"]["task_id"]

        drones = self.store.list_drones(self.mind.id, task_id)
        self.assertEqual(len(drones), 1)
        self.assertEqual(drones[0].status, "failed")
        self.assertIsNotNone(drones[0].result)
        self.assertIn("drone exploded", drones[0].result or "")

        loaded_trace = self.store.load_drone_trace(self.mind.id, drones[0].id)
        self.assertIsNotNone(loaded_trace)
        if loaded_trace is None:
            self.fail("Expected persisted drone trace")
        self.assertEqual(len(loaded_trace["events"]), 1)
        self.assertEqual(loaded_trace["events"][0]["type"], "text")


if __name__ == "__main__":
    unittest.main()
