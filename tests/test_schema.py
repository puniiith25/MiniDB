"""
Unit tests for schema engine (src/minidb/schema.py).
"""

import sys
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.schema import TableSchema, Column, DataType
from minidb.errors import SchemaError


class TestSchemaEngine(unittest.TestCase):

    def setUp(self):
        self.schema = TableSchema(
            name="users",
            columns=[
                Column("id", DataType.INTEGER, primary_key=True),
                Column("name", DataType.TEXT, nullable=False),
                Column("age", DataType.INTEGER, nullable=True),
                Column("is_active", DataType.BOOLEAN, nullable=True),
                Column("score", DataType.FLOAT, nullable=True),
            ],
        )

    def test_schema_primary_key(self):
        pk = self.schema.get_primary_key_column()
        self.assertEqual(pk.name, "id")
        self.assertEqual(pk.data_type, DataType.INTEGER)

    def test_row_validation_success(self):
        input_row = {
            "id": "1",  # string coerced to int 1
            "name": "Punith",
            "age": 22,
            "is_active": "true",  # string coerced to bool True
            "score": "98.5",  # string coerced to float 98.5
        }
        validated = self.schema.validate_row(input_row)

        self.assertEqual(validated["id"], 1)
        self.assertEqual(validated["name"], "Punith")
        self.assertEqual(validated["age"], 22)
        self.assertEqual(validated["is_active"], True)
        self.assertEqual(validated["score"], 98.5)

    def test_invalid_type_raises_error(self):
        invalid_row = {
            "id": 1,
            "name": "Punith",
            "age": "invalid_integer_string",
        }
        with self.assertRaises(SchemaError):
            self.schema.validate_row(invalid_row)

    def test_non_nullable_constraint(self):
        invalid_row = {
            "id": 1,
            "name": None,  # name cannot be null
        }
        with self.assertRaises(SchemaError):
            self.schema.validate_row(invalid_row)

    def test_serialize_deserialize_row(self):
        input_row = {"id": 10, "name": "Rahul", "age": 25, "is_active": True, "score": 85.0}
        serialized = self.schema.serialize_row(input_row)
        deserialized = self.schema.deserialize_row(serialized)

        self.assertEqual(deserialized, input_row)


if __name__ == "__main__":
    unittest.main()
