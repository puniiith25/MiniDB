"""
Unit tests for storage engine (src/minidb/storage.py).
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.storage import StorageEngine
from minidb.record import Record, RecordType
from minidb.errors import CorruptionError, StorageError


class TestStorageEngine(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_file = Path(self.temp_dir.name) / "test_table.db"
        self.storage = StorageEngine(self.db_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_milestone1_persistence(self):
        """Milestone 1: Insert -> Write to disk -> Restart program -> Retrieve value."""
        rec1 = Record(RecordType.INSERT, "user1", "Punith")
        offset = self.storage.append_record(rec1)
        self.assertGreaterEqual(offset, 0)

        # Simulate program restart by instantiating new StorageEngine object
        new_storage = StorageEngine(self.db_file)
        retrieved_rec = new_storage.read_record_at(offset)

        self.assertEqual(retrieved_rec.key, "user1")
        self.assertEqual(retrieved_rec.value, "Punith")

    def test_append_multiple_and_scan(self):
        rec1 = Record(RecordType.INSERT, "user1", "Punith")
        rec2 = Record(RecordType.INSERT, "user2", "Rahul")
        rec3 = Record(RecordType.DELETE, "user1", "")

        off1 = self.storage.append_record(rec1)
        off2 = self.storage.append_record(rec2)
        off3 = self.storage.append_record(rec3)

        self.assertLess(off1, off2)
        self.assertLess(off2, off3)

        scanned = list(self.storage.scan_all_records())
        self.assertEqual(len(scanned), 3)

        offsets = [s[0] for s in scanned]
        records = [s[1] for s in scanned]

        self.assertEqual(offsets, [off1, off2, off3])
        self.assertEqual(records[0].value, "Punith")
        self.assertEqual(records[1].value, "Rahul")
        self.assertEqual(records[2].record_type, RecordType.DELETE)

    def test_truncated_eof_handled_safely(self):
        rec = Record(RecordType.INSERT, "key1", "val1")
        self.storage.append_record(rec)

        # Corrupt file by appending partial byte header at EOF
        with open(self.db_file, "ab") as f:
            f.write(b"MB123")

        scanned = list(self.storage.scan_all_records())
        # Should yield 1 valid record and gracefully stop at partial EOF
        self.assertEqual(len(scanned), 1)
        self.assertEqual(scanned[0][1].key, "key1")

    def test_mid_file_corruption_raises_error(self):
        rec1 = Record(RecordType.INSERT, "key1", "val1")
        rec2 = Record(RecordType.INSERT, "key2", "val2")

        off1 = self.storage.append_record(rec1)
        off2 = self.storage.append_record(rec2)

        # Corrupt bytes in first record payload
        with open(self.db_file, "r+b") as f:
            f.seek(off1 + 5)
            f.write(b"\xFF\xFF")

        with self.assertRaises(CorruptionError):
            list(self.storage.scan_all_records())


if __name__ == "__main__":
    unittest.main()
