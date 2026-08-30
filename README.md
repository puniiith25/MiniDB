# MiniDB

> **A crash-safe, zero-dependency relational database engine built from scratch in Python.**

**Live Web Management Studio**: [https://mini-db.vercel.app](https://mini-db.vercel.app)

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

## Completed Features

- [x] Zero-dependency AST verifier (`scripts/verify_zero_deps.py`)
- [x] Custom binary record format (`struct`, CRC32 checksums)
- [x] Persistent append-only disk storage (`open`, `read`, `write`, `seek`, `tell`, `os.fsync`)
- [x] In-memory index with file offset lookup (`PrimaryIndex`)
- [x] Schema definition & validation (`INTEGER`, `TEXT`, `BOOLEAN`, `FLOAT`)
- [x] Hand-rolled SQL Lexer & Parser AST (`CREATE TABLE`, `INSERT`, `SELECT`, `DELETE`)
- [x] Query Executor with `WHERE` predicate filtering (`=`, `!=`, `>`, `<`, `>=`, `<=`)
- [x] Write-Ahead Logging (WAL) with `os.fsync()` durability
- [x] Automated crash recovery on restart (`RecoveryManager`)
- [x] ACID-style Transactions (`BEGIN`, `COMMIT`, `ROLLBACK`)
- [x] Thread-safe concurrency primitives (`threading.RLock`)
- [x] Client-Server TCP protocol over standard sockets (`socket`, `selectors`)
- [x] Interactive REPL CLI (`python3 -m minidb`)
- [x] Performance benchmark script (`scripts/benchmark.py`)
- [x] Reproducible 13-step demonstration (`scripts/demo.py`)

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

### Run TCP Server & CLI Shell
```bash
# Terminal 1: Start Database Server
make server

# Terminal 2: Start Interactive SQL Shell
make cli
# Or: PYTHONPATH=src python3 -m minidb
```

### Run Web Management Studio (Browser UI)
```bash
make web
# Open http://localhost:8080 in your browser
```

---

## Deployment Options

### 1. Vercel (Live Production Serverless Demo)
MiniDB is deployed serverless on Vercel with automatic REST API endpoints and Web Studio UI:
**Live Link**: [https://mini-db.vercel.app](https://mini-db.vercel.app)

### 2. Docker & Docker Compose
```bash
# Option A: Using docker-compose
docker-compose up -d

# Option B: Direct Docker run
docker build -t minidb .
docker run -d -p 8080:8080 -v minidb_data:/app/data --name minidb minidb
```
Open **`http://localhost:8080`** in your browser.

### 2. Cloud VPS / Render / Fly.io / Railway
Deploy MiniDB to any cloud provider by setting the startup command to:
```bash
PYTHONPATH=src python3 -m minidb.web --host 0.0.0.0 --port 8080 --data-dir ./data
```

---

## Hackathon Compliance

| Requirement | Compliance Status | Details |
| :--- | :--- | :--- |
| **Zero Third-Party Runtime Deps** | **PASS** | Verified via AST scanner (`scripts/verify_zero_deps.py`). |
| **No SQLite Usage** | **PASS** | `sqlite3` is prohibited and scanned in source/tests. |
| **Standard Library Only** | **PASS** | Uses `struct`, `os`, `socket`, `re`, `threading`, `unittest`, `zlib`. |
| **One-Command Execution** | **PASS** | Supported via `make demo` and `make test`. |

---

## Limitations & Honest Trade-offs

- **Educational Focus**: MiniDB is built for system understanding and hackathon verification, not multi-terabyte production data warehouses.
- **Transaction Model**: Page-level and table-level lock serialization rather than full multi-version concurrency control (MVCC).
- **SQL Subset**: Supports a documented subset of SQL (`CREATE TABLE`, `INSERT`, `SELECT ... WHERE`, `DELETE ... WHERE`, `BEGIN`, `COMMIT`, `ROLLBACK`).
