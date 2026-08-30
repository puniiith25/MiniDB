"""
Thread-Safe Concurrency Lock Manager for MiniDB.

Uses Python stdlib threading primitives (RLock) to ensure safe concurrent table operations,
index updates, and WAL file synchronization.
"""

import threading
from typing import Dict
from pathlib import Path


class TableLockManager:
    """
    Manages per-table re-entrant read/write locks (RLock).
    """

    def __init__(self):
        self._global_lock = threading.RLock()
        self._table_locks: Dict[str, threading.RLock] = {}

    def get_table_lock(self, table_name: str) -> threading.RLock:
        """Get or create RLock for specific table."""
        with self._global_lock:
            if table_name not in self._table_locks:
                self._table_locks[table_name] = threading.RLock()
            return self._table_locks[table_name]


class DatabaseLockManager:
    """
    Database-wide lock manager synchronizing global operations, WAL access, and table locks.
    """

    def __init__(self):
        self.wal_lock = threading.RLock()
        self.catalog_lock = threading.RLock()
        self.table_locks = TableLockManager()
