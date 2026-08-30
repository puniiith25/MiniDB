"""
Unit tests for Write-Ahead Log (src/minidb/wal.py).
"""

import sys
import tempfile
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.wal import WriteAheadLog, WALRecord
from minidb.record import RecordType


class TestWAL(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.wal_file = Path(self.temp_dir.name) / "minidb.wal"
        self.wal = WriteAheadLog(self.wal_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_wal_append_and_read_all(self):
        r1 = WALRecord(1, "users", RecordType.INSERT, "1", '{"id":1, "name":"Punith"}')
        r2 = WALRecord(1, "users", RecordType.COMMIT, "", "")

        off1 = self.wal.append(r1)
        off2 = self.wal.append(r2)

        records = [r[1] for r in self.wal.read_all()]
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].table_name, "users")
        self.assertEqual(records[0].record_type, RecordType.INSERT)
        self.assertEqual(records[1].record_type, RecordType.COMMIT)

    def test_wal_clear(self):
        r1 = WALRecord(1, "users", RecordType.INSERT, "1", '{"id":1}')
        self.wal.append(r1)
        self.wal.clear()

        records = list(self.wal.read_all())
        self.assertEqual(len(records), 0)


if __name__ == "__main__":
    unittest.main()
