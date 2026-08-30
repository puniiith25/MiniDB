"""
Zero-Dependency HTTP Server & REST API Bridge for MiniDB Web Management Studio.

Serves the static Web Studio single-page application and handles REST API endpoints:
- POST /api/query: Execute SQL queries and return JSON result with execution metrics.
- GET  /api/tables: List all database tables and row counts.
- GET  /api/schema: Get column schema metadata for a table.
- GET  /api/stats: Get overall database engine statistics.
"""

import json
import time
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict

from minidb.database import Database
from minidb.transaction import TransactionManager
from minidb.parser import Parser
from minidb.errors import DatabaseError, ParseError, TransactionError, SchemaError

WEB_DIR = Path(__file__).resolve().parent.parent.parent / "web"


class MiniDBHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for MiniDB Web Management Studio."""

    db: Database = None  # Class-level reference initialized on server startup
    tm: TransactionManager = None

    def log_message(self, format: str, *args: Any) -> None:
        """Custom clean HTTP access log format."""
        print(f"[HTTP] {self.address_string()} - {format % args}")

    def _send_json(self, status_code: int, data: Dict[str, Any]) -> None:
        """Helper to send JSON API responses with CORS headers."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        """Handle HTTP GET requests for static files and REST API endpoints."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # API Endpoints
        if path == "/api/tables":
            self._handle_get_tables()
        elif path == "/api/schema":
            table_name = query_params.get("table", [""])[0]
            self._handle_get_schema(table_name)
        elif path == "/api/stats":
            self._handle_get_stats()

        # Static File Serving
        elif path == "/" or path == "/index.html":
            self._serve_static_file(WEB_DIR / "index.html", "text/html; charset=utf-8")
        else:
            # Try serving from WEB_DIR
            safe_file = (WEB_DIR / path.lstrip("/")).resolve()
            if safe_file.is_relative_to(WEB_DIR) and safe_file.exists() and safe_file.is_file():
                mime = "text/html"
                if safe_file.suffix == ".css":
                    mime = "text/css"
                elif safe_file.suffix == ".js":
                    mime = "text/javascript"
                elif safe_file.suffix == ".json":
                    mime = "application/json"
                self._serve_static_file(safe_file, mime)
            else:
                self._send_json(404, {"status": "ERROR", "error": f"Path '{path}' not found"})

    def do_POST(self) -> None:
        """Handle HTTP POST requests (e.g. SQL query execution)."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/api/query":
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)
            try:
                payload = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                self._send_json(400, {"status": "ERROR", "error": f"Invalid JSON payload: {e}"})
                return

            sql = payload.get("sql", "").strip()
            if not sql:
                self._send_json(400, {"status": "ERROR", "error": "Missing 'sql' query parameter"})
                return

            self._execute_sql_query(sql)
        else:
            self._send_json(404, {"status": "ERROR", "error": f"POST endpoint '{path}' not found"})

    def _handle_get_tables(self) -> None:
        try:
            tables = self.db.list_tables()
            table_info = []
            for t_name in tables:
                table_obj = self.db.get_table(t_name)
                # Count valid indexed keys or scan count
                row_count = table_obj.index.count()
                table_info.append({
                    "table_name": t_name,
                    "row_count": row_count,
                    "columns_count": len(table_obj.schema.columns),
                })
            self._send_json(200, {"status": "OK", "tables": table_info})
        except Exception as e:
            self._send_json(500, {"status": "ERROR", "error": str(e)})

    def _handle_get_schema(self, table_name: str) -> None:
        if not table_name:
            self._send_json(400, {"status": "ERROR", "error": "Query parameter 'table' is required"})
            return

        try:
            table = self.db.get_table(table_name)
            cols = [
                {
                    "name": c.name,
                    "type": c.data_type.value,
                    "primary_key": c.primary_key,
                    "nullable": c.nullable,
                }
                for c in table.schema.columns
            ]
            self._send_json(200, {"status": "OK", "table_name": table_name, "columns": cols})
        except Exception as e:
            self._send_json(404, {"status": "ERROR", "error": str(e)})

    def _handle_get_stats(self) -> None:
        try:
            tables = self.db.list_tables()
            total_rows = 0
            for t_name in tables:
                total_rows += self.db.get_table(t_name).index.count()

            self._send_json(200, {
                "status": "OK",
                "tables_count": len(tables),
                "total_rows": total_rows,
                "data_dir": str(self.db.data_dir),
            })
        except Exception as e:
            self._send_json(500, {"status": "ERROR", "error": str(e)})

    def _execute_sql_query(self, sql: str) -> None:
        t0 = time.perf_counter()
        try:
            ast = Parser(sql).parse()
            res = self.tm.execute_sql_query(ast)
            execution_time_ms = round((time.perf_counter() - t0) * 1000, 3)

            self._send_json(200, {
                "status": "OK",
                "columns": res.columns,
                "rows": res.rows,
                "affected_rows": res.affected_rows,
                "message": res.message,
                "execution_time_ms": execution_time_ms,
            })
        except (DatabaseError, ParseError, TransactionError, SchemaError) as e:
            execution_time_ms = round((time.perf_counter() - t0) * 1000, 3)
            self._send_json(400, {
                "status": "ERROR",
                "error": str(e),
                "execution_time_ms": execution_time_ms,
            })
        except Exception as e:
            execution_time_ms = round((time.perf_counter() - t0) * 1000, 3)
            self._send_json(500, {
                "status": "ERROR",
                "error": f"Internal Database Error: {e}",
                "execution_time_ms": execution_time_ms,
            })

    def _serve_static_file(self, file_path: Path, content_type: str) -> None:
        try:
            content = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._send_json(404, {"status": "ERROR", "error": f"File read error: {e}"})


def run_web_server(data_dir: str = "./data", host: str = "127.0.0.1", port: int = 8080) -> None:
    data_path = Path(data_dir).resolve()
    data_path.mkdir(parents=True, exist_ok=True)

    db = Database(data_path)
    tm = TransactionManager(db)

    MiniDBHTTPRequestHandler.db = db
    MiniDBHTTPRequestHandler.tm = tm

    server = HTTPServer((host, port), MiniDBHTTPRequestHandler)
    print(f"MiniDB Web Management Studio running at http://{host}:{port}")
    print(f"Data Directory: {data_path}")
    print("Press Ctrl+C to stop server.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down MiniDB Web Server.")
        server.server_close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MiniDB Web Management Studio Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host IP (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    parser.add_argument("--data-dir", default="./data", help="Database data directory")

    args = parser.parse_args()
    run_web_server(data_dir=args.data_dir, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
