"""
Binary Length-Prefixed Wire Protocol for MiniDB TCP Client-Server.

Frames messages with a 4-byte big-endian length prefix (>I).
"""

import json
import struct
from socket import socket
from typing import Any, Dict, Optional
from minidb.errors import ProtocolError

LENGTH_HEADER_STRUCT = struct.Struct(">I")
LENGTH_HEADER_SIZE = LENGTH_HEADER_STRUCT.size  # 4 bytes


def send_message(sock: socket, payload: Dict[str, Any]) -> None:
    """
    Serialize payload dict to JSON, format with length prefix, and send over socket.
    """
    json_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    header = LENGTH_HEADER_STRUCT.pack(len(json_bytes))
    sock.sendall(header + json_bytes)


def receive_message(sock: socket) -> Optional[Dict[str, Any]]:
    """
    Read length-prefixed JSON payload from socket.
    Returns None if connection closed cleanly.
    """
    header_bytes = _read_exact(sock, LENGTH_HEADER_SIZE)
    if not header_bytes:
        return None

    length = LENGTH_HEADER_STRUCT.unpack(header_bytes)[0]
    if length > 10 * 1024 * 1024:  # Safety guard: max 10MB message
        raise ProtocolError(f"Message payload size exceeds 10MB limit ({length} bytes)")

    json_bytes = _read_exact(sock, length)
    if not json_bytes or len(json_bytes) < length:
        raise ProtocolError("Unexpected connection closure while reading payload data")

    try:
        return json.loads(json_bytes.decode("utf-8"))
    except Exception as e:
        raise ProtocolError(f"Failed to parse JSON protocol payload: {e}")


def _read_exact(sock: socket, num_bytes: int) -> bytes:
    """Helper to read exactly num_bytes from socket."""
    buffer = bytearray()
    while len(buffer) < num_bytes:
        chunk = sock.recv(num_bytes - len(buffer))
        if not chunk:
            break
        buffer.extend(chunk)
    return bytes(buffer)
