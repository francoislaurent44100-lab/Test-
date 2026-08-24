"""Command-line entry point: python -m dpe_pipeline run [options]."""

from __future__ import annotations

import argparse
import logging
import sys

from .config import DATASETS, DEFAULT_DATASET
from .pipeline import run


def build_qs(department: str | None, commune_insee: str | None, since: str | None, until: str | None) -> str | None:
    """Build a data-fair Lucene `qs` filter from convenience CLI flags."""
    clauses = []
    if department:
        clauses.append(f'N°_département_BAN:"{department}"')
    if commune_insee:
        clauses.append(f'Code_INSEE_BAN:"{commune_insee}"')
    if since or until:
        lo = since or "*"
        hi = until or "*"
        clauses.append(f"Date_établissement_DPE:[{lo} TO {hi}]")
    return " AND ".join(clauses) or None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dpe-pipeline", description="Extract/transform/load ADEME DPE data.")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run one extract-transform-load pass.")
    run_p.add_argument("--dataset", choices=sorted(DATASETS), default=DEFAULT_DATASET)
    run_p.add_argument("--db", default="dpe.db", help="Path to the output SQLite database.")
    run_p.add_argument("--departement", help='French department code, e.g. "75".')
    run_p.add_argument("--commune-insee", help="INSEE code of a single commune.")
    run_p.add_argument("--since", help="Only DPE established on/after this ISO date.")
    run_p.add_argument("--until", help="Only DPE established on/before this ISO date.")
    run_p.add_argument("--qs", help="Raw data-fair Lucene query string (overrides the convenience filters above).")
    run_p.add_argument("--page-size", type=int, default=1000)
    run_p.add_argument("--limit", type=int, help="Stop after this many records (useful for testing).")
    run_p.add_argument("-v", "--verbose", action="store_true")

    list_p = sub.add_parser("list-datasets", help="List the known ADEME DPE datasets.")

    args = parser.parse_args(argv)

    if args.command == "list-datasets":
        for key, ds in sorted(DATASETS.items()):
            print(f"{key:24s} {ds.label}\n{'':24s} {ds.base_url}")
        return 0

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s")

    qs = args.qs or build_qs(args.departement, args.commune_insee, args.since, args.until)
    result = run(
        dataset_key=args.dataset,
        db_path=args.db,
        qs=qs,
        page_size=args.page_size,
        limit=args.limit,
    )
    print(f"Loaded {result.records_loaded} records into {result.db_path} (table '{result.table}').")
    return 0


if __name__ == "__main__":
    sys.exit(main())
