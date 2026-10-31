import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import NotesRepository, validate_note  # noqa: E402


class NotesRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.database_path = Path(__file__).resolve().parents[1] / "data" / f"test-{uuid.uuid4().hex}.db"
        self.database_path.parent.mkdir(exist_ok=True)
        self.repository = NotesRepository(self.database_path)

    def tearDown(self):
        # Files are ignored by Git; keeping isolated test databases avoids Windows file-lock flakiness.
        pass

    def test_complete_crud_and_search_flow(self):
        note = self.repository.create("Interview prep", "Review REST APIs")
        note_id = note["id"]

        updated = self.repository.update(note_id, "Interview plan", "Review REST APIs and SQLite")
        self.assertEqual(updated["title"], "Interview plan")

        listed = self.repository.list("sqlite")
        self.assertEqual(len(listed), 1)

        self.assertTrue(self.repository.delete(note_id))
        self.assertEqual(self.repository.list(), [])

    def test_rejects_invalid_and_missing_notes(self):
        with self.assertRaisesRegex(ValueError, "title"):
            validate_note({"title": "", "content": "Text"})

        self.assertIsNone(self.repository.update(999, "Missing", "Text"))
        self.assertFalse(self.repository.delete(999))


if __name__ == "__main__":
    unittest.main()

