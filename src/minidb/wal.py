"""
Write-Ahead Logging (WAL) System for MiniDB.

Provides durability and atomicity by recording database operations to disk log
with os.fsync prior to modifying persistent table data files.
"""

import os
import struct
import zlib
from pathlib import Path
from typing import Generator, List, NamedTuple, Optional
from minidb.record import RecordType
from minidb.errors import CorruptionError, StorageError

# WAL Magic header identifier: 0x5741 ("WA")
WAL_MAGIC_INT = 0x5741

# Binary Header Format:
# > (big-endian), H (2B magic), Q (8B tx_id), B (1B type), H (2B table_len), H (2B key_len), I (4B val_len)
WAL_HEADER_STRUCT = struct.Struct(">HQB HHI")
WAL_HEADER_SIZE = WAL_HEADER_STRUCT.size  # 19 bytes

CRC_STRUCT = struct.Struct(">I")
CRC_SIZE = CRC_STRUCT.size  # 4 bytes


class WALRecord(NamedTuple):
    tx_id: int
    table_name: str
    record_type: RecordType
    key: str
    value: str

    def serialize(self) -> bytes:
        """
        Serialize WALRecord into binary format.
        Layout:
        [Magic (2B)][TxID (8B)][Type (1B)][TableLen (2B)][KeyLen (2B)][ValLen (4B)][TableBytes][KeyBytes][ValBytes][CRC32 (4B)]
        """
        tbl_bytes = self.table_name.encode("utf-8")
        key_bytes = self.key.encode("utf-8")
        val_bytes = self.value.encode("utf-8")

        header = WAL_HEADER_STRUCT.pack(
            WAL_MAGIC_INT,
            self.tx_id,
            int(self.record_type),
            len(tbl_bytes),
            len(key_bytes),
            len(val_bytes),
        )

        payload = header + tbl_bytes + key_bytes + val_bytes
        crc = zlib.crc32(payload) & 0xFFFFFFFF
        checksum_bytes = CRC_STRUCT.pack(crc)

        return payload + checksum_bytes

    @classmethod
    def deserialize_from_bytes(cls, data: bytes) -> tuple["WALRecord", int]:
        """
        Deserialize WALRecord from binary data bytes.
        """
        if len(data) < WAL_HEADER_SIZE + CRC_SIZE:
            raise StorageError("Insufficient bytes for WAL record header")

        magic, tx_id, rec_type_raw, tbl_len, key_len, val_len = WAL_HEADER_STRUCT.unpack(
            data[:WAL_HEADER_SIZE]
        )

        if magic != WAL_MAGIC_INT:
            raise CorruptionError(f"Invalid WAL magic header: {hex(magic)}")

        try:
            record_type = RecordType(rec_type_raw)
        except ValueError:
            raise CorruptionError(f"Unknown WAL record type byte: {rec_type_raw}")

        total_size = WAL_HEADER_SIZE + tbl_len + key_len + val_len + CRC_SIZE
        if len(data) < total_size:
            raise StorageError(f"Truncated WAL record: expected {total_size} bytes, got {len(data)}")

        tbl_start = WAL_HEADER_SIZE
        key_start = tbl_start + tbl_len
        val_start = key_start + key_len
        val_end = val_start + val_len

        tbl_bytes = data[tbl_start:key_start]
        key_bytes = data[key_start:val_start]
        val_bytes = data[val_start:val_end]
        expected_crc = CRC_STRUCT.unpack(data[val_end:total_size])[0]

        payload = data[:val_end]
        actual_crc = zlib.crc32(payload) & 0xFFFFFFFF

        if actual_crc != expected_crc:
            raise CorruptionError(f"WAL CRC32 mismatch: calculated {hex(actual_crc)}, expected {hex(expected_crc)}")

        return (
            cls(
                tx_id=tx_id,
                table_name=tbl_bytes.decode("utf-8"),
                record_type=record_type,
                key=key_bytes.decode("utf-8"),
                value=val_bytes.decode("utf-8"),
            ),
            total_size,
        )


class WriteAheadLog:
    """
    Write-Ahead Log persistence manager.
    """

    def __init__(self, wal_path: str | Path):
        self.wal_path = Path(wal_path).resolve()
        self.wal_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.wal_path.exists():
            self.wal_path.touch()

    def append(self, wal_record: WALRecord, fsync: bool = True) -> int:
        """Append WALRecord to disk file and fsync."""
        data = wal_record.serialize()
        with open(self.wal_path, "a+b") as f:
            f.seek(0, os.SEEK_END)
            offset = f.tell()
            f.write(data)
            f.flush()
            if fsync:
                os.fsync(f.fileno())
        return offset

    def read_all(self) -> Generator[tuple[int, WALRecord], None, None]:
        """Iterate through all valid WAL records in log file."""
        if not self.wal_path.exists():
            return

        file_size = self.wal_path.stat().st_size
        with open(self.wal_path, "rb") as f:
            while True:
                offset = f.tell()
                remaining = file_size - offset

                if remaining < WAL_HEADER_SIZE + CRC_SIZE:
                    break

                data = f.read()
                if not data:
                    break

                try:
                    record, bytes_read = WALRecord.deserialize_from_bytes(data)
                    f.seek(offset + bytes_read)
                    yield (offset, record)
                except (CorruptionError, StorageError):
                    # Handle partial/incomplete trailing WAL record cleanly
                    break

    def clear(self) -> None:
        """Truncate WAL log file after successful checkpointing."""
        with open(self.wal_path, "w+b") as f:
            f.truncate(0)
            f.flush()
            os.fsync(f.fileno())
