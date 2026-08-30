"""
Custom Exceptions for MiniDB.
"""


class DatabaseError(Exception):
    """Base exception for all MiniDB database errors."""

    pass


class StorageError(DatabaseError):
    """Raised when storage I/O or binary encoding operations fail."""

    pass


class CorruptionError(StorageError):
    """Raised when binary record checksum or magic byte verification fails."""

    pass


class SchemaError(DatabaseError):
    """Raised when record data violates table schema definitions."""

    pass


class ParseError(DatabaseError):
    """Raised when SQL tokenization or syntax parsing fails."""

    pass


class TransactionError(DatabaseError):
    """Raised when transaction management operations fail (e.g. invalid state)."""

    pass


class ProtocolError(DatabaseError):
    """Raised when client-server socket protocol messages are malformed."""

    pass
