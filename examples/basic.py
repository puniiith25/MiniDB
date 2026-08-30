#!/usr/bin/env python3
"""
Basic Usage Example for MiniDB.
"""

import sys
import tempfile
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.database import Database
from minidb.parser import Parser
from minidb.executor import QueryExecutor


def main():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(tmp)
        executor = QueryExecutor(db)

        executor.execute(Parser("CREATE TABLE products (sku TEXT PRIMARY KEY, name TEXT, price FLOAT);").parse())
        executor.execute(Parser("INSERT INTO products VALUES ('SKU-100', 'Laptop', 999.99);").parse())
        executor.execute(Parser("INSERT INTO products VALUES ('SKU-101', 'Mouse', 24.50);").parse())

        res = executor.execute(Parser("SELECT * FROM products WHERE price < 100.0;").parse())
        print("Products under $100:", res.rows)


if __name__ == "__main__":
    main()
