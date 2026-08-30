"""
Unit & Integration tests for HTTP Web Management Studio & REST API (src/minidb/web.py).
"""

import json
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import HTTPServer
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.database import Database
from minidb.transaction import TransactionManager
from minidb.web import MiniDBHTTPRequestHandler


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestWebStudioAPI(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.port = get_free_port()
        self.host = "127.0.0.1"

        db = Database(self.temp_dir.name)
        tm = TransactionManager(db)

        MiniDBHTTPRequestHandler.db = db
        MiniDBHTTPRequestHandler.tm = tm

        self.server = HTTPServer((self.host, self.port), MiniDBHTTPRequestHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        time.sleep(0.1)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temp_dir.cleanup()

    def test_http_api_endpoints(self):
        base_url = f"http://{self.host}:{self.port}"

        # 1. GET / index.html static file
        req = urllib.request.Request(f"{base_url}/")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            body = resp.read().decode("utf-8")
            self.assertIn("MiniDB Web Management Studio", body)

        # 2. POST /api/query - CREATE TABLE
        sql_create = "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, price FLOAT);"
        data = json.dumps({"sql": sql_create}).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/query",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            res_json = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(res_json["status"], "OK")

        # 3. POST /api/query - INSERT
        sql_insert = "INSERT INTO items VALUES (1, 'Laptop', 1200.50);"
        data_ins = json.dumps({"sql": sql_insert}).encode("utf-8")
        req_ins = urllib.request.Request(
            f"{base_url}/api/query",
            data=data_ins,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_ins) as resp:
            self.assertEqual(resp.status, 200)
            res_json = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(res_json["status"], "OK")

        # 4. GET /api/tables
        req_tbls = urllib.request.Request(f"{base_url}/api/tables")
        with urllib.request.urlopen(req_tbls) as resp:
            self.assertEqual(resp.status, 200)
            res_json = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(res_json["status"], "OK")
            self.assertEqual(len(res_json["tables"]), 1)
            self.assertEqual(res_json["tables"][0]["table_name"], "items")
            self.assertEqual(res_json["tables"][0]["row_count"], 1)

        # 5. GET /api/schema?table=items
        req_schema = urllib.request.Request(f"{base_url}/api/schema?table=items")
        with urllib.request.urlopen(req_schema) as resp:
            self.assertEqual(resp.status, 200)
            res_json = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(res_json["status"], "OK")
            self.assertEqual(len(res_json["columns"]), 3)

        # 6. GET /api/stats
        req_stats = urllib.request.Request(f"{base_url}/api/stats")
        with urllib.request.urlopen(req_stats) as resp:
            self.assertEqual(resp.status, 200)
            res_json = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(res_json["status"], "OK")
            self.assertEqual(res_json["tables_count"], 1)
            self.assertEqual(res_json["total_rows"], 1)


if __name__ == "__main__":
    unittest.main()
