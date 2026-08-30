"""
Unit & Integration tests for QueryExecutor and Database (src/minidb/executor.py).
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
from minidb.executor import QueryExecutor
from minidb.errors import DatabaseError, SchemaError


class TestQueryExecutor(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(self.temp_dir.name)
        self.executor = QueryExecutor(self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_sql(self, sql: str):
        ast = Parser(sql).parse()
        return self.executor.execute(ast)

    def test_full_sql_workflow(self):
        # 1. CREATE TABLE
        res = self.run_sql(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER, is_active BOOLEAN);"
        )
        self.assertIn("users", self.db.list_tables())

        # 2. INSERT 3 ROWS
        self.run_sql("INSERT INTO users VALUES (1, 'Punith', 22, TRUE);")
        self.run_sql("INSERT INTO users VALUES (2, 'Rahul', 25, FALSE);")
        self.run_sql("INSERT INTO users VALUES (3, 'Akash', 30, TRUE);")

        # 3. SELECT ALL
        res_select_all = self.run_sql("SELECT * FROM users;")
        self.assertEqual(len(res_select_all.rows), 3)

        # 4. SELECT WHERE PREDICATE (age > 23)
        res_where = self.run_sql("SELECT name, age FROM users WHERE age > 23;")
        self.assertEqual(len(res_where.rows), 2)
        names = [r["name"] for r in res_where.rows]
        self.assertEqual(names, ["Rahul", "Akash"])

        # 5. FAST PATH INDEXED LOOKUP (id = 1)
        res_fast = self.run_sql("SELECT * FROM users WHERE id = 1;")
        self.assertEqual(len(res_fast.rows), 1)
        self.assertEqual(res_fast.rows[0]["name"], "Punith")

        # 6. DELETE (id = 2)
        res_del = self.run_sql("DELETE FROM users WHERE id = 2;")
        self.assertEqual(res_del.affected_rows, 1)

        # 7. SELECT AGAIN AFTER DELETE
        res_after_del = self.run_sql("SELECT * FROM users WHERE id = 2;")
        self.assertEqual(len(res_after_del.rows), 0)

        # Total remaining rows should be 2
        self.assertEqual(len(self.run_sql("SELECT * FROM users;").rows), 2)

    def test_multiple_tables(self):
        self.run_sql("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);")
        self.run_sql("CREATE TABLE products (sku TEXT PRIMARY KEY, price FLOAT);")

        self.run_sql("INSERT INTO users VALUES (1, 'Punith');")
        self.run_sql("INSERT INTO products VALUES ('SKU100', 49.99);")

        self.assertEqual(self.db.list_tables(), ["products", "users"])

        res_u = self.run_sql("SELECT * FROM users;")
        res_p = self.run_sql("SELECT * FROM products;")

        self.assertEqual(res_u.rows[0]["name"], "Punith")
        self.assertEqual(res_p.rows[0]["price"], 49.99)


if __name__ == "__main__":
    unittest.main()
