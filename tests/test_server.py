"""
Unit & Integration tests for TCP Database Server & Client (src/minidb/server.py).
"""

import sys
import tempfile
import time
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.server import Server
from minidb.client import Client


class TestTCPServer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.port = 9876  # Ephemeral test port
        self.server = Server(data_dir=self.temp_dir.name, host="127.0.0.1", port=self.port)
        self.server.start(background=True)
        time.sleep(0.1)  # Allow socket bind

        self.client = Client(host="127.0.0.1", port=self.port)
        self.client.connect()

    def tearDown(self):
        self.client.close()
        self.server.stop()
        self.temp_dir.cleanup()

    def test_tcp_server_client_workflow(self):
        # 1. CREATE TABLE
        resp_create = self.client.execute_sql(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER);"
        )
        self.assertEqual(resp_create["status"], "OK")

        # 2. INSERT
        resp_ins1 = self.client.execute_sql("INSERT INTO users VALUES (1, 'Punith', 22);")
        resp_ins2 = self.client.execute_sql("INSERT INTO users VALUES (2, 'Rahul', 25);")
        self.assertEqual(resp_ins1["status"], "OK")
        self.assertEqual(resp_ins2["status"], "OK")

        # 3. SELECT
        resp_sel = self.client.execute_sql("SELECT * FROM users WHERE id = 1;")
        self.assertEqual(resp_sel["status"], "OK")
        self.assertEqual(len(resp_sel["rows"]), 1)
        self.assertEqual(resp_sel["rows"][0]["name"], "Punith")

        # 4. DOT COMMANDS
        resp_tables = self.client.execute_command(".tables")
        self.assertEqual(resp_tables["status"], "OK")
        self.assertEqual(resp_tables["rows"][0]["table_name"], "users")

        resp_schema = self.client.execute_command(".schema", ["users"])
        self.assertEqual(resp_schema["status"], "OK")
        self.assertEqual(len(resp_schema["rows"]), 3)


if __name__ == "__main__":
    unittest.main()
