# Standard Library Log & Substitutions (STDLIB.md)

Project: **MiniDB**  
Tagline: A crash-safe, zero-dependency relational database engine built from scratch in Python.  
Track: Track D — Data & Storage  
Target Language & Version: Python 3.14.3 (Standard Library Only)  

---

## Zero-Dependency Guarantee

MiniDB uses **zero** third-party Python packages, zero PyPI dependencies, zero external database binaries, and **zero `sqlite3` standard-library calls**. All storage, record binary serialization, indexing, SQL lexing/parsing, query execution, write-ahead logging (WAL), crash recovery, transaction management, concurrency synchronization, and network communication are implemented directly using Python's standard library.

---

## Standard-Library Substitutions

| Problem Domain | Typical Third-Party / External Choice | Standard-Library Solution Used | Rationale |
| :--- | :--- | :--- | :--- |
| **Database Storage Engine** | SQLite, PostgreSQL, LevelDB | `struct`, `os`, `pathlib`, `io` | Custom binary append-only storage engine with low-level `os.fsync()` durability guarantees. |
| **SQL Parser & AST** | sqlglot, sqlparse, PLY | `re`, `dataclasses` | Hand-rolled SQL lexer and recursive-descent query parser producing strongly typed AST dataclasses. |
| **In-Memory Indexing** | Redis, BTree packages | `dict`, `dataclasses` | Hash-based file offset index rebuilt deterministically on database startup. |
| **Write-Ahead Log (WAL)** | RocksDB WAL, SQLite WAL | `struct`, `os.fsync` | Binary write-ahead log for atomicity and crash recovery prior to table file mutation. |
| **Concurrency Control** | Redis lock, external lock servers | `threading.Lock`, `threading.RLock` | Thread-safe page/table lock synchronization primitives. |
| **TCP Database Server** | FastAPI, Flask, Asyncio/Uvicorn | `socket`, `selectors` | Low-level non-blocking TCP socket server with custom binary message protocol. |
| **Database Client CLI** | click, typer, prompt_toolkit | `argparse`, `cmd` | Standard library interactive REPL CLI with pretty-printed tabular outputs. |
| **Testing Harness** | pytest | `unittest` | Standard library unit and integration test suite with corruption and failure injection testing. |
| **Benchmarking** | pytest-benchmark, locust | `time.perf_counter` | Nanosecond-resolution CPU / wall-clock time measurement for indexed lookup vs full file scan comparisons. |
| **Dependency Audit** | pip-audit, safety | `ast`, `importlib.util` | Custom AST scanner (`scripts/verify_zero_deps.py`) checking source code against forbidden third-party imports and `sqlite3`. |

---

## Detailed Standard-Library Module Breakdown

1. **`struct`**: Encodes and decodes primitive types (`INTEGER`, `TEXT`, `BOOLEAN`, `FLOAT`) and headers into compact binary disk records using fixed endianness (`>`).
2. **`os` & `pathlib`**: File creation, path manipulation, file descriptor management, and `os.fsync()` for guaranteed disk persistence.
3. **`io`**: Binary stream buffers for in-memory serialization and log replaying.
4. **`threading` & `concurrent.futures`**: Concurrency locking (`Lock`, `RLock`) and thread pool execution for multi-client query isolation.
5. **`socket` & `selectors`**: Multiplexed I/O database TCP server (`127.0.0.1:9000`) and TCP network client.
6. **`re`**: Regular expression token matching in the SQL lexer.
7. **`dataclasses`**: AST node representations and schema definitions with zero boilerplate.
8. **`argparse` & `cmd`**: Command-line flag parsing and interactive SQL shell (`cmd.Cmd`).
9. **`unittest`**: Comprehensive test suite covering binary encoding, WAL recovery, concurrency, SQL parser, and TCP protocol.
10. **`time` & `datetime`**: High-precision execution benchmarking via `time.perf_counter()`.
11. **`hashlib` & `zlib`**: Checksum validation for record integrity and corruption detection.

---

## Custom Binary Storage Format Layout

Each record on disk is stored in a custom binary layout managed via `struct`:

```
┌─────────────────┬─────────────────┬─────────────────┬───────────────────┐
│ Magic (2B)      │ Type (1B)       │ Key Length (2B) │ Value Length (4B) │
├─────────────────┴─────────────────┴─────────────────┴───────────────────┤
│ Key bytes (UTF-8 string or binary ID)                                   │
├─────────────────────────────────────────────────────────────────────────┤
│ Value payload bytes (Schema-validated column tuple)                     │
├─────────────────────────────────────────────────────────────────────────┤
│ Checksum / CRC32 (4B)                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

- **Magic Header**: `0x4D42` ("MB" for MiniDB)
- **Record Type**: `0x01` (INSERT), `0x02` (UPDATE), `0x03` (DELETE / Tombstone), `0x04` (COMMIT), `0x05` (ROLLBACK)
- **Endianness**: Big-endian (`>`) for network and cross-platform compatibility
- **Corruption Behavior**: Mismatched CRC32 or invalid magic headers trigger `CorruptionError` and trigger automated WAL recovery.
