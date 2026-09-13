"""NCBI E-utilities client.

Absent fields become explicit None. This module never substitutes a value
for missing data (spec section 8.3 rule 1).
"""
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from pipeline.config import NCBI_RATE_LIMIT_SECONDS, NCBI_TOOL_NAME
from pipeline.schema import SearchRecord

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
MAX_ATTEMPTS = 3


class PubMedError(Exception):
    """Raised when E-utilities cannot be reached or returns an unusable body."""


def _get(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    params = {**params, "retmode": "json", "tool": NCBI_TOOL_NAME}
    last: Optional[Exception] = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001 - re-raised as PubMedError below
            last = exc
            time.sleep(NCBI_RATE_LIMIT_SECONDS * (attempt + 1) * 3)
    raise PubMedError(f"{endpoint} failed after {MAX_ATTEMPTS} attempts: {last}") from last


def _esearch_result(body: dict[str, Any], query: str) -> dict[str, Any]:
    """Extract esearchresult, raising PubMedError on an NCBI error payload."""
    result = body.get("esearchresult")
    if result is None:
        raise PubMedError(f"esearch response had no 'esearchresult' key for query: {query!r}")
    if "ERROR" in result:
        raise PubMedError(f"NCBI rejected the query ({result['ERROR']!r}): {query!r}")
    if "ERROR" in body:
        raise PubMedError(f"NCBI returned an error ({body['ERROR']!r}) for query: {query!r}")
    return result


def count(query: str) -> int:
    """Number of records matching `query`, without retrieving them."""
    body = _get("esearch.fcgi", {"db": "pubmed", "term": query, "retmax": 0})
    result = _esearch_result(body, query)
    if "count" not in result:
        raise PubMedError(f"esearch response missing 'count' for query: {query!r}")
    return int(result["count"])


def search(query: str, retmax: int) -> list[str]:
    """PMIDs matching `query`, up to `retmax`."""
    body = _get("esearch.fcgi", {"db": "pubmed", "term": query, "retmax": retmax})
    result = _esearch_result(body, query)
    if "idlist" not in result:
        raise PubMedError(f"esearch response missing 'idlist' for query: {query!r}")
    return list(result["idlist"])


def _parse_year(pubdate: str) -> Optional[int]:
    """Extract a 4-digit year, or None. Never guesses."""
    match = re.search(r"\b(19|20)\d{2}\b", pubdate or "")
    return int(match.group(0)) if match else None


def _extract_doi(article: dict[str, Any]) -> Optional[str]:
    for identifier in article.get("articleids", []):
        if identifier.get("idtype") == "doi":
            value = (identifier.get("value") or "").strip()
            return value or None
    return None


def fetch_summaries(
    pmids: list[str], query_hash_value: str, batch_size: int = 200
) -> list[SearchRecord]:
    """Retrieve summaries as SearchRecords. Absent fields become None."""
    records: list[SearchRecord] = []
    for start in range(0, len(pmids), batch_size):
        batch = pmids[start : start + batch_size]
        body = _get("esummary.fcgi", {"db": "pubmed", "id": ",".join(batch)})
        result = body.get("result", {})
        retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        for pmid in batch:
            article = result.get(pmid)
            if article is None:
                continue
            journal = (article.get("fulljournalname") or "").strip()
            records.append(
                SearchRecord(
                    source_db="pubmed",
                    source_id=pmid,
                    doi=_extract_doi(article),
                    pmid=pmid,
                    title=(article.get("title") or "").strip(),
                    abstract=None,  # esummary does not carry abstracts
                    year=_parse_year(article.get("pubdate", "")),
                    journal=journal or None,
                    authors=[a.get("name", "") for a in article.get("authors", [])],
                    retrieved_at=retrieved_at,
                    query_hash=query_hash_value,
                )
            )
        time.sleep(NCBI_RATE_LIMIT_SECONDS)
    return records
