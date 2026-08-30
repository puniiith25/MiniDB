"""
Unit & Crash simulation tests for RecoveryManager (src/minidb/recovery.py).
"""

import sys
import tempfile
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.database import Database
from minidb.schema import TableSchema, Column, DataType
from minidb.wal import WriteAheadLog, WALRecord
from minidb.record import RecordType
from minidb.recovery import RecoveryManager
from minidb.executor import QueryExecutor
from minidb.parser import Parser


class TestCrashRecovery(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_dir = Path(self.temp_dir.name)
        self.wal_file = self.db_dir / "minidb.wal"

        self.db = Database(self.db_dir)
        self.wal = WriteAheadLog(self.wal_file)

        # Create table schema
        schema = TableSchema(
            name="users",
            columns=[
                Column("id", DataType.INTEGER, primary_key=True),
                Column("name", DataType.TEXT),
            ],
        )
        self.db.create_table(schema)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_committed_wal_recovery_after_crash(self):
        """Simulate crash where WAL was written and committed, but database table file was not updated."""
        tx_id = 101
        payload = '{"id":1,"name":"Punith"}'

        # Write WAL INSERT & COMMIT records
        self.wal.append(WALRecord(tx_id, "users", RecordType.INSERT, "1", payload))
        self.wal.append(WALRecord(tx_id, "users", RecordType.COMMIT, "", ""))

        # Simulate Crash and Restart: re-instantiate Database object
        new_db = Database(self.db_dir)
        recovery_mgr = RecoveryManager(new_db, self.wal)
        replayed = recovery_mgr.recover()

        self.assertEqual(replayed, 1)

        # Query re-opened database to verify data exists
        executor = QueryExecutor(new_db)
        res = executor.execute(Parser("SELECT * FROM users WHERE id = 1;").parse())
        self.assertEqual(len(res.rows), 1)
        self.assertEqual(res.rows[0]["name"], "Punith")

    def test_uncommitted_wal_discarded_on_recovery(self):
        """Simulate crash during uncommitted transaction (no COMMIT record)."""
        tx_id = 102
        payload = '{"id":2,"name":"Uncommitted Rahul"}'

        # Write WAL INSERT but NO COMMIT
        self.wal.append(WALRecord(tx_id, "users", RecordType.INSERT, "2", payload))

        # Crash & Recover
        new_db = Database(self.db_dir)
        recovery_mgr = RecoveryManager(new_db, self.wal)
        replayed = recovery_mgr.recover()

        self.assertEqual(replayed, 0)

        # Query database: row 2 must not exist
        executor = QueryExecutor(new_db)
        res = executor.execute(Parser("SELECT * FROM users WHERE id = 2;").parse())
        self.assertEqual(len(res.rows), 0)


if __name__ == "__main__":
    unittest.main()
