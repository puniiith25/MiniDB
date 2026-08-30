#!/usr/bin/env python3
"""
Performance Benchmarking Script for MiniDB.

Measures real-world execution times for:
1. Indexed O(1) lookup
2. Full sequential table scan

Uses time.perf_counter() from Python stdlib to record accurate empirical measurements.
"""

import sys
import tempfile
import time
from pathlib import Path

# Add src to sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.database import Database
from minidb.schema import TableSchema, Column, DataType
from minidb.parser import Parser
from minidb.executor import QueryExecutor


def run_benchmark(num_records: int = 5000, num_runs: int = 100):
    print("==================================================")
    print("           MINIDB PERFORMANCE BENCHMARK          ")
    print("==================================================")
    print(f"Populating benchmark table with {num_records:,} records...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db = Database(temp_dir)
        executor = QueryExecutor(db)

        # 1. Create table
        schema = TableSchema(
            name="benchmark_users",
            columns=[
                Column("id", DataType.INTEGER, primary_key=True),
                Column("name", DataType.TEXT),
                Column("score", DataType.FLOAT),
            ],
        )
        db.create_table(schema)
        table = db.get_table("benchmark_users")

        # 2. Insert records
        start_insert = time.perf_counter()
        for i in range(1, num_records + 1):
            sql = f"INSERT INTO benchmark_users VALUES ({i}, 'User_{i}', {i * 1.5});"
            executor.execute(Parser(sql).parse())
        insert_duration = time.perf_counter() - start_insert

        print(f"Inserted {num_records:,} records in {insert_duration:.3f} seconds ({num_records/insert_duration:.0f} ops/sec)\n")

        target_id = num_records // 2
        target_name = f"User_{target_id}"

        # 3. Benchmark Indexed O(1) Lookup (WHERE id = target_id)
        indexed_query = Parser(f"SELECT * FROM benchmark_users WHERE id = {target_id};").parse()
        
        # Warmup
        executor.execute(indexed_query)

        indexed_times = []
        for _ in range(num_runs):
            t0 = time.perf_counter()
            res = executor.execute(indexed_query)
            t1 = time.perf_counter()
            indexed_times.append((t1 - t0) * 1000)  # Convert to ms

        avg_indexed = sum(indexed_times) / len(indexed_times)

        # 4. Benchmark Full Scan Lookup (WHERE name = target_name)
        scan_query = Parser(f"SELECT * FROM benchmark_users WHERE name = '{target_name}';").parse()
        
        # Warmup
        executor.execute(scan_query)

        scan_times = []
        for _ in range(num_runs):
            t0 = time.perf_counter()
            res = executor.execute(scan_query)
            t1 = time.perf_counter()
            scan_times.append((t1 - t0) * 1000)  # Convert to ms

        avg_scan = sum(scan_times) / len(scan_times)

        speedup = avg_scan / avg_indexed if avg_indexed > 0 else 1.0

        print(f"Benchmark Results ({num_runs} iterations):")
        print("--------------------------------------------------")
        print(f"Records in Table : {num_records:,}")
        print(f"Full Scan Lookup : {avg_scan:.4f} ms (average)")
        print(f"Indexed O(1)     : {avg_indexed:.4f} ms (average)")
        print(f"Speedup Factor   : {speedup:.1f}x faster with Primary Index")
        print("--------------------------------------------------\n")


if __name__ == "__main__":
    records_count = 2000
    if len(sys.argv) > 1:
        try:
            records_count = int(sys.argv[1])
        except ValueError:
            pass
    run_benchmark(num_records=records_count, num_runs=50)
