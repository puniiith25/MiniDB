"""
Vercel Serverless Function Entrypoint for MiniDB.

Uses Vercel Python runtime with BaseHTTPRequestHandler to serve REST API requests.
Uses /tmp/data for serverless disk storage.
"""

import sys
from pathlib import Path

# Add src/ directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from minidb.database import Database
from minidb.transaction import TransactionManager
from minidb.web import MiniDBHTTPRequestHandler

# Initialize database instance in Vercel's ephemeral /tmp storage
data_dir = Path("/tmp/minidb_data")
data_dir.mkdir(parents=True, exist_ok=True)

db = Database(data_dir)
tm = TransactionManager(db)

MiniDBHTTPRequestHandler.db = db
MiniDBHTTPRequestHandler.tm = tm


class handler(MiniDBHTTPRequestHandler):
    """Vercel Python Serverless Handler subclassing BaseHTTPRequestHandler."""
    pass
