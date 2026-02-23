"""Tests for core domain logic in the Culture Engine Mind system."""

import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from backend.mind.config import MAX_MEMORY_CONTEXT_ITEMS
from backend.mind.events import Event, EventStream
from backend.mind.memory import _build_fts_query
from backend.mind.pipeline import (
    _build_autonomous_insight,
    _event_type_counts,
    _merge_memory_context,
)
from backend.mind.reasoning import build_system_prompt
from backend.mind.schema import MemoryEntry, MindCharter, MindProfile


def _mem(
    mind_id: str = "m1", content: str = "c", *, id: str | None = None
) -> MemoryEntry:
    kwargs = {"mind_id": mind_id, "content": content}
    if id is not None:
        kwargs["id"] = id
    return MemoryEntry(**kwargs)


# ---------------------------------------------------------------------------
# _merge_memory_context
# ---------------------------------------------------------------------------


class TestMergeMemoryContext(unittest.TestCase):
    def test_priority_ordering(self):
        a = _mem(id="a", content="first")
        b = _mem(id="b", content="second")
        result = _merge_memory_context([[a], [b]], limit=10)
        self.assertEqual([e.id for e in result], ["a", "b"])

    def test_deduplication(self):
        a = _mem(id="dup", content="x")
        b = _mem(id="dup", content="y")
        result = _merge_memory_context([[a], [b]], limit=10)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "dup")

    def test_limit_enforcement(self):
        entries = [_mem(id=str(i)) for i in range(5)]
        result = _merge_memory_context([entries], limit=3)
        self.assertEqual(len(result), 3)

    def test_empty_groups(self):
        result = _merge_memory_context([[], []], limit=10)
        self.assertEqual(result, [])
        result2 = _merge_memory_context([], limit=10)
        self.assertEqual(result2, [])

    def test_limit_zero_returns_empty(self):
        a = _mem(id="a")
        result = _merge_memory_context([[a]], limit=0)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# _event_type_counts
# ---------------------------------------------------------------------------


class TestEventTypeCounts(unittest.TestCase):
    def test_counts_correctly(self):
        events = [
            {"type": "text"},
            {"type": "text"},
            {"type": "tool_use"},
        ]
        counts = _event_type_counts(events)
        self.assertEqual(counts, {"text": 2, "tool_use": 1})

    def test_empty_list(self):
        self.assertEqual(_event_type_counts([]), {})

    def test_missing_type_key(self):
        events = [{"content": "hello"}, {"type": "text"}]
        counts = _event_type_counts(events)
        self.assertEqual(counts, {"text": 1})


# ---------------------------------------------------------------------------
# _build_autonomous_insight
# ---------------------------------------------------------------------------


class TestBuildAutonomousInsight(unittest.TestCase):
    def test_completed_task(self):
        text, keywords = _build_autonomous_insight(
            description="Run tests",
            status="completed",
            latest_text="All passed",
            failure_reason=None,
            feedback_context_count=0,
            implicit_context_count=0,
            event_counts={},
        )
        self.assertIn("Run tests", text)
        self.assertIn("completed", text)

    def test_failed_task(self):
        text, keywords = _build_autonomous_insight(
            description="Deploy",
            status="failed",
            latest_text=None,
            failure_reason="timeout",
            feedback_context_count=0,
            implicit_context_count=0,
            event_counts={},
        )
        self.assertIn("timeout", text)
        self.assertIn("failure", keywords)

    def test_keywords_always_include_base(self):
        _, keywords = _build_autonomous_insight(
            description="x",
            status="completed",
            latest_text=None,
            failure_reason=None,
            feedback_context_count=0,
            implicit_context_count=0,
            event_counts={},
        )
        self.assertIn("insight", keywords)
        self.assertIn("learning", keywords)
        self.assertIn("completed", keywords)

    def test_long_latest_text_truncated(self):
        long_text = "A" * 300
        text, _ = _build_autonomous_insight(
            description="x",
            status="completed",
            latest_text=long_text,
            failure_reason=None,
            feedback_context_count=0,
            implicit_context_count=0,
            event_counts={},
        )
        self.assertIn("...", text)
        self.assertNotIn("A" * 300, text)

    def test_context_counts_appear(self):
        text, _ = _build_autonomous_insight(
            description="x",
            status="completed",
            latest_text=None,
            failure_reason=None,
            feedback_context_count=3,
            implicit_context_count=2,
            event_counts={},
        )
        self.assertIn("Feedback memories considered: 3", text)
        self.assertIn("Implicit signals considered: 2", text)

    def test_context_counts_absent_when_zero(self):
        text, _ = _build_autonomous_insight(
            description="x",
            status="completed",
            latest_text=None,
            failure_reason=None,
            feedback_context_count=0,
            implicit_context_count=0,
            event_counts={},
        )
        self.assertNotIn("Feedback memories considered", text)
        self.assertNotIn("Implicit signals considered", text)


