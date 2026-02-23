"""Tests for the protocol-agnostic MindService layer."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from backend.mind.exceptions import MindNotFoundError, TaskNotFoundError, ValidationError
from backend.mind.memory import MemoryManager
from backend.mind.schema import MindCharter, Task
from backend.mind.service import MindService
from backend.mind.store import MindStore


class TestCreateMind(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="svc-create-"))
        db = self._tmp / "test.db"
        self.svc = MindService(MindStore(db), MemoryManager(db))

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_returns_profile_with_correct_fields(self):
        mind = self.svc.create_mind(
            name="Alpha",
            personality="curious",
            preferences={"lang": "en"},
            system_prompt="Be concise.",
        )
        self.assertEqual(mind.name, "Alpha")
        self.assertEqual(mind.personality, "curious")
        self.assertEqual(mind.preferences, {"lang": "en"})
        self.assertEqual(mind.system_prompt, "Be concise.")
        self.assertIsNotNone(mind.id)
        self.assertIsNotNone(mind.created_at)

    def test_persists_mind(self):
        mind = self.svc.create_mind(name="Persisted")
        loaded = self.svc.get_mind(mind.id)
        self.assertEqual(loaded.name, "Persisted")

    def test_defaults(self):
        mind = self.svc.create_mind(name="Defaults")
        self.assertEqual(mind.personality, "")
        self.assertEqual(mind.preferences, {})
        self.assertEqual(mind.system_prompt, "")
        self.assertIsInstance(mind.charter, MindCharter)


class TestGetMind(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="svc-get-"))
        db = self._tmp / "test.db"
        self.svc = MindService(MindStore(db), MemoryManager(db))

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_returns_existing_mind(self):
        mind = self.svc.create_mind(name="Exists")
        loaded = self.svc.get_mind(mind.id)
        self.assertEqual(loaded.id, mind.id)
        self.assertEqual(loaded.name, "Exists")

    def test_raises_for_missing_mind(self):
        with self.assertRaises(MindNotFoundError):
            self.svc.get_mind("nonexistent")


class TestListMinds(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="svc-list-"))
        db = self._tmp / "test.db"
        self.svc = MindService(MindStore(db), MemoryManager(db))

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_empty_when_none(self):
        self.assertEqual(self.svc.list_minds(), [])

    def test_returns_all_minds(self):
        self.svc.create_mind(name="A")
        self.svc.create_mind(name="B")
        minds = self.svc.list_minds()
        self.assertEqual(len(minds), 2)
        names = {m.name for m in minds}
        self.assertEqual(names, {"A", "B"})


class TestUpdateMind(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="svc-update-"))
        db = self._tmp / "test.db"
        self.store = MindStore(db)
        self.memory = MemoryManager(db)
        self.svc = MindService(self.store, self.memory)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_name_change_persists_and_saves_implicit_memory(self):
        mind = self.svc.create_mind(name="OldName")
        updated = self.svc.update_mind(mind.id, name="NewName")
        self.assertEqual(updated.name, "NewName")

        reloaded = self.svc.get_mind(mind.id)
        self.assertEqual(reloaded.name, "NewName")

        memories = self.memory.list_all(mind.id, category="implicit_feedback")
        self.assertEqual(len(memories), 1)
        self.assertIn("identity_update", memories[0].relevance_keywords)
        self.assertIn("OldName", memories[0].content)
        self.assertIn("NewName", memories[0].content)

    def test_personality_change_saves_implicit_memory(self):
        mind = self.svc.create_mind(name="P", personality="calm")
        self.svc.update_mind(mind.id, personality="energetic")

        memories = self.memory.list_all(mind.id, category="implicit_feedback")
        self.assertEqual(len(memories), 1)
        self.assertIn("personality_update", memories[0].relevance_keywords)

    def test_charter_mission_change_saves_implicit_memory(self):
        mind = self.svc.create_mind(name="C")
        self.svc.update_mind(mind.id, charter={"mission": "New mission"})

        memories = self.memory.list_all(mind.id, category="implicit_feedback")
        self.assertEqual(len(memories), 1)
        self.assertIn("charter_mission_update", memories[0].relevance_keywords)

    def test_noop_update_does_not_create_memory(self):
        mind = self.svc.create_mind(name="Stable", personality="calm")
        self.svc.update_mind(mind.id, name="Stable", personality="calm")

        memories = self.memory.list_all(mind.id, category="implicit_feedback")
        self.assertEqual(len(memories), 0)

    def test_nonexistent_mind_raises(self):
        with self.assertRaises(MindNotFoundError):
            self.svc.update_mind("ghost", name="Nope")


class TestSubmitFeedback(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="svc-feedback-"))
        db = self._tmp / "test.db"
        self.store = MindStore(db)
        self.memory = MemoryManager(db)
        self.svc = MindService(self.store, self.memory)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_happy_path(self):
        mind = self.svc.create_mind(name="F")
        entry = self.svc.submit_feedback(
            mind.id, "Great work!", rating=5, tags=["quality"]
        )
        self.assertEqual(entry.category, "user_feedback")
        self.assertIn("Rating: 5/5", entry.content)
        self.assertIn("quality", entry.relevance_keywords)
        self.assertIn("positive_feedback", entry.relevance_keywords)

    def test_empty_content_raises(self):
        mind = self.svc.create_mind(name="F")
        with self.assertRaises(ValidationError):
            self.svc.submit_feedback(mind.id, "")

    def test_whitespace_only_content_raises(self):
        mind = self.svc.create_mind(name="F")
        with self.assertRaises(ValidationError):
            self.svc.submit_feedback(mind.id, "   ")

    def test_nonexistent_task_raises(self):
        mind = self.svc.create_mind(name="F")
        with self.assertRaises(TaskNotFoundError):
            self.svc.submit_feedback(mind.id, "Some feedback", task_id="bad_task")

    def test_nonexistent_mind_raises(self):
        with self.assertRaises(MindNotFoundError):
            self.svc.submit_feedback("missing_mind", "feedback")

    def test_with_existing_task(self):
        mind = self.svc.create_mind(name="F")
        task = Task(mind_id=mind.id, description="Do stuff")
        self.store.save_task(mind.id, task)

        entry = self.svc.submit_feedback(
            mind.id, "Good task", task_id=task.id, rating=4
        )
        self.assertIn(task.id, entry.content)
        self.assertIn("Do stuff", entry.content)

    def test_low_rating_adds_corrective_keyword(self):
        mind = self.svc.create_mind(name="F")
        entry = self.svc.submit_feedback(mind.id, "Needs work", rating=1)
        self.assertIn("corrective_feedback", entry.relevance_keywords)


class TestListAndGetTasks(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="svc-tasks-"))
        db = self._tmp / "test.db"
        self.store = MindStore(db)
        self.memory = MemoryManager(db)
        self.svc = MindService(self.store, self.memory)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_list_tasks_returns_tasks(self):
        mind = self.svc.create_mind(name="T")
        t1 = Task(mind_id=mind.id, description="Task 1")
        t2 = Task(mind_id=mind.id, description="Task 2")
        self.store.save_task(mind.id, t1)
        self.store.save_task(mind.id, t2)

        tasks = self.svc.list_tasks(mind.id)
        self.assertEqual(len(tasks), 2)

    def test_list_tasks_empty(self):
        mind = self.svc.create_mind(name="T")
        self.assertEqual(self.svc.list_tasks(mind.id), [])

    def test_list_tasks_nonexistent_mind_raises(self):
        with self.assertRaises(MindNotFoundError):
            self.svc.list_tasks("ghost")

    def test_get_task_returns_task(self):
        mind = self.svc.create_mind(name="T")
        task = Task(mind_id=mind.id, description="Specific")
        self.store.save_task(mind.id, task)

        loaded = self.svc.get_task(mind.id, task.id)
        self.assertEqual(loaded.description, "Specific")

    def test_get_task_nonexistent_raises(self):
        mind = self.svc.create_mind(name="T")
        with self.assertRaises(TaskNotFoundError):
            self.svc.get_task(mind.id, "no_such_task")


class TestListMemory(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="svc-memory-"))
        db = self._tmp / "test.db"
        self.store = MindStore(db)
        self.memory = MemoryManager(db)
        self.svc = MindService(self.store, self.memory)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_returns_memories(self):
        mind = self.svc.create_mind(name="M")
        self.svc.submit_feedback(mind.id, "Note one")
        self.svc.submit_feedback(mind.id, "Note two")

        memories = self.svc.list_memory(mind.id)
        self.assertEqual(len(memories), 2)

    def test_filter_by_category(self):
        mind = self.svc.create_mind(name="M")
        self.svc.submit_feedback(mind.id, "Feedback")
        self.svc.update_mind(mind.id, name="Renamed")

        user_fb = self.svc.list_memory(mind.id, category="user_feedback")
        implicit = self.svc.list_memory(mind.id, category="implicit_feedback")
        self.assertEqual(len(user_fb), 1)
        self.assertEqual(len(implicit), 1)

    def test_nonexistent_mind_raises(self):
        with self.assertRaises(MindNotFoundError):
            self.svc.list_memory("ghost")


if __name__ == "__main__":
    unittest.main()
