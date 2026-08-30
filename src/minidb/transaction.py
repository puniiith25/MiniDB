"""
Transaction Manager Engine for MiniDB.

Implements ACID transaction boundaries (BEGIN, COMMIT, ROLLBACK) with WAL logging
and in-memory uncommitted operation buffering.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from minidb.database import Database, Table
from minidb.wal import WriteAheadLog, WALRecord
from minidb.record import Record, RecordType
from minidb.schema import TableSchema
from minidb.parser import (
    ASTQuery,
    CreateTableQuery,
    InsertQuery,
    SelectQuery,
    DeleteQuery,
    BeginTransactionQuery,
    CommitTransactionQuery,
    RollbackTransactionQuery,
    WhereClause,
)
from minidb.executor import QueryExecutor, QueryResult
from minidb.errors import TransactionError, SchemaError, DatabaseError


@dataclass
class BufferedOp:
    table_name: str
    record_type: RecordType
    key: str
    payload: str  # Serialized json row payload
    row_dict: Dict[str, Any]


class TransactionManager:
    """
    Manages transaction lifecycle and integrates with WAL and QueryExecutor.
    """

    def __init__(self, db: Database, wal: Optional[WriteAheadLog] = None):
        self.db = db
        self.wal = wal or WriteAheadLog(db.data_dir / "minidb.wal")
        self.executor = QueryExecutor(db)

        self.in_transaction: bool = False
        self.current_tx_id: int = 0
        self.next_tx_id: int = 1
        self._buffer: List[BufferedOp] = []

    def execute_sql_query(self, query: ASTQuery) -> QueryResult:
        """
        Execute an AST query within current transaction context.
        """
        if isinstance(query, BeginTransactionQuery):
            return self.begin()
        elif isinstance(query, CommitTransactionQuery):
            return self.commit()
        elif isinstance(query, RollbackTransactionQuery):
            return self.rollback()

        if not self.in_transaction:
            # Autocommit mode (tx_id = 0)
            return self.executor.execute(query)

        # Active transaction mode: buffer DML operations
        if isinstance(query, CreateTableQuery):
            raise TransactionError("DDL CREATE TABLE is not permitted inside an active transaction")

        elif isinstance(query, InsertQuery):
            return self._tx_insert(query)

        elif isinstance(query, SelectQuery):
            return self._tx_select(query)

        elif isinstance(query, DeleteQuery):
            return self._tx_delete(query)

        else:
            raise TransactionError(f"Unsupported transaction query node: {type(query).__name__}")

    def begin(self) -> QueryResult:
        """Start a new transaction."""
        if self.in_transaction:
            raise TransactionError("Transaction is already active")

        self.in_transaction = True
        self.current_tx_id = self.next_tx_id
        self.next_tx_id += 1
        self._buffer.clear()

        # Log BEGIN in WAL
        self.wal.append(
            WALRecord(self.current_tx_id, "", RecordType.INSERT, "BEGIN", ""),
            fsync=True,
        )
        return QueryResult(message=f"Transaction {self.current_tx_id} started (BEGIN).")

    def commit(self) -> QueryResult:
        """Commit current transaction to persistent disk storage."""
        if not self.in_transaction:
            raise TransactionError("No active transaction to commit")

        # 1. Log COMMIT in WAL first
        self.wal.append(
            WALRecord(self.current_tx_id, "", RecordType.COMMIT, "COMMIT", ""),
            fsync=True,
        )

        # 2. Flush buffered DML operations to table storage files & indexes
        affected = 0
        for op in self._buffer:
            table = self.db.get_table(op.table_name)
            record = Record(op.record_type, key=op.key, value=op.payload)
            offset = table.storage.append_record(record, fsync=True)

            if op.record_type == RecordType.DELETE:
                table.index.delete(op.key)
            else:
                table.index.put(op.key, offset)
            affected += 1

        tx_id = self.current_tx_id
        self._reset_tx()

        return QueryResult(
            affected_rows=affected,
            message=f"Transaction {tx_id} committed successfully ({affected} operation(s) applied).",
        )

    def rollback(self) -> QueryResult:
        """Rollback current transaction, discarding buffered changes."""
        if not self.in_transaction:
            raise TransactionError("No active transaction to rollback")

        # Log ROLLBACK in WAL
        self.wal.append(
            WALRecord(self.current_tx_id, "", RecordType.ROLLBACK, "ROLLBACK", ""),
            fsync=True,
        )

        tx_id = self.current_tx_id
        self._reset_tx()

        return QueryResult(message=f"Transaction {tx_id} rolled back. Changes discarded.")

    def _reset_tx(self) -> None:
        self.in_transaction = False
        self.current_tx_id = 0
        self._buffer.clear()

    def _tx_insert(self, query: InsertQuery) -> QueryResult:
        table = self.db.get_table(query.table_name)
        schema = table.schema

        if query.columns:
            row_dict = dict(zip(query.columns, query.values))
        else:
            row_dict = {col.name: val for col, val in zip(schema.columns, query.values)}

        validated_row = schema.validate_row(row_dict)
        pk_col = schema.get_primary_key_column()
        pk_val = validated_row.get(pk_col.name)
        if pk_val is None:
            raise SchemaError(f"Primary key '{pk_col.name}' cannot be NULL")

        pk_key_str = str(pk_val)
        payload_str = schema.serialize_row(validated_row)

        # Log to WAL
        self.wal.append(
            WALRecord(self.current_tx_id, query.table_name, RecordType.INSERT, pk_key_str, payload_str),
            fsync=True,
        )

        # Buffer in memory
        self._buffer.append(
            BufferedOp(
                table_name=query.table_name,
                record_type=RecordType.INSERT,
                key=pk_key_str,
                payload=payload_str,
                row_dict=validated_row,
            )
        )

        return QueryResult(affected_rows=1, message="1 row inserted (buffered in transaction).")

    def _tx_select(self, query: SelectQuery) -> QueryResult:
        # Get committed rows from underlying executor
        committed_res = self.executor.execute(query)
        table = self.db.get_table(query.table_name)
        schema = table.schema

        # Overlay transaction buffer changes
        row_map: Dict[str, Dict[str, Any]] = {}
        pk_col = schema.get_primary_key_column().name

        # Populate with committed disk state
        for r in committed_res.rows:
            row_map[str(r[pk_col])] = r

        # Apply buffer overrides
        for op in self._buffer:
            if op.table_name == query.table_name:
                if op.record_type == RecordType.DELETE:
                    row_map.pop(op.key, None)
                else:
                    row_map[op.key] = op.row_dict

        # Filter by WHERE predicate & columns
        target_cols = query.columns if query.columns != ["*"] else [c.name for c in schema.columns]
        result_rows = []

        for row in row_map.values():
            if self.executor._evaluate_where(query.where, row):
                result_rows.append(self.executor._filter_columns(row, target_cols))

        return QueryResult(columns=target_cols, rows=result_rows, affected_rows=len(result_rows))

    def _tx_delete(self, query: DeleteQuery) -> QueryResult:
        # Find matching rows in merged state
        select_query = SelectQuery(table_name=query.table_name, columns=["*"], where=query.where)
        curr_res = self._tx_select(select_query)
        table = self.db.get_table(query.table_name)
        pk_col = table.schema.get_primary_key_column().name

        count = 0
        for r in curr_res.rows:
            key_str = str(r[pk_col])
            # Log to WAL
            self.wal.append(
                WALRecord(self.current_tx_id, query.table_name, RecordType.DELETE, key_str, ""),
                fsync=True,
            )
            # Buffer delete
            self._buffer.append(
                BufferedOp(
                    table_name=query.table_name,
                    record_type=RecordType.DELETE,
                    key=key_str,
                    payload="",
                    row_dict={},
                )
            )
            count += 1

        return QueryResult(affected_rows=count, message=f"{count} row(s) deleted (buffered in transaction).")
