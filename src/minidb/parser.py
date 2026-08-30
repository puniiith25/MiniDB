"""
SQL Parser and AST (Abstract Syntax Tree) for MiniDB.

Translates Token streams into typed AST Query dataclass objects.
"""

from typing import Any, List, Optional, Union
from dataclasses import dataclass
from minidb.lexer import Lexer, Token, TokenType
from minidb.schema import Column, DataType
from minidb.errors import ParseError


@dataclass
class WhereClause:
    column: str
    operator: str  # '=', '!=', '>', '<', '>=', '<='
    value: Any


@dataclass
class CreateTableQuery:
    table_name: str
    columns: List[Column]


@dataclass
class InsertQuery:
    table_name: str
    columns: Optional[List[str]]
    values: List[Any]


@dataclass
class SelectQuery:
    table_name: str
    columns: List[str]  # ['*'] or list of column names
    where: Optional[WhereClause] = None
    limit: Optional[int] = None


@dataclass
class DeleteQuery:
    table_name: str
    where: Optional[WhereClause] = None


@dataclass
class BeginTransactionQuery:
    pass


@dataclass
class CommitTransactionQuery:
    pass


@dataclass
class RollbackTransactionQuery:
    pass


ASTQuery = Union[
    CreateTableQuery,
    InsertQuery,
    SelectQuery,
    DeleteQuery,
    BeginTransactionQuery,
    CommitTransactionQuery,
    RollbackTransactionQuery,
]


