"""Thin client for ADEME's data-fair API (the backend behind the DPE
dataservices catalogued on data.gouv.fr)."""

from __future__ import annotations

import logging
import time
from typing import Any, Iterator

import requests

from .config import DpeDataset

logger = logging.getLogger(__name__)

USER_AGENT = "dpe-pipeline/0.1 (+https://github.com/francoislaurent44100-lab/test-)"


class AdemeApiError(RuntimeError):
    pass


class AdemeDpeClient:
    """Reads DPE records from a data-fair dataset via GET /lines pagination.

    data-fair returns a "next" field with a ready-to-use URL for the
    following page, so we just follow it until it disappears rather than
    hand-rolling cursor arithmetic.
    """

    def __init__(
        self,
        dataset: DpeDataset,
        session: requests.Session | None = None,
        timeout: float = 30.0,
        max_retries: int = 5,
    ) -> None:
        self.dataset = dataset
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", USER_AGENT)
        self.timeout = timeout
        self.max_retries = max_retries

    def _get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
            else:
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", 2 * attempt))
                    logger.warning("Rate limited by ADEME API, sleeping %.1fs", retry_after)
                    time.sleep(retry_after)
                    continue
                if resp.status_code >= 500:
                    last_error = AdemeApiError(f"{resp.status_code} {resp.text[:200]}")
                else:
                    resp.raise_for_status()
                    return resp.json()
            sleep_s = min(2**attempt, 30)
            logger.warning("Request to %s failed (%s), retrying in %ss", url, last_error, sleep_s)
            time.sleep(sleep_s)
        raise AdemeApiError(f"Giving up on {url} after {self.max_retries} attempts") from last_error

    def schema(self) -> list[dict[str, Any]]:
        """Return the dataset's field list as published by /schema."""
        return self._get(f"{self.dataset.base_url}/schema")

    def available_fields(self) -> set[str]:
        return {field["key"] for field in self.schema()}

    def iter_lines(
        self,
        select: list[str] | None = None,
        qs: str | None = None,
        sort: str | None = None,
        page_size: int = 1000,
    ) -> Iterator[dict[str, Any]]:
        """Yield every record matching the filters, paginating transparently."""
        params: dict[str, Any] = {"size": page_size}
        if select:
            params["select"] = ",".join(select)
        if qs:
            params["qs"] = qs
        if sort:
            params["sort"] = sort

        url = f"{self.dataset.base_url}/lines"
        page = 0
        total_yielded = 0
        while url:
            page += 1
            payload = self._get(url, params=params if page == 1 else None)
            results = payload.get("results", [])
            logger.info("Fetched page %d (%d records) for %s", page, len(results), self.dataset.key)
            for record in results:
                yield record
                total_yielded += 1
            url = payload.get("next")
            params = None  # "next" is a fully-formed URL already carrying params
        logger.info("Done: %d records fetched for %s", total_yielded, self.dataset.key)
