"""Tests for Mind tool primitives (memory_save, memory_search, spawn_agent)."""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from backend.mind.memory import list_memories, save_memory, search_memory
from backend.mind.store import init_db
from backend.mind.tools.primitives import create_memory_tools, create_spawn_agent_tool

MIND_ID = "test-mind-1"


class _MemoryAdapter:
    """Thin duck-typed wrapper over memory free functions for use in tests."""

    def __init__(self, db_path: Path):
        self._db_path = db_path

    def save(self, entry):
        return save_memory(self._db_path, entry)

    def search(self, mind_id: str, query: str, top_k: int = 10):
        return search_memory(self._db_path, mind_id, query, top_k=top_k)

    def list_all(self, mind_id: str, category=None):
        return list_memories(self._db_path, mind_id, category=category)


class TestMemorySave(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db_path = Path(self._tmpdir) / "test.db"
        init_db(self._db_path).close()
        self.mm = _MemoryAdapter(self._db_path)
        tools = create_memory_tools(self.mm, MIND_ID)
        self.memory_save = tools[0]
        self.memory_search = tools[1]

    def tearDown(self):
        shutil.rmtree(self._tmpdir)

    async def test_saves_with_category_and_keywords(self):
        result = await self.memory_save.execute(
            "c1",
            {
                "content": "Python is great",
                "category": "tech",
                "relevance_keywords": ["python", "programming"],
            },
        )
        text = result.content[0].text
        self.assertTrue(text.startswith("Saved memory:"))

        entries = self.mm.list_all(MIND_ID)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].content, "Python is great")
        self.assertEqual(entries[0].category, "tech")
        self.assertEqual(entries[0].relevance_keywords, ["python", "programming"])

    async def test_saves_without_optional_fields(self):
        result = await self.memory_save.execute("c1", {"content": "bare memory"})
        text = result.content[0].text
        self.assertTrue(text.startswith("Saved memory:"))

        entries = self.mm.list_all(MIND_ID)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].content, "bare memory")
        self.assertIsNone(entries[0].category)
        self.assertEqual(entries[0].relevance_keywords, [])

    async def test_counter_resets_per_tool_instance(self):
        tools_a = create_memory_tools(self.mm, MIND_ID, max_saves=2)
        tools_b = create_memory_tools(self.mm, MIND_ID, max_saves=2)
        save_a = tools_a[0]
        save_b = tools_b[0]

        # Exhaust instance A's limit
        await save_a.execute("c1", {"content": "a1"})
        await save_a.execute("c2", {"content": "a2"})
        result_a3 = await save_a.execute("c3", {"content": "a3"})
        self.assertIn("limit reached", result_a3.content[0].text)

        # Instance B should still have its own independent counter
        result_b1 = await save_b.execute("c4", {"content": "b1"})
        self.assertTrue(result_b1.content[0].text.startswith("Saved memory:"))


class TestMemorySearch(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db_path = Path(self._tmpdir) / "test.db"
        init_db(self._db_path).close()
        self.mm = _MemoryAdapter(self._db_path)
        tools = create_memory_tools(self.mm, MIND_ID)
        self.memory_save = tools[0]
        self.memory_search = tools[1]

    def tearDown(self):
        shutil.rmtree(self._tmpdir)

    async def test_returns_matching_results(self):
        await self.memory_save.execute("c1", {"content": "Python web frameworks"})
        await self.memory_save.execute("c2", {"content": "Cooking pasta recipes"})
        await self.memory_save.execute("c3", {"content": "Python data analysis"})

        result = await self.memory_search.execute("c4", {"query": "Python"})
        entries = json.loads(result.content[0].text)
        self.assertGreaterEqual(len(entries), 2)
        contents = [e["content"] for e in entries]
        self.assertIn("Python web frameworks", contents)
        self.assertIn("Python data analysis", contents)

    async def test_returns_empty_for_no_matches(self):
        await self.memory_save.execute("c1", {"content": "Hello world"})

        result = await self.memory_search.execute("c2", {"query": "xyznonexistent"})
        entries = json.loads(result.content[0].text)
        self.assertEqual(entries, [])

    async def test_respects_top_k(self):
        for i in range(10):
            await self.memory_save.execute(
                f"c{i}", {"content": f"Alpha topic number {i}"}
            )

        result = await self.memory_search.execute(
            "s1", {"query": "Alpha", "top_k": 3}
        )
        entries = json.loads(result.content[0].text)
        self.assertLessEqual(len(entries), 3)
        self.assertGreater(len(entries), 0)


class TestSpawnAgent(unittest.IsolatedAsyncioTestCase):
    async def test_clamps_max_turns_down_to_cap(self):
        mock_spawn = AsyncMock(return_value="done")
        tool = create_spawn_agent_tool(mock_spawn, max_turns_cap=10)

        await tool.execute("c1", {"objective": "do stuff", "max_turns": 100})
        mock_spawn.assert_awaited_once_with("do stuff", 10)

    async def test_min_turns_is_one(self):
        mock_spawn = AsyncMock(return_value="done")
        tool = create_spawn_agent_tool(mock_spawn)

        await tool.execute("c1", {"objective": "do stuff", "max_turns": 0})
        mock_spawn.assert_awaited_once_with("do stuff", 1)

    async def test_default_max_turns(self):
        mock_spawn = AsyncMock(return_value="done")
        tool = create_spawn_agent_tool(mock_spawn)

        await tool.execute("c1", {"objective": "do stuff"})
        mock_spawn.assert_awaited_once_with("do stuff", 12)


if __name__ == "__main__":
    unittest.main()
