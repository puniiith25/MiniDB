# MiniDB

> **A crash-safe, zero-dependency relational database engine built from scratch in Python.**

MiniDB is built for the **Zero Dependency Hackathon** (Track D: Data & Storage). It demonstrates deep database internals—persistent binary disk storage, in-memory offset indexing, write-ahead logging (WAL), crash recovery, SQL-like query parsing & execution, transactions, concurrency, and a client-server TCP architecture—using **only Python's standard library**.

---

## Zero Dependency Guarantee

- **Zero Third-Party Packages**: No `pip` dependencies.
- **SQLite Ban**: `sqlite3` is **NOT USED** anywhere in storage, tests, or internals.
- **Stdlib Only**: Runs natively on Python 3.14+ standard library.

For full architectural substitutions, see [STDLIB.md](STDLIB.md) and [deps-proof.txt](deps-proof.txt).

---

## Architecture Overview

```
CLI / REPL Shell        TCP Client
       │                     │
       └──────────┬──────────┘
                  │ (TCP Socket Protocol)
                  v
         TCP Server / Protocol
                  │
                  v
              SQL Lexer
                  │
                  v
             SQL Parser
                  │
                  v
           Query Executor
                  │
                  v
         Transaction Manager
                  │
         ┌────────┴────────┐
         │                 │
         v                 v
 Write-Ahead Log        Storage Engine
      (WAL)                │
                           ├──────────> In-Memory Index
                           v
                  Binary File Store (.db)
```

### Crash Recovery Pipeline

```
Database Startup ──> Read WAL ──> Validate Records ──> Replay Operations ──> Rebuild Indexes ──> Ready
```

---

## Features (Progressive Roadmap)

- [x] Zero-dependency audit harness
- [ ] Custom binary record serialization (`struct`)
- [ ] Persistent append-only disk storage
- [ ] In-memory index with file offset lookup
- [ ] Schema definition & validation (`INTEGER`, `TEXT`, `BOOLEAN`)
- [ ] SQL Lexer & Parser AST
- [ ] Query Executor (`CREATE TABLE`, `INSERT`, `SELECT`, `DELETE`)
- [ ] `WHERE` filtering engine (`=`, `!=`, `>`, `<`, `>=`, `<=`)
- [ ] Write-Ahead Logging (WAL) with `os.fsync()` durability
- [ ] Automated crash recovery on restart
- [ ] ACID-style Transactions (`BEGIN`, `COMMIT`, `ROLLBACK`)
- [ ] Thread-safe concurrency primitives
- [ ] Client-Server TCP protocol over standard sockets
- [ ] Interactive REPL CLI

---

## Quick Start

### Prerequisites
- Python 3.14+ (Target standard library environment)
- `make`

### Installation
No installation needed! Zero third-party dependencies.

```bash
git clone https://github.com/user/MiniDB.git
cd MiniDB
```

### Run Zero-Dependency Verification
```bash
make verify
```

### Run Tests
```bash
make test
```

### Run Demonstration
```bash
make demo
```

### Run Performance Benchmarks
```bash
make benchmark
```

---

## Hackathon Compliance

| Requirement | Compliance Status | Details |
| :--- | :--- | :--- |
| **Zero Third-Party Runtime Deps** | **PASS** | Verified via AST scanner (`scripts/verify_zero_deps.py`). |
| **No SQLite Usage** | **PASS** | `sqlite3` is prohibited and scanned in source/tests. |
| **Standard Library Only** | **PASS** | Uses `struct`, `os`, `socket`, `selectors`, `re`, `threading`, `unittest`. |
| **One-Command Execution** | **PASS** | Supported via `make demo` and `make test`. |

---

## Limitations & Honest Trade-offs

- **Educational Focus**: MiniDB is built for system understanding and hackathon verification, not multi-terabyte production data warehouses.
- **Transaction Model**: Page-level and table-level lock serialization rather than full multi-version concurrency control (MVCC).
- **SQL Subset**: Supports a documented subset of SQL (`CREATE TABLE`, `INSERT`, `SELECT ... WHERE`, `DELETE ... WHERE`).
