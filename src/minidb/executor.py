"""
Query Executor Engine for MiniDB.

Executes parsed SQL AST objects against the Database storage engine.
Supports fast-path indexed lookups and full scan predicate evaluation.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from minidb.database import Database, Table
from minidb.parser import (
    ASTQuery,
    CreateTableQuery,
    DropTableQuery,
    InsertQuery,
    SelectQuery,
    DeleteQuery,
    WhereClause,
)
from minidb.schema import TableSchema, Column, DataType
from minidb.record import Record, RecordType
from minidb.errors import DatabaseError, SchemaError, StorageError


@dataclass
class QueryResult:
    columns: List[str] = field(default_factory=list)
    rows: List[Dict[str, Any]] = field(default_factory=list)
    affected_rows: int = 0
    message: str = ""


class QueryExecutor:
    """
    Executes AST query trees against Database catalog and storage engine.
    """

    def __init__(self, db: Database):
        self.db = db

    def execute(self, query: ASTQuery) -> QueryResult:
        """Dispatch query execution to specific AST handler."""
        if isinstance(query, CreateTableQuery):
            return self._execute_create_table(query)
        elif isinstance(query, DropTableQuery):
            return self._execute_drop_table(query)
        elif isinstance(query, InsertQuery):
            return self._execute_insert(query)
        elif isinstance(query, SelectQuery):
            return self._execute_select(query)
        elif isinstance(query, DeleteQuery):
            return self._execute_delete(query)
        else:
            raise DatabaseError(f"Executor received unhandled query node type: {type(query).__name__}")

    def _execute_create_table(self, query: CreateTableQuery) -> QueryResult:
        if query.if_not_exists and self.db.has_table(query.table_name):
            return QueryResult(message=f"Table '{query.table_name}' already exists (skipped).")
        schema = TableSchema(name=query.table_name, columns=query.columns)
        self.db.create_table(schema, if_not_exists=query.if_not_exists)
        return QueryResult(message=f"Table '{query.table_name}' created successfully.")

    def _execute_drop_table(self, query: DropTableQuery) -> QueryResult:
        dropped = self.db.drop_table(query.table_name, if_exists=query.if_exists)
        if dropped:
            return QueryResult(message=f"Table '{query.table_name}' dropped successfully.")
        else:
            return QueryResult(message=f"Table '{query.table_name}' does not exist (skipped).")

    def _execute_insert(self, query: InsertQuery) -> QueryResult:
        table = self.db.get_table(query.table_name)
        schema = table.schema

        # Build row dictionary
        if query.columns:
            if len(query.columns) != len(query.values):
                raise SchemaError(
                    f"INSERT column count ({len(query.columns)}) does not match values count ({len(query.values)})"
                )
            row_dict = dict(zip(query.columns, query.values))
        else:
            if len(schema.columns) != len(query.values):
                raise SchemaError(
                    f"INSERT values count ({len(query.values)}) does not match table column count ({len(schema.columns)})"
                )
            row_dict = {col.name: val for col, val in zip(schema.columns, query.values)}

        # Validate against schema
        validated_row = schema.validate_row(row_dict)

        # Get primary key value
        pk_col = schema.get_primary_key_column()
        pk_val = validated_row.get(pk_col.name)
        if pk_val is None:
            raise SchemaError(f"Primary key column '{pk_col.name}' cannot be NULL")

        pk_key_str = str(pk_val)

        # Serialize payload
        payload_str = schema.serialize_row(validated_row)

        # Append record to binary storage
        record = Record(RecordType.INSERT, key=pk_key_str, value=payload_str)
        offset = table.storage.append_record(record)

        # Update in-memory primary index
        table.index.put(pk_key_str, offset)

        return QueryResult(affected_rows=1, message="1 row inserted.")

    def _execute_select(self, query: SelectQuery) -> QueryResult:
        table = self.db.get_table(query.table_name)
        schema = table.schema
        pk_col = schema.get_primary_key_column()

        # Determine target output columns
        if query.columns == ["*"]:
            target_cols = [c.name for c in schema.columns]
        else:
            for c in query.columns:
                schema.get_column(c)  # Validate column existence
            target_cols = query.columns

        matched_rows: List[Dict[str, Any]] = []

        # FAST PATH: Check if WHERE predicate is `pk_col = constant_val`
        is_fast_path = (
            query.where is not None
            and query.where.column == pk_col.name
            and query.where.operator == "="
        )

        if is_fast_path and query.where:
            pk_val_str = str(query.where.value)
            offset = table.index.get(pk_val_str)
            if offset is not None:
                record = table.storage.read_record_at(offset)
                if record.record_type != RecordType.DELETE:
                    row_dict = schema.deserialize_row(record.value)
                    if self._evaluate_where(query.where, row_dict):
                        matched_rows.append(self._filter_columns(row_dict, target_cols))
        else:
            # FULL SCAN PATH: Iterate through active indexed keys or storage file
            for key, offset in table.index.items():
                record = table.storage.read_record_at(offset)
                if record.record_type == RecordType.DELETE:
                    continue

                row_dict = schema.deserialize_row(record.value)
                if self._evaluate_where(query.where, row_dict):
                    matched_rows.append(self._filter_columns(row_dict, target_cols))

                if query.limit and len(matched_rows) >= query.limit:
                    break

        return QueryResult(columns=target_cols, rows=matched_rows, affected_rows=len(matched_rows))

    def _execute_delete(self, query: DeleteQuery) -> QueryResult:
        table = self.db.get_table(query.table_name)
        schema = table.schema
        pk_col = schema.get_primary_key_column()

        keys_to_delete = []

        # Fast path for WHERE pk = val
        if query.where and query.where.column == pk_col.name and query.where.operator == "=":
            pk_val_str = str(query.where.value)
            if table.index.contains(pk_val_str):
                keys_to_delete.append(pk_val_str)
        else:
            # Full scan path
            for key, offset in list(table.index.items()):
                record = table.storage.read_record_at(offset)
                if record.record_type == RecordType.DELETE:
                    continue
                row_dict = schema.deserialize_row(record.value)
                if self._evaluate_where(query.where, row_dict):
                    keys_to_delete.append(key)

        # Write tombstone records for deleted keys
        count = 0
        for key in keys_to_delete:
            tombstone_record = Record(RecordType.DELETE, key=key, value="")
            table.storage.append_record(tombstone_record)
            table.index.delete(key)
            count += 1

        return QueryResult(affected_rows=count, message=f"{count} row(s) deleted.")

    def _evaluate_where(self, where: Optional[WhereClause], row: Dict[str, Any]) -> bool:
        """Evaluate WHERE predicate against a row dictionary."""
        if where is None:
            return True

        if where.column not in row:
            raise SchemaError(f"Column '{where.column}' in WHERE clause does not exist in row")

        val = row[where.column]
        target = where.value
        op = where.operator

        if val is None:
            return False

        if op == "=":
            return val == target
        elif op == "!=":
            return val != target
        elif op == ">":
            return val > target
        elif op == "<":
            return val < target
        elif op == ">=":
            return val >= target
        elif op == "<=":
            return val <= target

        return False

    def _filter_columns(self, row: Dict[str, Any], target_cols: List[str]) -> Dict[str, Any]:
        """Extract only target columns for SELECT query response."""
        return {col: row.get(col) for col in target_cols}
