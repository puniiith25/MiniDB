"""
Binary Record Format for MiniDB.

Uses struct and zlib.crc32 to serialize and deserialize data records into
a custom compact binary format with corruption detection.
"""

import struct
import zlib
from enum import IntEnum
from typing import NamedTuple
from minidb.errors import CorruptionError, StorageError

# Magic bytes identifier: 0x4D42 ("MB")
MAGIC_BYTES = b"MB"
MAGIC_INT = 0x4D42

# Binary Header Format:
# > (big-endian), H (2B magic), B (1B type), H (2B key_len), I (4B val_len)
HEADER_STRUCT = struct.Struct(">HBH I")
HEADER_SIZE = HEADER_STRUCT.size  # 9 bytes

CRC_STRUCT = struct.Struct(">I")
CRC_SIZE = CRC_STRUCT.size  # 4 bytes


class RecordType(IntEnum):
    INSERT = 1
    UPDATE = 2
    DELETE = 3
    COMMIT = 4
    ROLLBACK = 5


class Record(NamedTuple):
    record_type: RecordType
    key: str
    value: str
    tx_id: int = 0

    def serialize(self) -> bytes:
        """
        Serialize Record instance into binary format.
        
        Binary Layout:
        [Magic (2B)][Type (1B)][Key Length (2B)][Value Length (4B)][Key Bytes][Value Bytes][CRC32 (4B)]
        """
        key_bytes = self.key.encode("utf-8")
        value_bytes = self.value.encode("utf-8")

        if len(key_bytes) > 65535:
            raise StorageError(f"Key length exceeds 65535 bytes limit ({len(key_bytes)})")
        if len(value_bytes) > 4294967295:
            raise StorageError(f"Value length exceeds 4GB limit ({len(value_bytes)})")

        header = HEADER_STRUCT.pack(
            MAGIC_INT,
            int(self.record_type),
            len(key_bytes),
            len(value_bytes),
        )

        payload = header + key_bytes + value_bytes
        crc = zlib.crc32(payload) & 0xFFFFFFFF
        checksum_bytes = CRC_STRUCT.pack(crc)

        return payload + checksum_bytes

    @classmethod
    def deserialize_from_bytes(cls, data: bytes) -> tuple["Record", int]:
        """
        Deserialize Record from binary data.
        
        Returns tuple of (Record, total_bytes_read).
        Raises CorruptionError if magic header or CRC32 checksum fails.
        """
        if len(data) < HEADER_SIZE + CRC_SIZE:
            raise StorageError("Insufficient bytes for binary record header")

        magic, rec_type_raw, key_len, val_len = HEADER_STRUCT.unpack(data[:HEADER_SIZE])

        if magic != MAGIC_INT:
            raise CorruptionError(f"Invalid magic header: {hex(magic)} (expected {hex(MAGIC_INT)})")

        try:
            record_type = RecordType(rec_type_raw)
        except ValueError:
            raise CorruptionError(f"Unknown record type byte: {rec_type_raw}")

        total_size = HEADER_SIZE + key_len + val_len + CRC_SIZE
        if len(data) < total_size:
            raise StorageError(f"Truncated record: expected {total_size} bytes, got {len(data)}")

        key_start = HEADER_SIZE
        key_end = key_start + key_len
        val_end = key_end + val_len

        key_bytes = data[key_start:key_end]
        val_bytes = data[key_end:val_end]
        expected_crc = CRC_STRUCT.unpack(data[val_end:total_size])[0]

        payload = data[:val_end]
        actual_crc = zlib.crc32(payload) & 0xFFFFFFFF

        if actual_crc != expected_crc:
            raise CorruptionError(
                f"CRC32 mismatch: calculated {hex(actual_crc)}, expected {hex(expected_crc)}"
            )

        try:
            key = key_bytes.decode("utf-8")
            value = val_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise CorruptionError(f"UTF-8 decode failure in record: {e}")

        return cls(record_type=record_type, key=key, value=value), total_size
