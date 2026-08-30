"""
Unit tests for TransactionManager (src/minidb/transaction.py).
"""

import sys
import tempfile
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.database import Database
from minidb.parser import Parser
from minidb.transaction import TransactionManager
from minidb.errors import TransactionError


class TestTransactions(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(self.temp_dir.name)
        self.tm = TransactionManager(self.db)

        # Setup table
        self.run_sql(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER);"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_sql(self, sql: str):
        ast = Parser(sql).parse()
        return self.tm.execute_sql_query(ast)

    def test_commit_transaction(self):
        self.run_sql("BEGIN;")
        self.run_sql("INSERT INTO users VALUES (1, 'Punith', 22);")
        self.run_sql("INSERT INTO users VALUES (2, 'Rahul', 25);")
        res_commit = self.run_sql("COMMIT;")

        self.assertEqual(res_commit.affected_rows, 2)

        # Verify data persisted across database reopen
        new_db = Database(self.temp_dir.name)
        new_tm = TransactionManager(new_db)
        res_select = new_tm.execute_sql_query(Parser("SELECT * FROM users;").parse())

        self.assertEqual(len(res_select.rows), 2)
        names = [r["name"] for r in res_select.rows]
        self.assertIn("Punith", names)
        self.assertIn("Rahul", names)

    def test_rollback_transaction(self):
        # 1. Commit initial row 1
        self.run_sql("INSERT INTO users VALUES (1, 'Punith', 22);")

        # 2. Start transaction for row 3 and rollback
        self.run_sql("BEGIN;")
        self.run_sql("INSERT INTO users VALUES (3, 'Akash', 30);")

        # Uncommitted read inside transaction should see row 3
        res_inside = self.run_sql("SELECT * FROM users WHERE id = 3;")
        self.assertEqual(len(res_inside.rows), 1)
        self.assertEqual(res_inside.rows[0]["name"], "Akash")

        # Rollback transaction
        self.run_sql("ROLLBACK;")

        # After rollback: row 3 MUST NOT exist
        res_after = self.run_sql("SELECT * FROM users WHERE id = 3;")
        self.assertEqual(len(res_after.rows), 0)

        # Row 1 must still exist
        res_row1 = self.run_sql("SELECT * FROM users WHERE id = 1;")
        self.assertEqual(len(res_row1.rows), 1)

    def test_nested_begin_raises_error(self):
        self.run_sql("BEGIN;")
        with self.assertRaises(TransactionError):
            self.run_sql("BEGIN;")

    def test_commit_without_begin_raises_error(self):
        with self.assertRaises(TransactionError):
            self.run_sql("COMMIT;")


if __name__ == "__main__":
    unittest.main()
