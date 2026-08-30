"""
TCP Network Client for MiniDB.

Connects to MiniDB TCP Database Server over sockets and handles requests.
"""

import socket
from typing import Any, Dict, List, Optional
from minidb.protocol import send_message, receive_message
from minidb.errors import DatabaseError, ProtocolError


class Client:
    """
    MiniDB Client connecting to TCP server.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9000):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None

    def connect(self) -> None:
        """Connect to TCP server."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

    def execute_sql(self, sql: str) -> Dict[str, Any]:
        """Send SQL query statement to server and return response."""
        if not self.sock:
            self.connect()

        send_message(self.sock, {"sql": sql})
        resp = receive_message(self.sock)
        if resp is None:
            raise ProtocolError("Server connection closed unexpectedly")
        return resp

    def execute_command(self, command: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Send dot-command (.tables, .schema, .help) to server."""
        if not self.sock:
            self.connect()

        send_message(self.sock, {"command": command, "args": args or []})
        resp = receive_message(self.sock)
        if resp is None:
            raise ProtocolError("Server connection closed unexpectedly")
        return resp

    def close(self) -> None:
        """Close client socket."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
