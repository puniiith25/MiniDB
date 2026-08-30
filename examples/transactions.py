#!/usr/bin/env python3
"""
Transactions Example for MiniDB.
"""

import sys
import tempfile
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.database import Database
from minidb.parser import Parser
from minidb.transaction import TransactionManager


def main():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(tmp)
        tm = TransactionManager(db)

        tm.execute_sql_query(Parser("CREATE TABLE accounts (id INTEGER PRIMARY KEY, balance FLOAT);").parse())
        tm.execute_sql_query(Parser("INSERT INTO accounts VALUES (1, 1000.0);").parse())

        # Begin transaction
        tm.execute_sql_query(Parser("BEGIN;").parse())
        tm.execute_sql_query(Parser("INSERT INTO accounts VALUES (2, 500.0);").parse())
        # Rollback
        tm.execute_sql_query(Parser("ROLLBACK;").parse())

        res = tm.execute_sql_query(Parser("SELECT * FROM accounts;").parse())
        print("Accounts after ROLLBACK:", res.rows)


if __name__ == "__main__":
    main()
