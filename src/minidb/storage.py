"""
Persistent Append-Only Binary Storage Engine for MiniDB.

Provides durable low-level disk persistence using Python stdlib os, io, and pathlib.
Enforces fsync durability guarantees and offset tracking.
"""

import os
from pathlib import Path
from typing import Generator
from minidb.record import Record, RecordType, HEADER_SIZE, CRC_SIZE
from minidb.errors import StorageError, CorruptionError


class StorageEngine:
    """
    Append-only persistent binary storage engine for MiniDB tables.
    """

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path).resolve()
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.touch()

    def append_record(self, record: Record, fsync: bool = True) -> int:
        """
        Append a binary Record to the file.
        Returns the file offset (start byte position) of the written record.
        """
        data = record.serialize()
        with open(self.file_path, "a+b") as f:
            f.seek(0, os.SEEK_END)
            offset = f.tell()
            f.write(data)
            f.flush()
            if fsync:
                os.fsync(f.fileno())
        return offset

    def read_record_at(self, offset: int) -> Record:
        """
        Read and deserialize a single Record at the specified file offset.
        """
        with open(self.file_path, "rb") as f:
            f.seek(offset)
            header_and_data = f.read()
            if not header_and_data:
                raise StorageError(f"No data at offset {offset}")
            record, _ = Record.deserialize_from_bytes(header_and_data)
            return record

    def scan_all_records(self, stop_on_corruption: bool = False) -> Generator[tuple[int, Record], None, None]:
        """
        Scan all valid records sequentially from start of file to EOF.
        Yields tuples of (file_offset, Record).
        Safely handles incomplete/truncated records at EOF.
        """
        if not self.file_path.exists():
            return

        file_size = self.get_file_size()

        with open(self.file_path, "rb") as f:
            while True:
                offset = f.tell()
                remaining_bytes = file_size - offset

                if remaining_bytes == 0:
                    break

                if remaining_bytes < HEADER_SIZE + CRC_SIZE:
                    # Incomplete tail header at EOF
                    break

                # Read remaining contents from current offset
                data = f.read()
                if not data:
                    break

                try:
                    record, bytes_read = Record.deserialize_from_bytes(data)
                    f.seek(offset + bytes_read)
                    yield (offset, record)
                except CorruptionError as ce:
                    if stop_on_corruption or (offset + HEADER_SIZE + CRC_SIZE <= file_size):
                        # If corruption happens before the last incomplete record or stop_on_corruption is set
                        raise ce
                    break
                except StorageError as se:
                    # StorageError due to truncated record or oversized length
                    if offset + HEADER_SIZE + CRC_SIZE < file_size:
                        raise CorruptionError(f"Corrupted record length at offset {offset}: {se}")
                    # Otherwise clean EOF truncation
                    break

    def get_file_size(self) -> int:
        """Returns current file size in bytes."""
        if not self.file_path.exists():
            return 0
        return self.file_path.stat().st_size
