"""
Unit tests for in-memory indexing engine (src/minidb/index.py).
"""

import sys
import tempfile
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.index import PrimaryIndex
from minidb.storage import StorageEngine
from minidb.record import Record, RecordType


class TestPrimaryIndex(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_file = Path(self.temp_dir.name) / "indexed_table.db"
        self.storage = StorageEngine(self.db_file)
        self.index = PrimaryIndex()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_basic_index_operations(self):
        self.index.put("user1", 100)
        self.index.put("user2", 250)

        self.assertTrue(self.index.contains("user1"))
        self.assertEqual(self.index.get("user1"), 100)
        self.assertEqual(self.index.get("user2"), 250)
        self.assertIsNone(self.index.get("user3"))
        self.assertEqual(self.index.count(), 2)

        self.assertTrue(self.index.delete("user1"))
        self.assertFalse(self.index.contains("user1"))
        self.assertEqual(self.index.count(), 1)

    def test_rebuild_from_storage_log(self):
        # 1. Insert user1
        off1 = self.storage.append_record(Record(RecordType.INSERT, "user1", "Punith"))
        # 2. Insert user2
        off2 = self.storage.append_record(Record(RecordType.INSERT, "user2", "Rahul"))
        # 3. Update user1
        off3 = self.storage.append_record(Record(RecordType.UPDATE, "user1", "Punith V2"))
        # 4. Delete user2 (Tombstone)
        off4 = self.storage.append_record(Record(RecordType.DELETE, "user2", ""))

        # Rebuild index from disk storage
        count = self.index.rebuild_from_storage(self.storage)

        self.assertEqual(count, 1)
        self.assertTrue(self.index.contains("user1"))
        self.assertFalse(self.index.contains("user2"))
        self.assertEqual(self.index.get("user1"), off3)

        # Read directly from storage using index offset
        offset = self.index.get("user1")
        self.assertIsNotNone(offset)
        assert offset is not None
        rec = self.storage.read_record_at(offset)
        self.assertEqual(rec.value, "Punith V2")


if __name__ == "__main__":
    unittest.main()
