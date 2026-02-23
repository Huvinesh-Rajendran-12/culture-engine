import shutil
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from backend.mind.database import init_db
from backend.mind.memory import MemoryManager
from backend.mind.schema import Drone, MemoryEntry, MindCharter, MindProfile, Task
from backend.mind.store import MindStore


class DatabaseInitTests(unittest.TestCase):
    def test_init_db_creates_tables_and_enables_wal(self):
        tmp_dir = Path(tempfile.mkdtemp(prefix="db-init-tests-"))
        try:
            db_path = tmp_dir / "test.db"
            conn = init_db(db_path)

            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual(mode, "wal")

            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            self.assertIn("minds", tables)
            self.assertIn("tasks", tables)
            self.assertIn("task_traces", tables)
            self.assertIn("memories", tables)

            conn.close()
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_init_db_is_idempotent(self):
        tmp_dir = Path(tempfile.mkdtemp(prefix="db-idempotent-tests-"))
        try:
            db_path = tmp_dir / "test.db"
            conn1 = init_db(db_path)
            conn1.close()
            conn2 = init_db(db_path)
            conn2.close()
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_init_db_migrates_existing_minds_table_with_charter_column(self):
        tmp_dir = Path(tempfile.mkdtemp(prefix="db-migrate-charter-tests-"))
        try:
            db_path = tmp_dir / "test.db"

            conn = sqlite3.connect(str(db_path))
            conn.executescript(
                """
                CREATE TABLE minds (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    personality TEXT NOT NULL DEFAULT '',
                    preferences TEXT NOT NULL DEFAULT '{}',
                    system_prompt TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.commit()
            conn.close()

            migrated = init_db(db_path)
            columns = {
                row[1]
                for row in migrated.execute("PRAGMA table_info(minds)").fetchall()
            }
            self.assertIn("charter", columns)
            migrated.close()
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


class MindStoreSqliteTests(unittest.TestCase):
    def test_mind_crud(self):
        tmp_dir = Path(tempfile.mkdtemp(prefix="mind-store-tests-"))
        try:
            store = MindStore(tmp_dir / "test.db")

            mind = MindProfile(name="TestMind", personality="friendly")
            store.save_mind(mind)

            loaded = store.load_mind(mind.id)
            self.assertIsNotNone(loaded)
            if loaded is None:
                self.fail("Expected stored mind to be loadable")
            self.assertEqual(loaded.name, "TestMind")
            self.assertEqual(loaded.personality, "friendly")

            task = Task(mind_id=mind.id, description="cleanup candidate")
            store.save_task(mind.id, task)
            store.save_task_trace(mind.id, task.id, [{"type": "text", "content": "hi"}])
            drone = store.save_drone(
                Drone(
                    mind_id=mind.id,
                    task_id=task.id,
                    objective="subtask",
                    status="completed",
                )
            )
            store.save_drone_trace(mind.id, drone, [{"type": "text", "content": "ok"}])
            MemoryManager(tmp_dir / "test.db").save(
                MemoryEntry(mind_id=mind.id, content="memory to delete")
            )

            minds = store.list_minds()
            self.assertEqual(len(minds), 1)

            deleted = store.delete_mind(mind.id)
            self.assertTrue(deleted)
            self.assertIsNone(store.load_mind(mind.id))
            self.assertEqual(store.list_tasks(mind.id), [])
            self.assertIsNone(store.load_task_trace(mind.id, task.id))
            self.assertEqual(store.list_drones(mind.id, task.id), [])
            self.assertIsNone(store.load_drone_trace(mind.id, drone))
            self.assertEqual(MemoryManager(tmp_dir / "test.db").list_all(mind.id), [])
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_task_trace_roundtrip(self):
        tmp_dir = Path(tempfile.mkdtemp(prefix="mind-trace-tests-"))
        try:
            store = MindStore(tmp_dir / "test.db")
            mind_id = "mind_1"
            task_id = "task_1"

            events = [{"type": "text", "content": "hello"}]
            store.save_task_trace(mind_id, task_id, events)

            trace = store.load_task_trace(mind_id, task_id)
            self.assertIsNotNone(trace)
            if trace is None:
                self.fail("Expected task trace to roundtrip")
            self.assertEqual(trace["task_id"], task_id)
            self.assertEqual(trace["events"], events)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_mind_charter_roundtrip(self):
        tmp_dir = Path(tempfile.mkdtemp(prefix="mind-charter-tests-"))
        try:
            store = MindStore(tmp_dir / "test.db")
            mind = MindProfile(
                name="Builder",
                charter=MindCharter(
                    mission="Assess and evolve the Mind runtime.",
                    non_goals=["Faking unsupported capabilities."],
                ),
            )

            store.save_mind(mind)
            loaded = store.load_mind(mind.id)

            self.assertIsNotNone(loaded)
            if loaded is None:
                self.fail("Expected stored mind with charter to be loadable")
            self.assertEqual(
                loaded.charter.mission,
                "Assess and evolve the Mind runtime.",
            )
            self.assertIn(
                "Faking unsupported capabilities.",
                loaded.charter.non_goals,
            )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_concurrent_writes(self):
        tmp_dir = Path(tempfile.mkdtemp(prefix="mind-concurrent-tests-"))
        try:
            store = MindStore(tmp_dir / "test.db")
            mind_id = "mind_1"
            errors = []

            def worker(start: int) -> None:
                try:
                    for i in range(50):
                        task = Task(
                            id=f"task_{start}_{i}",
                            mind_id=mind_id,
                            description=f"task {start}_{i}",
                        )
                        store.save_task(mind_id, task)
                except Exception as exc:
                    errors.append(exc)

            threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertEqual(errors, [])
            tasks = store.list_tasks(mind_id)
            self.assertEqual(len(tasks), 200)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


class MemoryFtsTests(unittest.TestCase):
    def test_fts_search_finds_matching_memories(self):
        tmp_dir = Path(tempfile.mkdtemp(prefix="memory-fts-tests-"))
        try:
            manager = MemoryManager(tmp_dir / "test.db")
            mind_id = "mind_1"

            manager.save(
                MemoryEntry(
                    mind_id=mind_id,
                    content="Release notes for version 3.2",
                    category="notes",
                    relevance_keywords=["release", "version"],
                )
            )
            manager.save(
                MemoryEntry(
                    mind_id=mind_id,
                    content="Meeting notes from Monday standup",
                    category="notes",
                    relevance_keywords=["meeting", "standup"],
                )
            )
            manager.save(
                MemoryEntry(
                    mind_id=mind_id,
                    content="Database migration plan for Q4",
                    category="planning",
                    relevance_keywords=["database", "migration"],
                )
            )

            results = manager.search(mind_id, "release notes")
            self.assertTrue(len(results) >= 1)
            self.assertTrue(any("release" in r.content.lower() for r in results))

            results = manager.search(mind_id, "standup meeting")
            self.assertTrue(len(results) >= 1)
            self.assertTrue(any("standup" in r.content.lower() for r in results))

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_search_empty_query_returns_empty(self):
        tmp_dir = Path(tempfile.mkdtemp(prefix="memory-empty-tests-"))
        try:
            manager = MemoryManager(tmp_dir / "test.db")
            results = manager.search("mind_1", "")
            self.assertEqual(results, [])
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_search_supports_non_latin_tokens(self):
        tmp_dir = Path(tempfile.mkdtemp(prefix="memory-unicode-tests-"))
        try:
            manager = MemoryManager(tmp_dir / "test.db")
            mind_id = "mind_1"

            manager.save(MemoryEntry(mind_id=mind_id, content="今日は新しい計画を立てる"))
            results = manager.search(mind_id, "計画")
            self.assertEqual(len(results), 1)
            self.assertIn("計画", results[0].content)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_search_isolates_by_mind_id(self):
        tmp_dir = Path(tempfile.mkdtemp(prefix="memory-isolation-tests-"))
        try:
            manager = MemoryManager(tmp_dir / "test.db")

            manager.save(
                MemoryEntry(
                    mind_id="mind_a",
                    content="Secret project alpha details",
                )
            )
            manager.save(
                MemoryEntry(
                    mind_id="mind_b",
                    content="Secret project beta details",
                )
            )

            results_a = manager.search("mind_a", "secret project")
            results_b = manager.search("mind_b", "secret project")

            self.assertEqual(len(results_a), 1)
            self.assertIn("alpha", results_a[0].content)
            self.assertEqual(len(results_b), 1)
            self.assertIn("beta", results_b[0].content)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_delete_removes_from_fts_index(self):
        tmp_dir = Path(tempfile.mkdtemp(prefix="memory-delete-tests-"))
        try:
            manager = MemoryManager(tmp_dir / "test.db")
            mind_id = "mind_1"

            entry = MemoryEntry(mind_id=mind_id, content="Unique searchable content")
            manager.save(entry)

            results = manager.search(mind_id, "unique searchable")
            self.assertEqual(len(results), 1)

            manager.delete(mind_id, entry.id)

            results = manager.search(mind_id, "unique searchable")
            self.assertEqual(len(results), 0)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
