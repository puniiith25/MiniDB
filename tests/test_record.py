"""
Unit tests for binary record format (src/minidb/record.py).
"""

import sys
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.record import Record, RecordType, HEADER_SIZE, CRC_SIZE
from minidb.errors import CorruptionError, StorageError


class TestRecordFormat(unittest.TestCase):

    def test_record_serialize_deserialize_roundtrip(self):
        records = [
            Record(RecordType.INSERT, "user1", '{"id": 1, "name": "Punith"}'),
            Record(RecordType.UPDATE, "user1", '{"id": 1, "name": "Punith Updated"}'),
            Record(RecordType.DELETE, "user1", ""),
            Record(RecordType.COMMIT, "tx101", ""),
            Record(RecordType.ROLLBACK, "tx102", ""),
        ]

        for rec in records:
            binary = rec.serialize()
            decoded_rec, bytes_read = Record.deserialize_from_bytes(binary)
            self.assertEqual(bytes_read, len(binary))
            self.assertEqual(decoded_rec.record_type, rec.record_type)
            self.assertEqual(decoded_rec.key, rec.key)
            self.assertEqual(decoded_rec.value, rec.value)

    def test_unicode_records(self):
        rec = Record(RecordType.INSERT, "user_café", "Punith Database Engine (nombres: José, Señor)")
        binary = rec.serialize()
        decoded, bytes_read = Record.deserialize_from_bytes(binary)
        self.assertEqual(decoded.key, "user_café")
        self.assertEqual(decoded.value, "Punith Database Engine (nombres: José, Señor)")

    def test_corrupted_magic_header(self):
        rec = Record(RecordType.INSERT, "key1", "val1")
        binary = bytearray(rec.serialize())
        # Mutate magic byte
        binary[0] = 0xFF
        with self.assertRaises(CorruptionError) as ctx:
            Record.deserialize_from_bytes(bytes(binary))
        self.assertIn("Invalid magic header", str(ctx.exception))

    def test_corrupted_crc32(self):
        rec = Record(RecordType.INSERT, "key1", "val1")
        binary = bytearray(rec.serialize())
        # Mutate last byte (CRC32)
        binary[-1] ^= 0xFF
        with self.assertRaises(CorruptionError) as ctx:
            Record.deserialize_from_bytes(bytes(binary))
        self.assertIn("CRC32 mismatch", str(ctx.exception))

    def test_truncated_header(self):
        with self.assertRaises(StorageError):
            Record.deserialize_from_bytes(b"MB123")

    def test_truncated_body(self):
        rec = Record(RecordType.INSERT, "long_key", "long_value_body")
        binary = rec.serialize()
        # Truncate 5 bytes from end
        truncated = binary[:-5]
        with self.assertRaises(StorageError):
            Record.deserialize_from_bytes(truncated)

    def test_invalid_record_type(self):
        rec = Record(RecordType.INSERT, "key1", "val1")
        binary = bytearray(rec.serialize())
        # Set record type byte to 99
        binary[2] = 99
        with self.assertRaises(CorruptionError):
            Record.deserialize_from_bytes(bytes(binary))


if __name__ == "__main__":
    unittest.main()
