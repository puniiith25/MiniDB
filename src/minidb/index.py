"""
In-Memory Indexing Engine for MiniDB.

Provides O(1) key to file-offset lookup mapping dictionary.
Supports automated index rebuilding from persistent binary storage logs,
properly tracking updates and tombstone deletions.
"""

from typing import Optional, Dict, Iterator
from minidb.storage import StorageEngine
from minidb.record import RecordType


class PrimaryIndex:
    """
    In-memory index mapping primary key strings to binary file byte offsets.
    """

    def __init__(self):
        self._index: Dict[str, int] = {}

    def put(self, key: str, offset: int) -> None:
        """Add or update primary key mapping to file offset."""
        self._index[key] = offset

    def get(self, key: str) -> Optional[int]:
        """
        Get binary file offset for key.
        Returns offset int if key exists, else None.
        """
        return self._index.get(key)

    def delete(self, key: str) -> bool:
        """Remove key from index (for tombstone deletion). Returns True if key existed."""
        if key in self._index:
            del self._index[key]
            return True
        return False

    def contains(self, key: str) -> bool:
        """Check if key exists in active index."""
        return key in self._index

    def clear(self) -> None:
        """Clear all in-memory index mappings."""
        self._index.clear()

    def count(self) -> int:
        """Return total number of indexed keys."""
        return len(self._index)

    def keys(self) -> Iterator[str]:
        """Iterate over all active indexed keys."""
        return iter(self._index.keys())

    def items(self) -> Iterator[tuple[str, int]]:
        """Iterate over (key, offset) pairs."""
        return iter(self._index.items())

    def rebuild_from_storage(self, storage: StorageEngine) -> int:
        """
        Rebuild index from scratch by scanning persistent storage sequentially.
        Handles INSERT, UPDATE, and DELETE (tombstones).
        Returns total valid active keys in index.
        """
        self.clear()
        for offset, record in storage.scan_all_records():
            if record.record_type in (RecordType.INSERT, RecordType.UPDATE):
                self._index[record.key] = offset
            elif record.record_type == RecordType.DELETE:
                self._index.pop(record.key, None)

        return len(self._index)
