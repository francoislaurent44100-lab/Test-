"""Load normalized DPE rows into a local SQLite database.

The ADEME schema is wide (100+ columns) and occasionally grows, so the
table is built incrementally: any new key seen in a row gets an
`ALTER TABLE ... ADD COLUMN` before the row is upserted. All columns are
untyped (SQLite columns are dynamically typed regardless of declaration).
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Iterable

from .transform import to_snake_case

_RESERVED_META_COLUMNS = ("_source_dataset", "_raw_json")


class SqliteLoader:
    def __init__(self, db_path: str, table: str, primary_key: str) -> None:
        self.db_path = db_path
        self.table = table
        self.primary_key = to_snake_case(primary_key)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._known_columns: set[str] = set()
        self._ensure_table()

    def _ensure_table(self) -> None:
        cur = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (self.table,)
        )
        if cur.fetchone() is None:
            self.conn.execute(
                f'CREATE TABLE "{self.table}" ("{self.primary_key}" TEXT PRIMARY KEY, '
                f'"_source_dataset" TEXT, "_raw_json" TEXT)'
            )
            self.conn.commit()
        self._known_columns = self._existing_columns()

    def _existing_columns(self) -> set[str]:
        cur = self.conn.execute(f'PRAGMA table_info("{self.table}")')
        return {row[1] for row in cur.fetchall()}

    def _add_missing_columns(self, keys: Iterable[str]) -> None:
        for key in keys:
            if key in self._known_columns:
                continue
            self.conn.execute(f'ALTER TABLE "{self.table}" ADD COLUMN "{key}" TEXT')
            self._known_columns.add(key)

    def upsert_many(self, rows: Iterable[dict[str, Any]], source_dataset: str, batch_size: int = 500) -> int:
        count = 0
        batch: list[dict[str, Any]] = []
        for row in rows:
            batch.append(row)
            count += 1
            if len(batch) >= batch_size:
                self._flush(batch, source_dataset)
                batch = []
        if batch:
            self._flush(batch, source_dataset)
        return count

    def _flush(self, batch: list[dict[str, Any]], source_dataset: str) -> None:
        all_keys: set[str] = set()
        for row in batch:
            all_keys.update(row.keys())
        self._add_missing_columns(all_keys)

        columns = [self.primary_key] + sorted(all_keys - {self.primary_key}) + list(_RESERVED_META_COLUMNS)
        placeholders = ", ".join("?" for _ in columns)
        col_list = ", ".join(f'"{c}"' for c in columns)
        sql = f'INSERT OR REPLACE INTO "{self.table}" ({col_list}) VALUES ({placeholders})'

        values = []
        for row in batch:
            if self.primary_key not in row:
                continue
            record = [row.get(self.primary_key)]
            record += [_stringify(row.get(col)) for col in sorted(all_keys - {self.primary_key})]
            record += [source_dataset, json.dumps(row, ensure_ascii=False, default=str)]
            values.append(record)

        self.conn.executemany(sql, values)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "SqliteLoader":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, default=str)
