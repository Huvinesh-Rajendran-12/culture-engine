"""Tests for the protocol-agnostic MindService layer."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from backend.mind.events import Event
from backend.mind.exceptions import (
    DroneNotFoundError,
    MindNotFoundError,
    TaskNotFoundError,
    ValidationError,
)
from backend.mind.memory import MemoryManager
from backend.mind.schema import Drone, MindCharter, Task
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

    def test_charter_string_fields_can_be_cleared(self):
        mind = self.svc.create_mind(name="C")
        self.svc.update_mind(mind.id, charter={"mission": "Non-empty"})

        cleared = self.svc.update_mind(mind.id, charter={"mission": ""})
        self.assertEqual(cleared.charter.mission, "")

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


class TestTracesAndDrones(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="svc-traces-drones-"))
        db = self._tmp / "test.db"
        self.store = MindStore(db)
        self.memory = MemoryManager(db)
        self.svc = MindService(self.store, self.memory)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_get_task_trace_returns_trace(self):
        mind = self.svc.create_mind(name="T")
        task = Task(mind_id=mind.id, description="Traced task")
        self.store.save_task(mind.id, task)
        self.store.save_task_trace(mind.id, task.id, [{"type": "text", "content": "hi"}])

        trace = self.svc.get_task_trace(mind.id, task.id)
        self.assertEqual(trace["task_id"], task.id)
        self.assertEqual(len(trace["events"]), 1)

    def test_get_task_trace_missing_raises(self):
        mind = self.svc.create_mind(name="T")
        with self.assertRaises(TaskNotFoundError):
            self.svc.get_task_trace(mind.id, "missing-task")

    def test_list_drones_returns_drones(self):
        mind = self.svc.create_mind(name="D")
        task = Task(mind_id=mind.id, description="Parent task")
        self.store.save_task(mind.id, task)

        d1 = Drone(mind_id=mind.id, task_id=task.id, objective="o1", status="completed")
        d2 = Drone(mind_id=mind.id, task_id=task.id, objective="o2", status="failed")
        self.store.save_drone(d1)
        self.store.save_drone(d2)

        drones = self.svc.list_drones(mind.id, task.id)
        self.assertEqual(len(drones), 2)

    def test_list_drones_missing_task_raises(self):
        mind = self.svc.create_mind(name="D")
        with self.assertRaises(TaskNotFoundError):
            self.svc.list_drones(mind.id, "missing-task")

    def test_get_drone_trace_returns_trace(self):
        mind = self.svc.create_mind(name="D")
        drone = Drone(mind_id=mind.id, task_id="task-1", objective="x", status="completed")
        self.store.save_drone_trace(mind.id, drone.id, [{"type": "text", "content": "drone"}])

        trace = self.svc.get_drone_trace(mind.id, drone.id)
        self.assertEqual(trace["drone_id"], drone.id)
        self.assertEqual(len(trace["events"]), 1)

    def test_get_drone_trace_missing_raises_drone_not_found(self):
        mind = self.svc.create_mind(name="D")
        with self.assertRaises(DroneNotFoundError):
            self.svc.get_drone_trace(mind.id, "missing-drone")


class TestDelegateEventEnvelope(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="svc-delegate-"))
        db = self._tmp / "test.db"
        self.store = MindStore(db)
        self.memory = MemoryManager(db)
        self.svc = MindService(self.store, self.memory)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    @staticmethod
    async def _collect(stream):
        events = []
        async for event in stream:
            events.append(event)
        return events

    @staticmethod
    async def _raw_events():
        yield {"type": "a", "content": {"x": 1}}
        yield {"type": "b", "content": "done"}

    @patch("backend.mind.service.delegate_to_mind")
    async def test_delegate_wraps_events_with_envelope_fields(self, mock_delegate):
        mock_delegate.return_value = self._raw_events()

        events = await self._collect(
            self.svc.delegate("mind-1", "Run task", team="default")
        )

        self.assertEqual(len(events), 2)
        self.assertTrue(all(isinstance(e, Event) for e in events))
        self.assertEqual([e.seq for e in events], [0, 1])
        self.assertEqual(events[0].type, "a")
        self.assertEqual(events[1].type, "b")
        self.assertEqual(events[0].content, {"x": 1})
        self.assertEqual(events[1].content, "done")
        self.assertEqual(events[0].trace_id, events[1].trace_id)
        self.assertTrue(events[0].trace_id)
        self.assertTrue(events[0].id)
        self.assertTrue(events[0].ts)


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
