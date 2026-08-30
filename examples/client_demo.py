#!/usr/bin/env python3
"""
TCP Client Demo Example for MiniDB.
"""

import sys
import tempfile
import time
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.server import Server
from minidb.client import Client


def main():
    with tempfile.TemporaryDirectory() as tmp:
        server = Server(data_dir=tmp, host="127.0.0.1", port=9123)
        server.start(background=True)
        time.sleep(0.1)

        client = Client(host="127.0.0.1", port=9123)
        client.connect()

        client.execute_sql("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);")
        client.execute_sql("INSERT INTO users VALUES (1, 'Punith');")
        res = client.execute_sql("SELECT * FROM users;")

        print("TCP Response:", res)

        client.close()
        server.stop()


if __name__ == "__main__":
    main()
