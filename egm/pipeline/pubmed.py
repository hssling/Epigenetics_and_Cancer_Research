"""NCBI E-utilities client.

Absent fields become explicit None. This module never substitutes a value
for missing data (spec section 8.3 rule 1).
"""
import re
import time
import xml.etree.ElementTree as ET
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


def _get_text(endpoint: str, params: dict[str, Any]) -> str:
    """As _get, but for endpoints returning XML rather than JSON."""
    params = {**params, "tool": NCBI_TOOL_NAME}
    last: Optional[Exception] = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=90)
            response.raise_for_status()
            return response.text
        except Exception as exc:  # noqa: BLE001 - re-raised as PubMedError below
            last = exc
            time.sleep(NCBI_RATE_LIMIT_SECONDS * (attempt + 1) * 3)
    raise PubMedError(f"{endpoint} failed after {MAX_ATTEMPTS} attempts: {last}") from last


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
        if "result" not in body:
            raise PubMedError(
                f"esummary response missing 'result' key for a batch of {len(batch)} "
                f"pmid(s) (first={batch[0]!r}, last={batch[-1]!r}); the batch would "
                "otherwise vanish from the corpus with no error"
            )
        result = body["result"]
        retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        missing: list[str] = []
        for pmid in batch:
            article = result.get(pmid)
            if article is None:
                missing.append(pmid)
                continue
            title = (article.get("title") or "").strip()
            if not title:
                raise PubMedError(
                    f"esummary record for pmid {pmid!r} has no title; title is a "
                    "required field and must never be defaulted to an empty string"
                )
            journal = (article.get("fulljournalname") or "").strip()
            records.append(
                SearchRecord(
                    source_db="pubmed",
                    source_id=pmid,
                    doi=_extract_doi(article),
                    pmid=pmid,
                    title=title,
                    abstract=None,  # esummary does not carry abstracts
                    year=_parse_year(article.get("pubdate", "")),
                    journal=journal or None,
                    authors=[a.get("name", "") for a in article.get("authors", [])],
                    retrieved_at=retrieved_at,
                    query_hash=query_hash_value,
                )
            )
        if missing:
            shown = missing[:20]
            more = f" (+{len(missing) - 20} more)" if len(missing) > 20 else ""
            raise PubMedError(
                f"esummary omitted {len(missing)} pmid(s) requested in this batch: "
                f"{', '.join(shown)}{more}"
            )
        time.sleep(NCBI_RATE_LIMIT_SECONDS)
    return records


def _abstract_of(article: ET.Element) -> Optional[str]:
    """Join a record's AbstractText nodes, preserving section labels.

    Returns None when the record carries no abstract. That is a legitimate
    state for many PubMed records (editorials, some case reports, older
    indexing) and is reported as a count by the caller rather than raised.
    """
    nodes = article.findall(".//Abstract/AbstractText")
    if not nodes:
        return None

    parts: list[str] = []
    for node in nodes:
        text = " ".join("".join(node.itertext()).split())
        if not text:
            continue
        label = node.get("Label")
        parts.append(f"{label}: {text}" if label else text)

    joined = "\n\n".join(parts).strip()
    return joined or None


def fetch_abstracts(
    pmids: list[str], batch_size: int = 200
) -> dict[str, Optional[str]]:
    """Retrieve abstracts for `pmids` via efetch.

    Returns {pmid: abstract-or-None}. The two absences are treated
    differently on purpose:

      - a PMID missing from the response raises PubMedError, because a
        record that vanishes silently corrupts the PRISMA count;
      - a PMID present with no abstract maps to None, because that is a
        real property of the record and not an error.
    """
    if not pmids:
        return {}

    abstracts: dict[str, Optional[str]] = {}

    for start in range(0, len(pmids), batch_size):
        batch = pmids[start : start + batch_size]
        body = _get_text(
            "efetch.fcgi",
            {"db": "pubmed", "id": ",".join(batch), "retmode": "xml",
             "rettype": "abstract"},
        )

        try:
            root = ET.fromstring(body)
        except ET.ParseError as exc:
            raise PubMedError(
                f"efetch returned unparseable XML for a batch of {len(batch)} "
                f"pmid(s) (first={batch[0]!r}, last={batch[-1]!r}): {exc}"
            ) from exc

        for article in root.iter():
            if article.tag not in ("PubmedArticle", "PubmedBookArticle"):
                continue
            pmid_node = article.find(".//MedlineCitation/PMID")
            if pmid_node is None:
                pmid_node = article.find(".//BookDocument/PMID")
            if pmid_node is None or not (pmid_node.text or "").strip():
                continue
            abstracts[pmid_node.text.strip()] = _abstract_of(article)

        missing = [p for p in batch if p not in abstracts]
        if missing:
            shown = ", ".join(missing[:20])
            more = f" (and {len(missing) - 20} more)" if len(missing) > 20 else ""
            raise PubMedError(
                f"efetch omitted {len(missing)} requested pmid(s): {shown}{more}"
            )

        time.sleep(NCBI_RATE_LIMIT_SECONDS)

    return abstracts
