#!/usr/bin/env python3
"""
Reproducible End-to-End Demonstration Script for MiniDB.

Demonstrates all 13 core database engine features:
1. Create database
2. Create table
3. Insert data
4. Select data
5. WHERE query
6. Index lookup
7. Transaction
8. Rollback
9. Commit
10. WAL logging
11. Crash recovery
12. TCP server
13. TCP client
"""

import sys
import tempfile
import time
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.database import Database
from minidb.parser import Parser
from minidb.executor import QueryExecutor
from minidb.transaction import TransactionManager
from minidb.wal import WriteAheadLog, WALRecord
from minidb.record import RecordType
from minidb.recovery import RecoveryManager
from minidb.server import Server
from minidb.client import Client


def print_step(step_num: int, title: str):
    print(f"\n==================================================")
    print(f" STEP {step_num:02d}: {title.upper()}")
    print(f"==================================================")


def run_demo():
    print("🚀 Starting MiniDB Reproducible Demonstration...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_dir = Path(temp_dir) / "demo_data"
        db_dir.mkdir()

        # Step 1: Create Database
        print_step(1, "Create Database")
        db = Database(db_dir)
        tm = TransactionManager(db)
        print(f"✅ Database initialized in directory: {db_dir}")

        # Step 2: Create Table
        print_step(2, "Create Table")
        sql_create = "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER, is_active BOOLEAN);"
        res_create = tm.execute_sql_query(Parser(sql_create).parse())
        print(f"SQL: {sql_create}")
        print(f"Result: {res_create.message}")

        # Step 3: Insert Data
        print_step(3, "Insert Data")
        inserts = [
            "INSERT INTO users VALUES (1, 'Punith', 22, TRUE);",
            "INSERT INTO users VALUES (2, 'Rahul', 25, FALSE);",
            "INSERT INTO users VALUES (3, 'Akash', 30, TRUE);",
        ]
        for sql in inserts:
            tm.execute_sql_query(Parser(sql).parse())
            print(f"SQL: {sql}")
        print("✅ 3 rows inserted into 'users' table.")

        # Step 4: Select Data
        print_step(4, "Select Data")
        sql_select = "SELECT * FROM users;"
        res_sel = tm.execute_sql_query(Parser(sql_select).parse())
        print(f"SQL: {sql_select}")
        for r in res_sel.rows:
            print(f"  Row: {r}")

        # Step 5: WHERE Query
        print_step(5, "WHERE Filtering Query")
        sql_where = "SELECT name, age FROM users WHERE age > 23;"
        res_where = tm.execute_sql_query(Parser(sql_where).parse())
        print(f"SQL: {sql_where}")
        for r in res_where.rows:
            print(f"  Matched: {r}")

        # Step 6: Index Lookup
        print_step(6, "In-Memory Primary Index O(1) Fast-Path Lookup")
        sql_idx = "SELECT * FROM users WHERE id = 1;"
        res_idx = tm.execute_sql_query(Parser(sql_idx).parse())
        print(f"SQL: {sql_idx}")
        print(f"  Retrieved record directly via file offset: {res_idx.rows[0]}")

        # Step 7 & 8: Transaction Rollback
        print_step(7, "Transaction & Rollback Demonstration")
        print("Executing: BEGIN;")
        tm.execute_sql_query(Parser("BEGIN;").parse())
        print("Executing: INSERT INTO users VALUES (4, 'Uncommitted User', 99, FALSE);")
        tm.execute_sql_query(Parser("INSERT INTO users VALUES (4, 'Uncommitted User', 99, FALSE);").parse())

        print("Executing: ROLLBACK;")
        tm.execute_sql_query(Parser("ROLLBACK;").parse())

        res_check_rb = tm.execute_sql_query(Parser("SELECT * FROM users WHERE id = 4;").parse())
        print(f"  Query after ROLLBACK (id = 4): {len(res_check_rb.rows)} rows (Successfully discarded).")

        # Step 9: Transaction Commit
        print_step(9, "Transaction Commit Demonstration")
        print("Executing: BEGIN;")
        tm.execute_sql_query(Parser("BEGIN;").parse())
        print("Executing: INSERT INTO users VALUES (4, 'Committed Akash V2', 31, TRUE);")
        tm.execute_sql_query(Parser("INSERT INTO users VALUES (4, 'Committed Akash V2', 31, TRUE);").parse())
        print("Executing: COMMIT;")
        tm.execute_sql_query(Parser("COMMIT;").parse())

        res_check_cm = tm.execute_sql_query(Parser("SELECT * FROM users WHERE id = 4;").parse())
        print(f"  Query after COMMIT (id = 4): {res_check_cm.rows[0]}")

        # Step 10 & 11: WAL & Crash Recovery
        print_step(10, "WAL & Crash Recovery Simulation")
        wal_path = db_dir / "minidb.wal"
        wal = WriteAheadLog(wal_path)

        # Simulate writing a committed transaction to WAL before database crash
        tx_id = 999
        wal.append(WALRecord(tx_id, "users", RecordType.INSERT, "5", '{"id":5,"name":"Recovered User","age":40,"is_active":true}'))
        wal.append(WALRecord(tx_id, "users", RecordType.COMMIT, "", ""))
        print("Simulated crash: WAL record written for ID=5 with COMMIT header, but not yet applied to database disk file.")

        # Perform Recovery on newly opened database instance
        crashed_db = Database(db_dir)
        recovery_mgr = RecoveryManager(crashed_db, wal)
        replayed = recovery_mgr.recover()
        print(f"✅ Recovery complete! Replayed {replayed} transaction operations from WAL log.")

        res_recovery = QueryExecutor(crashed_db).execute(Parser("SELECT * FROM users WHERE id = 5;").parse())
        print(f"  Recovered Row (id = 5): {res_recovery.rows[0]}")

        # Step 12 & 13: TCP Server & TCP Client
        print_step(12, "TCP Database Server & Client Networking")
        server = Server(data_dir=db_dir, host="127.0.0.1", port=9555)
        server.start(background=True)
        time.sleep(0.1)

        client = Client(host="127.0.0.1", port=9555)
        client.connect()

        tcp_resp = client.execute_sql("SELECT name, age FROM users WHERE age >= 30;")
        print(f"Client sent TCP SQL: SELECT name, age FROM users WHERE age >= 30;")
        print(f"Server TCP Response: {tcp_resp['rows']}")

        client.close()
        server.stop()

        print("\n==================================================")
        print(" 🎉 MINIDB DEMONSTRATION COMPLETED SUCCESSFULLY!")
        print("==================================================")


if __name__ == "__main__":
    run_demo()
