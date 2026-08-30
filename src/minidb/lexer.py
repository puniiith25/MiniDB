"""
SQL Lexer (Tokenizer) for MiniDB.

Tokenizes SQL query strings into a stream of typed Token objects using stdlib re.
"""

import re
from enum import Enum, auto
from typing import List, Optional
from dataclasses import dataclass
from minidb.errors import ParseError


class TokenType(Enum):
    # Keywords
    CREATE = auto()
    TABLE = auto()
    INSERT = auto()
    INTO = auto()
    VALUES = auto()
    SELECT = auto()
    FROM = auto()
    WHERE = auto()
    DELETE = auto()
    BEGIN = auto()
    COMMIT = auto()
    ROLLBACK = auto()
    PRIMARY = auto()
    KEY = auto()
    NULL = auto()
    NOT = auto()
    AND = auto()
    OR = auto()
    LIMIT = auto()

    # Types
    TYPE_INTEGER = auto()
    TYPE_TEXT = auto()
    TYPE_BOOLEAN = auto()
    TYPE_FLOAT = auto()

    # Literals & Identifiers
    IDENTIFIER = auto()
    NUMBER_INT = auto()
    NUMBER_FLOAT = auto()
    STRING_LITERAL = auto()
    BOOLEAN_LITERAL = auto()

    # Operators & Punctuation
    ASTERISK = auto()  # *
    COMMA = auto()  # ,
    LPAREN = auto()  # (
    RPAREN = auto()  # )
    SEMICOLON = auto()  # ;
    EQ = auto()  # =
    NEQ = auto()  # != or <>
    GT = auto()  # >
    GTE = auto()  # >=
    LT = auto()  # <
    LTE = auto()  # <=

    EOF = auto()


KEYWORDS = {
    "CREATE": TokenType.CREATE,
    "TABLE": TokenType.TABLE,
    "INSERT": TokenType.INSERT,
    "INTO": TokenType.INTO,
    "VALUES": TokenType.VALUES,
    "SELECT": TokenType.SELECT,
    "FROM": TokenType.FROM,
    "WHERE": TokenType.WHERE,
    "DELETE": TokenType.DELETE,
    "BEGIN": TokenType.BEGIN,
    "COMMIT": TokenType.COMMIT,
    "ROLLBACK": TokenType.ROLLBACK,
    "PRIMARY": TokenType.PRIMARY,
    "KEY": TokenType.KEY,
    "NULL": TokenType.NULL,
    "NOT": TokenType.NOT,
    "AND": TokenType.AND,
    "OR": TokenType.OR,
    "LIMIT": TokenType.LIMIT,
    "INTEGER": TokenType.TYPE_INTEGER,
    "INT": TokenType.TYPE_INTEGER,
    "TEXT": TokenType.TYPE_TEXT,
    "VARCHAR": TokenType.TYPE_TEXT,
    "BOOLEAN": TokenType.TYPE_BOOLEAN,
    "BOOL": TokenType.TYPE_BOOLEAN,
    "FLOAT": TokenType.TYPE_FLOAT,
    "TRUE": TokenType.BOOLEAN_LITERAL,
    "FALSE": TokenType.BOOLEAN_LITERAL,
}


@dataclass
class Token:
    type: TokenType
    value: str
    position: int


class Lexer:
    """
    Hand-rolled SQL Lexer using Python regex.
    """

    def __init__(self, sql: str):
        self.sql = sql
        self.pos = 0

    def tokenize(self) -> List[Token]:
        tokens = []
        sql = self.sql

        # Regex patterns for tokens
        token_regex = [
            (r"\s+", None),  # Whitespace
            (r"--[^\n]*", None),  # Comments
            (r">=", TokenType.GTE),
            (r"<=", TokenType.LTE),
            (r"!=", TokenType.NEQ),
            (r"<>", TokenType.NEQ),
            (r"=", TokenType.EQ),
            (r">", TokenType.GT),
            (r"<", TokenType.LT),
            (r"\*", TokenType.ASTERISK),
            (r",", TokenType.COMMA),
            (r"\(", TokenType.LPAREN),
            (r"\)", TokenType.RPAREN),
            (r";", TokenType.SEMICOLON),
            (r"'([^'\\]*(?:\\.[^'\\]*)*)'", TokenType.STRING_LITERAL),  # Single-quoted strings
            (r'"([^"\\]*(?:\\.[^"\\]*)*)"', TokenType.STRING_LITERAL),  # Double-quoted strings
            (r"-?\d+\.\d+", TokenType.NUMBER_FLOAT),
            (r"-?\d+", TokenType.NUMBER_INT),
            (r"[a-zA-Z_][a-zA-Z0-9_]*", TokenType.IDENTIFIER),
        ]

        compiled_regex = [(re.compile(pattern, re.IGNORECASE), token_type) for pattern, token_type in token_regex]

        while self.pos < len(sql):
            match_found = False
            for pattern, token_type in compiled_regex:
                match = pattern.match(sql, self.pos)
                if match:
                    match_found = True
                    match_str = match.group(0)
                    start_pos = self.pos
                    self.pos = match.end()

                    if token_type is not None:
                        if token_type == TokenType.STRING_LITERAL:
                            # Extract contents inside quotes
                            val = match.group(1)
                            tokens.append(Token(token_type, val, start_pos))
                        elif token_type == TokenType.IDENTIFIER:
                            upper_val = match_str.upper()
                            if upper_val in KEYWORDS:
                                kw_type = KEYWORDS[upper_val]
                                if kw_type == TokenType.BOOLEAN_LITERAL:
                                    val = "true" if upper_val == "TRUE" else "false"
                                    tokens.append(Token(kw_type, val, start_pos))
                                else:
                                    tokens.append(Token(kw_type, upper_val, start_pos))
                            else:
                                tokens.append(Token(TokenType.IDENTIFIER, match_str, start_pos))
                        else:
                            tokens.append(Token(token_type, match_str, start_pos))
                    break

            if not match_found:
                raise ParseError(f"Unexpected character '{sql[self.pos]}' at position {self.pos}")

        tokens.append(Token(TokenType.EOF, "", self.pos))
        return tokens
