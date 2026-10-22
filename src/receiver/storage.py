"""Receiver storage is physically independent from authorization storage."""

from pathlib import Path

from services.storage import Store


class InboxStore(Store):
    """Own the receiver-only SQLite database and idempotent messages."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)
