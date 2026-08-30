"""
Initial environment & package structure tests for MiniDB.
"""

import sys
import unittest
from pathlib import Path

# Ensure src directory is in sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import minidb
from minidb.errors import DatabaseError, StorageError, CorruptionError


class TestMiniDBInit(unittest.TestCase):

    def test_version(self):
        self.assertEqual(minidb.__version__, "0.1.0")

    def test_python_version(self):
        """Verify Python 3 standard library environment."""
        self.assertGreaterEqual(sys.version_info[0], 3)
        self.assertGreaterEqual(sys.version_info[1], 14)

    def test_sqlite3_not_imported(self):
        """Verify sqlite3 module is not present in sys.modules."""
        self.assertNotIn("sqlite3", sys.modules)

    def test_custom_exceptions(self):
        err = CorruptionError("Corrupted byte stream")
        self.assertIsInstance(err, StorageError)
        self.assertIsInstance(err, DatabaseError)


if __name__ == "__main__":
    unittest.main()
