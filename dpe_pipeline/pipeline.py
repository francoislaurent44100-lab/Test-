"""Wires the client, transform and loader together into one run."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .client import AdemeDpeClient
from .config import DATASETS, DEFAULT_SELECT, DpeDataset
from .load import SqliteLoader
from .transform import normalize_record

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    dataset: str
    records_loaded: int
    db_path: str
    table: str


def resolve_dataset(key: str) -> DpeDataset:
    try:
        return DATASETS[key]
    except KeyError as exc:
        raise ValueError(f"Unknown dataset '{key}'. Choices: {', '.join(sorted(DATASETS))}") from exc


def run(
    dataset_key: str,
    db_path: str,
    qs: str | None = None,
    select: list[str] | None = None,
    page_size: int = 1000,
    limit: int | None = None,
) -> RunResult:
    """Extract records matching `qs` from `dataset_key`, normalize them and
    upsert them into a SQLite table named after the dataset key."""
    dataset = resolve_dataset(dataset_key)
    client = AdemeDpeClient(dataset)

    fields_to_select = select if select is not None else DEFAULT_SELECT
    try:
        available = client.available_fields()
        fields_to_select = [f for f in fields_to_select if f in available] or None
    except Exception:  # pragma: no cover - best-effort convenience only
        logger.warning("Could not fetch schema for %s, selecting all fields", dataset.key)
        fields_to_select = None

    def normalized_rows():
        n = 0
        for raw in client.iter_lines(select=fields_to_select, qs=qs, page_size=page_size):
            yield normalize_record(raw)
            n += 1
            if limit is not None and n >= limit:
                return

    with SqliteLoader(db_path, table=dataset.key, primary_key=dataset.primary_key) as loader:
        loaded = loader.upsert_many(normalized_rows(), source_dataset=dataset.key)

    return RunResult(dataset=dataset.key, records_loaded=loaded, db_path=db_path, table=dataset.key)
