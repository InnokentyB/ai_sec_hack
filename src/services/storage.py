"""Short-lived SQLite connections and atomic aggregate/event transactions."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from core.canonical import Json


class Store:
    """Persist one synthetic case, grants, attempts and its append-only ledger."""

    def __init__(self, path: Path) -> None:
        self.path = path
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS objects (
                    kind TEXT NOT NULL,
                    id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    PRIMARY KEY(kind, id)
                );
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY,
                    data TEXT NOT NULL
                );
                """
            )
        finally:
            db.close()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Commit or rollback a bounded transaction and always close its connection."""
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        try:
            db.execute("PRAGMA busy_timeout=10000")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def get(db: sqlite3.Connection, kind: str, identifier: str) -> Json | None:
        """Load an object inside the caller's transaction."""
        row = db.execute(
            "SELECT data FROM objects WHERE kind=? AND id=?", (kind, identifier)
        ).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def put(db: sqlite3.Connection, kind: str, identifier: str, data: Json) -> None:
        """Persist aggregate state within the same transaction as its ledger event."""
        db.execute(
            "INSERT INTO objects VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
            (kind, identifier, json.dumps(data)),
        )

    @staticmethod
    def all(db: sqlite3.Connection, kind: str) -> list[Json]:
        """Read all objects of one kind in insertion order."""
        return [
            json.loads(row[0])
            for row in db.execute("SELECT data FROM objects WHERE kind=? ORDER BY rowid", (kind,))
        ]

    @staticmethod
    def events(db: sqlite3.Connection) -> list[Json]:
        """Read the complete ordered ledger without mutating it."""
        return [
            json.loads(row[0]) for row in db.execute("SELECT data FROM events ORDER BY sequence")
        ]
