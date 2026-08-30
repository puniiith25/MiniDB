"""
Unit tests for SQL Lexer (src/minidb/lexer.py).
"""

import sys
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.lexer import Lexer, TokenType
from minidb.errors import ParseError


class TestLexer(unittest.TestCase):

    def test_tokenize_select_query(self):
        sql = "SELECT * FROM users WHERE age > 20;"
        lexer = Lexer(sql)
        tokens = lexer.tokenize()

        token_types = [t.type for t in tokens]
        expected_types = [
            TokenType.SELECT,
            TokenType.ASTERISK,
            TokenType.FROM,
            TokenType.IDENTIFIER,
            TokenType.WHERE,
            TokenType.IDENTIFIER,
            TokenType.GT,
            TokenType.NUMBER_INT,
            TokenType.SEMICOLON,
            TokenType.EOF,
        ]
        self.assertEqual(token_types, expected_types)

    def test_tokenize_create_table(self):
        sql = "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER, is_active BOOLEAN);"
        lexer = Lexer(sql)
        tokens = lexer.tokenize()

        token_types = [t.type for t in tokens]
        self.assertEqual(token_types[0], TokenType.CREATE)
        self.assertEqual(token_types[1], TokenType.TABLE)
        self.assertEqual(tokens[2].value, "users")
        self.assertEqual(tokens[4].value, "id")
        self.assertEqual(tokens[5].type, TokenType.TYPE_INTEGER)

    def test_tokenize_insert_query(self):
        sql = "INSERT INTO users VALUES (1, 'Punith', 22, TRUE);"
        lexer = Lexer(sql)
        tokens = lexer.tokenize()

        values_token = tokens[5]
        self.assertEqual(tokens[0].type, TokenType.INSERT)
        self.assertEqual(tokens[1].type, TokenType.INTO)
        self.assertEqual(tokens[7].value, "Punith")
        self.assertEqual(tokens[7].type, TokenType.STRING_LITERAL)

    def test_unexpected_character_raises_parse_error(self):
        sql = "SELECT * FROM users WHERE age @ 20;"
        lexer = Lexer(sql)
        with self.assertRaises(ParseError):
            lexer.tokenize()


if __name__ == "__main__":
    unittest.main()