# ---------------------------------------------------------------------------
# EventStream
# ---------------------------------------------------------------------------


class TestEventStream(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    async def _gen(items: list[dict]):
        for item in items:
            yield item

    async def test_sequential_seq(self):
        stream = EventStream(self._gen([{"type": "a"}, {"type": "b"}]), trace_id="t1")
        events = [e async for e in stream]
        self.assertEqual([e.seq for e in events], [0, 1])

    async def test_trace_id(self):
        stream = EventStream(self._gen([{"type": "x"}]), trace_id="trace-abc")
        events = [e async for e in stream]
        self.assertEqual(events[0].trace_id, "trace-abc")

    async def test_unique_ids(self):
        stream = EventStream(
            self._gen([{"type": "a"}, {"type": "b"}, {"type": "c"}]),
            trace_id="t",
        )
        events = [e async for e in stream]
        ids = [e.id for e in events]
        self.assertEqual(len(ids), len(set(ids)))

    async def test_missing_type_defaults_to_unknown(self):
        stream = EventStream(self._gen([{"content": "hi"}]), trace_id="t")
        events = [e async for e in stream]
        self.assertEqual(events[0].type, "unknown")

    async def test_content_preserved(self):
        stream = EventStream(
            self._gen([{"type": "text", "content": "hello world"}]),
            trace_id="t",
        )
        events = [e async for e in stream]
        self.assertEqual(events[0].content, "hello world")


# ---------------------------------------------------------------------------
# _build_fts_query
# ---------------------------------------------------------------------------


class TestBuildFtsQuery(unittest.TestCase):
    def test_normal_query(self):
        result = _build_fts_query("hello world")
        self.assertEqual(result, "hello OR world")

    def test_special_characters_stripped(self):
        result = _build_fts_query("hello! @world#")
        self.assertEqual(result, "hello OR world")

    def test_empty_string(self):
        self.assertEqual(_build_fts_query(""), "")

    def test_single_token(self):
        self.assertEqual(_build_fts_query("test"), "test")

    def test_mixed_case_lowered(self):
        self.assertEqual(_build_fts_query("Hello World"), "hello OR world")

    def test_punctuation_only(self):
        self.assertEqual(_build_fts_query("!@#$%"), "")


# ---------------------------------------------------------------------------
# build_system_prompt
# ---------------------------------------------------------------------------


class TestBuildSystemPrompt(unittest.TestCase):
    def _mind(self, **overrides) -> MindProfile:
        defaults = {
            "name": "TestMind",
            "personality": "helpful",
            "charter": MindCharter(mission="Do good things"),
        }
        defaults.update(overrides)
        return MindProfile(**defaults)

    def test_includes_mind_name(self):
        prompt = build_system_prompt(self._mind(), [])
        self.assertIn("TestMind", prompt)

    def test_includes_personality(self):
        prompt = build_system_prompt(self._mind(personality="witty"), [])
        self.assertIn("witty", prompt)

    def test_excludes_empty_personality(self):
        prompt = build_system_prompt(self._mind(personality=""), [])
        self.assertNotIn("Personality:", prompt)

    def test_includes_charter_mission(self):
        prompt = build_system_prompt(self._mind(), [])
        self.assertIn("Do good things", prompt)

    def test_includes_memory_content(self):
        mem = _mem(content="Remember this fact", mind_id="m1")
        mem.category = "general"
        prompt = build_system_prompt(self._mind(), [mem])
        self.assertIn("Remember this fact", prompt)

    def test_includes_runtime_manifest(self):
        manifest = {
            "tool_names": ["run_command", "memory_save"],
            "limits": {"max_turns": 5},
        }
        prompt = build_system_prompt(self._mind(), [], manifest)
        self.assertIn("run_command", prompt)
        self.assertIn("max_turns", prompt)

    def test_memory_context_respects_configured_cap(self):
        memories = [
            _mem(content=f"memory-{i}", mind_id="m1", id=f"m{i}")
            for i in range(MAX_MEMORY_CONTEXT_ITEMS + 2)
        ]
        prompt = build_system_prompt(self._mind(), memories)

        for i in range(MAX_MEMORY_CONTEXT_ITEMS):
            self.assertIn(f"memory-{i}", prompt)
        self.assertNotIn(f"memory-{MAX_MEMORY_CONTEXT_ITEMS}", prompt)

    def test_includes_meta_conversation_policy(self):
        prompt = build_system_prompt(self._mind(), [])
        self.assertIn("Meta conversation policy:", prompt)

    def test_truncates_long_memory(self):
        long_content = "X" * 500
        mem = _mem(content=long_content, mind_id="m1")
        prompt = build_system_prompt(self._mind(), [mem])
        self.assertNotIn("X" * 500, prompt)
        self.assertIn("X" * 400, prompt)
        self.assertIn("...", prompt)


if __name__ == "__main__":
    unittest.main()
