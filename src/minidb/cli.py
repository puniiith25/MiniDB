"""
Interactive REPL Command-Line Interface (CLI) for MiniDB.

Uses Python stdlib cmd module to provide an interactive SQL shell with ASCII tabular output.
"""

import cmd
import sys
import argparse
from typing import Any, Dict, List
from minidb.client import Client
from minidb.database import Database
from minidb.transaction import TransactionManager
from minidb.parser import Parser


def format_table_output(columns: List[str], rows: List[Dict[str, Any]]) -> str:
    """Format query result rows into an ASCII table string."""
    if not columns:
        return ""

    # Calculate column widths
    col_widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            val_str = str(row.get(col, "NULL"))
            col_widths[col] = max(col_widths[col], len(val_str))

    # Header line
    header = " | ".join(f"{col:<{col_widths[col]}}" for col in columns)
    separator = "-+-".join("-" * col_widths[col] for col in columns)

    # Data lines
    data_lines = []
    for row in rows:
        line = " | ".join(f"{str(row.get(col, 'NULL')):<{col_widths[col]}}" for col in columns)
        data_lines.append(line)

    lines = [header, separator] + data_lines
    return "\n".join(lines)


class MiniDBCli(cmd.Cmd):
    """
    Interactive REPL Shell for MiniDB.
    """

    prompt = "minidb> "
    intro = "Welcome to MiniDB Shell v0.1.0\nType '.help' or '.tables' for commands. Type '.quit' or 'exit' to exit."

    def __init__(self, client: Client):
        super().__init__()
        self.client = client

    def default(self, line: str) -> None:
        """Handle SQL statements or dot commands."""
        line = line.strip()
        if not line:
            return

        if line.lower() in ("exit", "quit", ".quit"):
            print("Goodbye!")
            sys.exit(0)

        if line.startswith("."):
            parts = line.split()
            cmd_name = parts[0]
            args = parts[1:]
            try:
                resp = self.client.execute_command(cmd_name, args)
                self._display_response(resp)
            except Exception as e:
                print(f"Error: {e}")
        else:
            # SQL statement
            try:
                resp = self.client.execute_sql(line)
                self._display_response(resp)
            except Exception as e:
                print(f"Error: {e}")

    def _display_response(self, resp: dict) -> None:
        if resp.get("status") == "ERROR":
            print(f"Error: {resp.get('error')}")
            return

        cols = resp.get("columns")
        rows = resp.get("rows")
        msg = resp.get("message")

        if cols and rows is not None:
            if rows:
                print(format_table_output(cols, rows))
                print(f"({len(rows)} row(s) returned)\n")
            else:
                print("Empty set (0 rows returned)\n")
        elif msg:
            print(f"OK: {msg}\n")


def main():
    parser = argparse.ArgumentParser(description="MiniDB Interactive REPL Shell")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9000, help="Server port (default: 9000)")
    args = parser.parse_args()

    client = Client(host=args.host, port=args.port)
    try:
        client.connect()
    except Exception as e:
        print(f"Could not connect to MiniDB Server at {args.host}:{args.port}: {e}")
        print("Please ensure 'make server' is running.")
        sys.exit(1)

    cli = MiniDBCli(client)
    try:
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
