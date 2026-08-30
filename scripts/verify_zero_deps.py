#!/usr/bin/env python3
"""
Zero-Dependency Verification Script for MiniDB.

Scans all Python files in the repository for forbidden third-party imports
and ensures sqlite3 is NEVER imported.
"""

import ast
import sys
from pathlib import Path

# Explicit list of forbidden third-party modules and banned stdlib modules
FORBIDDEN_IMPORTS = {
    # Strictly Banned Standard Library Database Module
    "sqlite3": "FORBIDDEN: SQLite is strictly prohibited by hackathon prompt instructions.",

    # Popular Third-Party Frameworks & Packages
    "requests": "FORBIDDEN: Third-party HTTP library.",
    "httpx": "FORBIDDEN: Third-party HTTP library.",
    "flask": "FORBIDDEN: Third-party web framework.",
    "fastapi": "FORBIDDEN: Third-party web framework.",
    "django": "FORBIDDEN: Third-party web framework.",
    "sqlalchemy": "FORBIDDEN: Third-party ORM/database library.",
    "pandas": "FORBIDDEN: Third-party data analysis library.",
    "numpy": "FORBIDDEN: Third-party numerical library.",
    "pytest": "FORBIDDEN: Use unittest from standard library instead.",
    "click": "FORBIDDEN: Use argparse/cmd from standard library instead.",
    "typer": "FORBIDDEN: Use argparse/cmd from standard library instead.",
    "rich": "FORBIDDEN: Third-party terminal formatting library.",
    "sqlparse": "FORBIDDEN: Third-party SQL parser library.",
    "sqlglot": "FORBIDDEN: Third-party SQL parser library.",
    "redis": "FORBIDDEN: Third-party key-value client.",
    "psycopg2": "FORBIDDEN: Third-party database driver.",
    "pymongo": "FORBIDDEN: Third-party database driver.",
}

# Standard library module whitelist (known top-level stdlib modules)
STDLIB_MODULES = {
    "os", "sys", "pathlib", "struct", "io", "typing", "dataclasses",
    "collections", "re", "json", "argparse", "cmd", "unittest", "threading",
    "concurrent", "socket", "selectors", "hashlib", "hmac", "time",
    "datetime", "uuid", "logging", "tempfile", "shutil", "zlib", "ast",
    "importlib", "traceback", "signal", "math", "random", "enum", "functools",
    "itertools", "contextlib", "copy", "abc", "string", "site", "builtins"
}


def scan_file(file_path: Path) -> list[str]:
    """Scan a Python source file for forbidden import statements."""
    violations = []
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        return [f"Failed to parse {file_path}: {e}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod_base = alias.name.split(".")[0]
                if mod_base in FORBIDDEN_IMPORTS:
                    violations.append(
                        f"{file_path}:{node.lineno} -> Banned import '{alias.name}': {FORBIDDEN_IMPORTS[mod_base]}"
                    )
                elif mod_base not in STDLIB_MODULES and not is_local_module(mod_base, file_path):
                    violations.append(
                        f"{file_path}:{node.lineno} -> Potential third-party import '{alias.name}'"
                    )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod_base = node.module.split(".")[0]
                if mod_base in FORBIDDEN_IMPORTS:
                    violations.append(
                        f"{file_path}:{node.lineno} -> Banned import from '{node.module}': {FORBIDDEN_IMPORTS[mod_base]}"
                    )
                elif mod_base not in STDLIB_MODULES and not is_local_module(mod_base, file_path):
                    violations.append(
                        f"{file_path}:{node.lineno} -> Potential third-party import from '{node.module}'"
                    )

    return violations


def is_local_module(mod_name: str, current_file: Path) -> bool:
    """Check if imported module refers to local minidb packages/modules."""
    local_names = {"minidb", "src", "tests", "scripts", "examples"}
    return mod_name in local_names


def main():
    root = Path(__file__).resolve().parent.parent
    py_files = list(root.rglob("*.py"))

    # Exclude virtualenvs if any exist
    py_files = [f for f in py_files if "venv" not in f.parts and ".venv" not in f.parts]

    total_files = len(py_files)
    all_violations = []

    print("==================================================")
    print("      MINIDB ZERO-DEPENDENCY VERIFICATION         ")
    print("==================================================")
    print(f"Scanning {total_files} Python files in project...\n")

    for py_file in sorted(py_files):
        rel_path = py_file.relative_to(root)
        file_violations = scan_file(py_file)
        if file_violations:
            all_violations.extend(file_violations)

    if all_violations:
        print("❌ ZERO-DEPENDENCY AUDIT FAILED!")
        print("Violations found:")
        for v in all_violations:
            print(f"  - {v}")
        sys.exit(1)
    else:
        print("✅ ZERO-DEPENDENCY AUDIT PASSED!")
        print("  - Zero third-party packages detected.")
        print("  - sqlite3 module NOT used anywhere.")
        print("  - Python Standard Library compliance: 100%\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
