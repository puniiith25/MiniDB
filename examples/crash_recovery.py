#!/usr/bin/env python3
"""
Crash Recovery Example for MiniDB.
"""

import sys
import tempfile
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


def main():
    with tempfile.TemporaryDirectory() as tmp:
        db_dir = Path(tmp)
        db = Database(db_dir)

        # Create schema
        db.create_table(
            TableSchema("orders", [Column("id", DataType.INTEGER, primary_key=True), Column("amount", DataType.FLOAT)])
        )

        # Write WAL committed entry
        wal = WriteAheadLog(db_dir / "minidb.wal")
        wal.append(WALRecord(10, "orders", RecordType.INSERT, "1", '{"id":1,"amount":250.75}'))
        wal.append(WALRecord(10, "orders", RecordType.COMMIT, "", ""))

        # Crash recovery
        recovered_db = Database(db_dir)
        RecoveryManager(recovered_db, wal).recover()

        res = QueryExecutor(recovered_db).execute(Parser("SELECT * FROM orders;").parse())
        print("Recovered Orders:", res.rows)


if __name__ == "__main__":
    main()
