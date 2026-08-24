"""Normalize raw ADEME DPE records into a flat, typed row ready for loading."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any

_SNAKE_RE = re.compile(r"[^a-z0-9]+")


def to_snake_case(field: str) -> str:
    """"N°_département_(BAN)" -> "n_departement_ban"."""
    ascii_field = unicodedata.normalize("NFKD", field).encode("ascii", "ignore").decode("ascii")
    return _SNAKE_RE.sub("_", ascii_field.lower()).strip("_")


_NUMERIC_HINTS = ("conso_", "emission_", "surface_", "annee_")


def _coerce(key: str, value: Any) -> Any:
    if value in (None, ""):
        return None
    if key.startswith(_NUMERIC_HINTS) or key.startswith("n_departement") or key.startswith("code_postal"):
        try:
            return float(value) if "." in str(value) else int(value)
        except (TypeError, ValueError):
            return value
    return value


def normalize_record(raw: dict[str, Any]) -> dict[str, Any]:
    """Rename every key to snake_case, coerce a handful of numeric fields,
    and keep the rest as-is so no data is silently dropped."""
    row: dict[str, Any] = {}
    for key, value in raw.items():
        snake_key = to_snake_case(key)
        row[snake_key] = _coerce(snake_key, value)
    return row


def dpe_letter_bucket(etiquette: str | None) -> str:
    """Group the A-G energy label into 'sobre' (A-C), 'moyen' (D-E) or
    'passoire' (F-G) for quick aggregate reporting."""
    if not etiquette:
        return "inconnu"
    letter = etiquette.strip().upper()
    if letter in ("A", "B", "C"):
        return "sobre"
    if letter in ("D", "E"):
        return "moyen"
    if letter in ("F", "G"):
        return "passoire"
    return "inconnu"


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
