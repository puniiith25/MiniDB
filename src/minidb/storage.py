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
        if file_size == 0:
            return

        with open(self.file_path, "rb") as f:
            offset = 0
            buf = b""
            chunk_size = 64 * 1024

            while True:
                more = f.read(chunk_size)
                if more:
                    buf += more

                if not buf:
                    break

                progress = False
                while True:
                    if len(buf) < HEADER_SIZE + CRC_SIZE:
                        break

                    try:
                        record, bytes_read = Record.deserialize_from_bytes(buf)
                        yield (offset, record)
                        offset += bytes_read
                        buf = buf[bytes_read:]
                        progress = True
                    except CorruptionError as ce:
                        if stop_on_corruption or (offset + HEADER_SIZE + CRC_SIZE <= file_size):
                            raise ce
                        buf = b""
                        break
                    except StorageError as se:
                        if stop_on_corruption or (offset + HEADER_SIZE + CRC_SIZE < file_size):
                            raise CorruptionError(f"Corrupted record at offset {offset}: {se}")
                        break

                if not more and not progress:
                    break

    def get_file_size(self) -> int:
        """Returns current file size in bytes."""
        if not self.file_path.exists():
            return 0
        return self.file_path.stat().st_size
