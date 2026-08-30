"""
TCP Database Server for MiniDB.

Multithreaded socket server listening on 127.0.0.1:9000 using standard library socket.
"""

import socket
import threading
from pathlib import Path
from typing import Optional
from minidb.database import Database
from minidb.transaction import TransactionManager
from minidb.parser import Parser
from minidb.protocol import send_message, receive_message
from minidb.errors import DatabaseError, ParseError, TransactionError, SchemaError


class Server:
    """
    MiniDB TCP Server handling multi-client socket connections.
    """

    def __init__(self, data_dir: str | Path = "./data", host: str = "127.0.0.1", port: int = 9000):
        self.data_dir = Path(data_dir).resolve()
        self.host = host
        self.port = port

        self.db = Database(self.data_dir)
        self.server_socket: Optional[socket.socket] = None
        self.is_running: bool = False
        self._threads: list[threading.Thread] = []

    def start(self, background: bool = False) -> None:
        """Start listening for TCP client connections."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(128)
        self.is_running = True

        print(f"🚀 MiniDB Server started at tcp://{self.host}:{self.port} (data_dir: {self.data_dir})")

        if background:
            t = threading.Thread(target=self._listen_loop, daemon=True)
            t.start()
            self._threads.append(t)
        else:
            self._listen_loop()

    def _listen_loop(self) -> None:
        while self.is_running:
            try:
                client_sock, addr = self.server_socket.accept()
                t = threading.Thread(target=self._handle_client, args=(client_sock, addr), daemon=True)
                t.start()
                self._threads.append(t)
            except Exception:
                if not self.is_running:
                    break

    def _handle_client(self, client_sock: socket.socket, addr: tuple[str, int]) -> None:
        """Client connection session handler thread."""
        tm = TransactionManager(self.db)
        try:
            while self.is_running:
                req = receive_message(client_sock)
                if req is None:
                    break  # Client disconnected

                response = self._process_request(tm, req)
                send_message(client_sock, response)
        except Exception as e:
            pass
        finally:
            client_sock.close()

    def _process_request(self, tm: TransactionManager, req: dict) -> dict:
        """Process incoming client command or SQL query."""
        cmd = req.get("command")
        sql = req.get("sql")

        try:
            if cmd == ".tables":
                tables = self.db.list_tables()
                return {"status": "OK", "rows": [{"table_name": t} for t in tables], "columns": ["table_name"], "message": f"{len(tables)} table(s)"}

            elif cmd == ".schema":
                tbl_name = req.get("args", [""])[0]
                if not tbl_name:
                    return {"status": "ERROR", "error": "Usage: .schema <table_name>"}
                table = self.db.get_table(tbl_name)
                cols_info = [
                    {
                        "column": c.name,
                        "type": c.data_type.value,
                        "primary_key": c.primary_key,
                        "nullable": c.nullable,
                    }
                    for c in table.schema.columns
                ]
                return {"status": "OK", "rows": cols_info, "columns": ["column", "type", "primary_key", "nullable"]}

            elif cmd == ".help":
                return {
                    "status": "OK",
                    "message": "MiniDB CLI Help:\n"
                               "  .tables            List all tables\n"
                               "  .schema <table>    Show table schema\n"
                               "  .help              Show this help menu\n"
                               "  .quit              Exit REPL\n"
                               "  <SQL Query>        Execute SQL query statement",
                }

            elif sql:
                ast = Parser(sql).parse()
                result = tm.execute_sql_query(ast)
                return {
                    "status": "OK",
                    "columns": result.columns,
                    "rows": result.rows,
                    "affected_rows": result.affected_rows,
                    "message": result.message,
                }
            else:
                return {"status": "ERROR", "error": "Invalid request: missing 'sql' or 'command'"}

        except (DatabaseError, ParseError, TransactionError, SchemaError) as e:
            return {"status": "ERROR", "error": str(e)}
        except Exception as e:
            return {"status": "ERROR", "error": f"Internal Server Error: {e}"}

    def stop(self) -> None:
        """Stop TCP server and close socket."""
        self.is_running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MiniDB TCP Database Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host IP to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9000, help="Port to listen (default: 9000)")
    parser.add_argument("--data-dir", default="./data", help="Directory path for database files")

    args = parser.parse_args()
    server = Server(data_dir=args.data_dir, host=args.host, port=args.port)
    try:
        server.start(background=False)
    except KeyboardInterrupt:
        print("\nShutting down MiniDB Server.")
        server.stop()


if __name__ == "__main__":
    main()
