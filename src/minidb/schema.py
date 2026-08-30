"""
Schema Definition and Row Validation Engine for MiniDB.

Provides column data type definitions (INTEGER, TEXT, BOOLEAN, FLOAT)
and row payload schema validation and serialization.
"""

import json
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from minidb.errors import SchemaError


class DataType(str, Enum):
    INTEGER = "INTEGER"
    TEXT = "TEXT"
    BOOLEAN = "BOOLEAN"
    FLOAT = "FLOAT"


@dataclass
class Column:
    name: str
    data_type: DataType
    primary_key: bool = False
    nullable: bool = True

    def validate_value(self, val: Any) -> Any:
        """Validate and coerce value according to column data type."""
        if val is None:
            if not self.nullable and not self.primary_key:
                raise SchemaError(f"Column '{self.name}' cannot be NULL")
            return None

        if self.data_type == DataType.INTEGER:
            if isinstance(val, bool):
                raise SchemaError(f"Column '{self.name}' expects INTEGER, got BOOLEAN {val}")
            try:
                return int(val)
            except (ValueError, TypeError):
                raise SchemaError(f"Column '{self.name}' expects INTEGER, got '{val}' ({type(val).__name__})")

        elif self.data_type == DataType.FLOAT:
            if isinstance(val, bool):
                raise SchemaError(f"Column '{self.name}' expects FLOAT, got BOOLEAN {val}")
            try:
                return float(val)
            except (ValueError, TypeError):
                raise SchemaError(f"Column '{self.name}' expects FLOAT, got '{val}' ({type(val).__name__})")

        elif self.data_type == DataType.BOOLEAN:
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                if val.lower() in ("true", "1"):
                    return True
                if val.lower() in ("false", "0"):
                    return False
            if isinstance(val, int):
                return bool(val)
            raise SchemaError(f"Column '{self.name}' expects BOOLEAN, got '{val}' ({type(val).__name__})")

        elif self.data_type == DataType.TEXT:
            return str(val)

        raise SchemaError(f"Unsupported data type '{self.data_type}' for column '{self.name}'")


@dataclass
class TableSchema:
    name: str
    columns: List[Column] = field(default_factory=list)
    _column_map: Dict[str, Column] = field(init=False, default_factory=dict)
    _primary_key_column: Optional[Column] = field(init=False, default=None)

    def __post_init__(self):
        pk_cols = []
        for col in self.columns:
            self._column_map[col.name] = col
            if col.primary_key:
                pk_cols.append(col)

        if len(pk_cols) > 1:
            raise SchemaError(f"Table '{self.name}' cannot have multiple primary keys ({[c.name for c in pk_cols]})")
        if pk_cols:
            self._primary_key_column = pk_cols[0]
        elif self.columns:
            # Default to first column as primary key if none specified
            self._primary_key_column = self.columns[0]

    def get_column(self, col_name: str) -> Column:
        """Get column metadata by name."""
        if col_name not in self._column_map:
            raise SchemaError(f"Column '{col_name}' does not exist in table '{self.name}'")
        return self._column_map[col_name]

    def get_primary_key_column(self) -> Column:
        """Get primary key column for table."""
        if not self._primary_key_column:
            raise SchemaError(f"Table '{self.name}' has no defined columns or primary key")
        return self._primary_key_column

    def validate_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and coerce a row dictionary against the table schema.
        Returns validated row dictionary with all columns filled.
        """
        validated = {}
        for col in self.columns:
            val = row.get(col.name)
            validated[col.name] = col.validate_value(val)

        return validated

    def serialize_row(self, row: Dict[str, Any]) -> str:
        """Serialize a row dictionary to JSON payload string for binary record value."""
        validated_row = self.validate_row(row)
        return json.dumps(validated_row, separators=(",", ":"))

    def deserialize_row(self, json_str: str) -> Dict[str, Any]:
        """Deserialize JSON payload string into typed row dictionary."""
        try:
            raw_dict = json.loads(json_str)
            return self.validate_row(raw_dict)
        except Exception as e:
            raise SchemaError(f"Failed to deserialize row payload: {e}")
