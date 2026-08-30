"""
Concurrency unit tests for MiniDB (src/minidb/lock.py).
"""

import sys
import tempfile
import threading
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.database import Database
from minidb.schema import TableSchema, Column, DataType
from minidb.parser import Parser
from minidb.executor import QueryExecutor
from minidb.lock import DatabaseLockManager


class TestConcurrency(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(self.temp_dir.name)
        self.executor = QueryExecutor(self.db)
        self.lock_mgr = DatabaseLockManager()

        # Create test table
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

    def test_concurrent_inserts(self):
        """Simulate concurrent threads inserting rows into database safely."""
        num_threads = 10
        records_per_thread = 20
        errors = []

        def worker(thread_id: int):
            try:
                table_lock = self.lock_mgr.table_locks.get_table_lock("users")
                for i in range(records_per_thread):
                    row_id = thread_id * 1000 + i
                    sql = f"INSERT INTO users VALUES ({row_id}, 'User_{row_id}');"
                    ast = Parser(sql).parse()
                    with table_lock:
                        self.executor.execute(ast)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent thread errors encountered: {errors}")

        # Verify all records inserted
        res = self.executor.execute(Parser("SELECT * FROM users;").parse())
        self.assertEqual(len(res.rows), num_threads * records_per_thread)


if __name__ == "__main__":
    unittest.main()
