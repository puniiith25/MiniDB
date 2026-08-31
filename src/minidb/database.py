"""
Database Engine Catalog and Table Storage Manager for MiniDB.

Manages multiple table storage files, schemas, and primary indexes.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from minidb.schema import TableSchema, Column, DataType
from minidb.storage import StorageEngine
from minidb.index import PrimaryIndex
from minidb.record import Record, RecordType
from minidb.errors import DatabaseError, SchemaError


class Table:
    """
    Represents a single database table containing schema, disk storage, and primary index.
    """

    def __init__(self, db_dir: Path, schema: TableSchema):
        self.db_dir = db_dir
        self.schema = schema
        self.db_file = db_dir / f"{schema.name}.db"
        self.schema_file = db_dir / f"{schema.name}.schema.json"

        self.storage = StorageEngine(self.db_file)
        self.index = PrimaryIndex()

        # Save schema to disk
        self._save_schema()
        # Rebuild index from disk storage
        self.index.rebuild_from_storage(self.storage)

    def _save_schema(self) -> None:
        """Persist table schema definition to disk."""
        data = {
            "name": self.schema.name,
            "columns": [
                {
                    "name": col.name,
                    "data_type": col.data_type.value,
                    "primary_key": col.primary_key,
                    "nullable": col.nullable,
                }
                for col in self.schema.columns
            ],
        }
        with open(self.schema_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_from_dir(cls, db_dir: Path, table_name: str) -> "Table":
        """Load an existing table and schema from database directory."""
        schema_file = db_dir / f"{table_name}.schema.json"
        if not schema_file.exists():
            raise DatabaseError(f"Table '{table_name}' does not exist")

        with open(schema_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        cols = [
            Column(
                name=c["name"],
                data_type=DataType(c["data_type"]),
                primary_key=c.get("primary_key", False),
                nullable=c.get("nullable", True),
            )
            for c in data["columns"]
        ]
        schema = TableSchema(name=data["name"], columns=cols)
        return cls(db_dir, schema)


class Database:
    """
    Main MiniDB Database engine class.
    Manages catalog of tables and data directory persistence.
    """

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tables: Dict[str, Table] = {}
        self._load_existing_tables()

    def _load_existing_tables(self) -> None:
        """Discover and load all existing table schemas in data directory."""
        for schema_file in self.data_dir.glob("*.schema.json"):
            table_name = schema_file.name.replace(".schema.json", "")
            try:
                table = Table.load_from_dir(self.data_dir, table_name)
                self.tables[table_name] = table
            except Exception as e:
                # Log schema loading warning
                pass

    def create_table(self, schema: TableSchema, if_not_exists: bool = False) -> Table:
        """Create a new database table."""
        if schema.name in self.tables:
            if if_not_exists:
                return self.tables[schema.name]
            raise DatabaseError(f"Table '{schema.name}' already exists")

        table = Table(self.data_dir, schema)
        self.tables[schema.name] = table
        return table

    def drop_table(self, table_name: str, if_exists: bool = False) -> bool:
        """Drop a database table and remove its storage files."""
        if table_name not in self.tables:
            if if_exists:
                return False
            raise DatabaseError(f"Table '{table_name}' does not exist")

        self.tables.pop(table_name, None)

        db_file = self.data_dir / f"{table_name}.db"
        schema_file = self.data_dir / f"{table_name}.schema.json"

        if db_file.exists():
            db_file.unlink()
        if schema_file.exists():
            schema_file.unlink()

        return True

    def get_table(self, table_name: str) -> Table:
        """Retrieve table instance by name."""
        if table_name not in self.tables:
            raise DatabaseError(f"Table '{table_name}' does not exist")
        return self.tables[table_name]

    def has_table(self, table_name: str) -> bool:
        """Check if table exists."""
        return table_name in self.tables

    def list_tables(self) -> List[str]:
        """List all available table names."""
        return sorted(list(self.tables.keys()))
