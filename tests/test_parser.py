"""
Unit tests for SQL Parser (src/minidb/parser.py).
"""

import sys
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.parser import (
    Parser,
    CreateTableQuery,
    InsertQuery,
    SelectQuery,
    DeleteQuery,
    BeginTransactionQuery,
    CommitTransactionQuery,
    RollbackTransactionQuery,
    WhereClause,
)
from minidb.schema import DataType
from minidb.errors import ParseError


class TestParser(unittest.TestCase):

    def test_parse_create_table(self):
        sql = "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER, is_active BOOLEAN);"
        parser = Parser(sql)
        ast = parser.parse()

        self.assertIsInstance(ast, CreateTableQuery)
        self.assertEqual(ast.table_name, "users")
        self.assertEqual(len(ast.columns), 4)
        self.assertEqual(ast.columns[0].name, "id")
        self.assertTrue(ast.columns[0].primary_key)

    def test_parse_insert(self):
        sql = "INSERT INTO users VALUES (1, 'Punith', 22, TRUE);"
        parser = Parser(sql)
        ast = parser.parse()

        self.assertIsInstance(ast, InsertQuery)
        self.assertEqual(ast.table_name, "users")
        self.assertEqual(ast.values, [1, "Punith", 22, True])

    def test_parse_select_where(self):
        sql = "SELECT id, name FROM users WHERE age >= 20 LIMIT 10;"
        parser = Parser(sql)
        ast = parser.parse()

        self.assertIsInstance(ast, SelectQuery)
        self.assertEqual(ast.table_name, "users")
        self.assertEqual(ast.columns, ["id", "name"])
        self.assertIsNotNone(ast.where)
        self.assertEqual(ast.where.column, "age")
        self.assertEqual(ast.where.operator, ">=")
        self.assertEqual(ast.where.value, 20)
        self.assertEqual(ast.limit, 10)

    def test_parse_delete_where(self):
        sql = "DELETE FROM users WHERE id = 1;"
        parser = Parser(sql)
        ast = parser.parse()

        self.assertIsInstance(ast, DeleteQuery)
        self.assertEqual(ast.table_name, "users")
        self.assertEqual(ast.where.column, "id")
        self.assertEqual(ast.where.operator, "=")
        self.assertEqual(ast.where.value, 1)

    def test_parse_transaction_statements(self):
        self.assertIsInstance(Parser("BEGIN;").parse(), BeginTransactionQuery)
        self.assertIsInstance(Parser("COMMIT;").parse(), CommitTransactionQuery)
        self.assertIsInstance(Parser("ROLLBACK;").parse(), RollbackTransactionQuery)

    def test_invalid_syntax_raises_error(self):
        with self.assertRaises(ParseError):
            Parser("INVALID STATEMENT").parse()


if __name__ == "__main__":
    unittest.main()