class Parser:
    """
    Recursive-descent parser producing typed AST query objects.
    """

    def __init__(self, sql: str):
        self.sql = sql
        self.lexer = Lexer(sql)
        self.tokens: List[Token] = self.lexer.tokenize()
        self.pos = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.pos]

    def peek(self, offset: int = 1) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]

    def advance(self) -> Token:
        tok = self.current
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def match(self, *expected_types: TokenType) -> bool:
        if self.current.type in expected_types:
            self.advance()
            return True
        return False

    def expect(self, expected_type: TokenType, err_msg: str = "") -> Token:
        if self.current.type != expected_type:
            raise ParseError(
                err_msg
                or f"Expected token '{expected_type.name}' at position {self.current.position}, got '{self.current.value}' ({self.current.type.name})"
            )
        return self.advance()

    def parse(self) -> ASTQuery:
        """Parse SQL token stream into ASTQuery object."""
        tok = self.current

        if tok.type == TokenType.CREATE:
            return self._parse_create_table()
        elif tok.type == TokenType.INSERT:
            return self._parse_insert()
        elif tok.type == TokenType.SELECT:
            return self._parse_select()
        elif tok.type == TokenType.DELETE:
            return self._parse_delete()
        elif tok.type == TokenType.BEGIN:
            self.advance()
            self.match(TokenType.SEMICOLON)
            return BeginTransactionQuery()
        elif tok.type == TokenType.COMMIT:
            self.advance()
            self.match(TokenType.SEMICOLON)
            return CommitTransactionQuery()
        elif tok.type == TokenType.ROLLBACK:
            self.advance()
            self.match(TokenType.SEMICOLON)
            return RollbackTransactionQuery()
        else:
            raise ParseError(f"Unsupported SQL statement starting with token '{tok.value}'")

    def _parse_create_table(self) -> CreateTableQuery:
        self.expect(TokenType.CREATE)
        self.expect(TokenType.TABLE)
        table_name_tok = self.expect(TokenType.IDENTIFIER, "Expected table name after CREATE TABLE")
        table_name = table_name_tok.value

        self.expect(TokenType.LPAREN, "Expected '(' after table name")

        columns: List[Column] = []

        while True:
            col_name_tok = self.expect(TokenType.IDENTIFIER, "Expected column name")
            col_name = col_name_tok.value

            # Match data type
            type_tok = self.current
            if type_tok.type == TokenType.TYPE_INTEGER:
                data_type = DataType.INTEGER
            elif type_tok.type == TokenType.TYPE_TEXT:
                data_type = DataType.TEXT
            elif type_tok.type == TokenType.TYPE_BOOLEAN:
                data_type = DataType.BOOLEAN
            elif type_tok.type == TokenType.TYPE_FLOAT:
                data_type = DataType.FLOAT
            else:
                raise ParseError(f"Invalid data type '{type_tok.value}' for column '{col_name}'")
            self.advance()

            primary_key = False
            if self.current.type == TokenType.PRIMARY:
                self.advance()
                self.expect(TokenType.KEY, "Expected KEY after PRIMARY")
                primary_key = True

            columns.append(Column(name=col_name, data_type=data_type, primary_key=primary_key))

            if self.match(TokenType.COMMA):
                continue
            else:
                break

        self.expect(TokenType.RPAREN, "Expected ')' after column definitions")
        self.match(TokenType.SEMICOLON)

        return CreateTableQuery(table_name=table_name, columns=columns)

    def _parse_insert(self) -> InsertQuery:
        self.expect(TokenType.INSERT)
        self.expect(TokenType.INTO)
        table_name_tok = self.expect(TokenType.IDENTIFIER, "Expected table name after INSERT INTO")
        table_name = table_name_tok.value

        columns = None
        if self.match(TokenType.LPAREN):
            columns = []
            while True:
                col_tok = self.expect(TokenType.IDENTIFIER, "Expected column name")
                columns.append(col_tok.value)
                if not self.match(TokenType.COMMA):
                    break
            self.expect(TokenType.RPAREN, "Expected ')' after column list")

        self.expect(TokenType.VALUES, "Expected VALUES in INSERT query")
        self.expect(TokenType.LPAREN, "Expected '(' before INSERT values")

        values = []
        while True:
            val = self._parse_literal_value()
            values.append(val)
            if not self.match(TokenType.COMMA):
                break

        self.expect(TokenType.RPAREN, "Expected ')' after INSERT values")
        self.match(TokenType.SEMICOLON)

        return InsertQuery(table_name=table_name, columns=columns, values=values)

    def _parse_select(self) -> SelectQuery:
        self.expect(TokenType.SELECT)

        columns = []
        if self.match(TokenType.ASTERISK):
            columns = ["*"]
        else:
            while True:
                col_tok = self.expect(TokenType.IDENTIFIER, "Expected column name in SELECT")
                columns.append(col_tok.value)
                if not self.match(TokenType.COMMA):
                    break

        self.expect(TokenType.FROM, "Expected FROM in SELECT query")
        table_name_tok = self.expect(TokenType.IDENTIFIER, "Expected table name in SELECT query")
        table_name = table_name_tok.value

        where = None
        if self.match(TokenType.WHERE):
            where = self._parse_where_clause()

        limit = None
        if self.match(TokenType.LIMIT):
            limit_tok = self.expect(TokenType.NUMBER_INT, "Expected integer limit number")
            limit = int(limit_tok.value)

        self.match(TokenType.SEMICOLON)

        return SelectQuery(table_name=table_name, columns=columns, where=where, limit=limit)

    def _parse_delete(self) -> DeleteQuery:
        self.expect(TokenType.DELETE)
        self.expect(TokenType.FROM)
        table_name_tok = self.expect(TokenType.IDENTIFIER, "Expected table name in DELETE query")
        table_name = table_name_tok.value

        where = None
        if self.match(TokenType.WHERE):
            where = self._parse_where_clause()

        self.match(TokenType.SEMICOLON)

        return DeleteQuery(table_name=table_name, where=where)

    def _parse_where_clause(self) -> WhereClause:
        col_tok = self.expect(TokenType.IDENTIFIER, "Expected column name in WHERE clause")
        col_name = col_tok.value

        op_tok = self.current
        valid_ops = {
            TokenType.EQ: "=",
            TokenType.NEQ: "!=",
            TokenType.GT: ">",
            TokenType.GTE: ">=",
            TokenType.LT: "<",
            TokenType.LTE: "<=",
        }

        if op_tok.type not in valid_ops:
            raise ParseError(f"Invalid operator '{op_tok.value}' in WHERE clause")

        op_str = valid_ops[op_tok.type]
        self.advance()

        val = self._parse_literal_value()

        return WhereClause(column=col_name, operator=op_str, value=val)

    def _parse_literal_value(self) -> Any:
        tok = self.current
        if tok.type == TokenType.NUMBER_INT:
            self.advance()
            return int(tok.value)
        elif tok.type == TokenType.NUMBER_FLOAT:
            self.advance()
            return float(tok.value)
        elif tok.type == TokenType.STRING_LITERAL:
            self.advance()
            return tok.value
        elif tok.type == TokenType.BOOLEAN_LITERAL:
            self.advance()
            return True if tok.value.lower() == "true" else False
        elif tok.type == TokenType.NULL:
            self.advance()
            return None
        else:
            raise ParseError(f"Expected literal value at position {tok.position}, got '{tok.value}'")
