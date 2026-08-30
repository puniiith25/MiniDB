"""
Crash Recovery Engine for MiniDB.

Replays committed operations from Write-Ahead Log (WAL) on database startup,
discarding incomplete/uncommitted transactions to enforce atomicity and durability.
"""

from typing import Dict, List, Set
from minidb.database import Database
from minidb.wal import WriteAheadLog, WALRecord
from minidb.record import Record, RecordType


class RecoveryManager:
    """
    Handles WAL log analysis, transaction replay, and index rebuilding on startup.
    """

    def __init__(self, db: Database, wal: WriteAheadLog):
        self.db = db
        self.wal = wal

    def recover(self) -> int:
        """
        Perform complete crash recovery sequence.
        Returns total number of replayed log records.
        """
        wal_records = list(self.wal.read_all())
        if not wal_records:
            # Rebuild indexes for all existing tables
            for name, table in self.db.tables.items():
                table.index.rebuild_from_storage(table.storage)
            return 0

        # Phase 1: Analysis Pass
        committed_tx_ids: Set[int] = {0}  # tx_id 0 represents non-transactional autocommit
        rolledback_tx_ids: Set[int] = set()
        tx_ops: Dict[int, List[WALRecord]] = {}

        for offset, wal_rec in wal_records:
            tx_id = wal_rec.tx_id
            if tx_id not in tx_ops:
                tx_ops[tx_id] = []

            if wal_rec.record_type == RecordType.COMMIT:
                committed_tx_ids.add(tx_id)
            elif wal_rec.record_type == RecordType.ROLLBACK:
                rolledback_tx_ids.add(tx_id)
            else:
                tx_ops[tx_id].append(wal_rec)

        # Phase 2: Redo / Replay Pass for Committed Transactions
        replayed_count = 0
        for tx_id, ops in tx_ops.items():
            if tx_id in committed_tx_ids and tx_id not in rolledback_tx_ids:
                for wal_rec in ops:
                    if self.db.has_table(wal_rec.table_name):
                        table = self.db.get_table(wal_rec.table_name)
                        record = Record(
                            record_type=wal_rec.record_type,
                            key=wal_rec.key,
                            value=wal_rec.value,
                        )
                        table.storage.append_record(record, fsync=True)
                        replayed_count += 1

        # Phase 3: Rebuild Primary Indexes for all tables
        for name, table in self.db.tables.items():
            table.index.rebuild_from_storage(table.storage)

        # Phase 4: Clear checkpointed WAL
        self.wal.clear()

        return replayed_count
