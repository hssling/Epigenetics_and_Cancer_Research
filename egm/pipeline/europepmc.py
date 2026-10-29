"""Europe PMC REST client (registered-protocol substitution for Embase).

Why this source exists
----------------------
The registration (OSF 3xtf2) lists Embase. The investigator has no Embase
access, and the recorded substitution (protocol/amendments.md) is Europe PMC
on the basis that it adds coverage BEYOND MEDLINE: preprints, PMC-only
content, theses, agricola. PubMed/MEDLINE was already searched natively on
2026-09-13 (9,088 deduplicated records) with a precise field-tagged strategy.

Why the search is restricted to `NOT SRC:MED`
---------------------------------------------
This is a ruling, not a tuning knob. Fetching all Europe PMC hits and
deduplicating against the PubMed corpus would import MEDLINE records that the
registered PubMed strategy deliberately EXCLUDED via `[pt]` and `[MeSH]`
filters (`NOT (review[pt] OR ... OR letter[pt])`, `humans[MeSH]`) which Europe
PMC's query syntax cannot express. That would silently loosen a registered
strategy. Do not "improve" this by dropping the SRC filter.

Why every free-text term is wrapped as `(TITLE:x OR ABSTRACT:x)`
----------------------------------------------------------------
Europe PMC free-text terms search FULL TEXT, not title/abstract. The same
strategy left unwrapped returns 239,868 records. Wrapping each term mirrors
PubMed's `[tiab]` and is what makes the strategy comparable to the registered
one. The next reader will otherwise "simplify" `_ta()` away and silently
multiply the corpus 40-fold.

Live counts observed 2026-09-14 with the query built here:
    all sources        5,982
    NOT SRC:MED          890   <- what this module fetches
      of which SRC:PPR   672
      of which SRC:PMC   194

Absent fields become explicit None. This module never substitutes a value for
missing data (spec section 8.3 rule 1). Europe PMC requires no API key and
this module sends no credential of any kind.
"""
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

import requests

from pipeline.config import SOURCE_ID_SEPARATOR
from pipeline.schema import SearchRecord

BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
MAX_ATTEMPTS = 3
RATE_LIMIT_SECONDS = 0.34  # ~3 requests/sec; Europe PMC publishes no hard cap


class EuropePMCError(Exception):
    """Raised when Europe PMC cannot be reached or returns an unusable body."""


def _get(params: dict[str, Any]) -> dict[str, Any]:
    last: Optional[Exception] = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.get(BASE_URL, params=params, timeout=120)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001 - re-raised as EuropePMCError below
            last = exc
            time.sleep(RATE_LIMIT_SECONDS * (attempt + 1) * 3)
    raise EuropePMCError(
        f"Europe PMC search failed after {MAX_ATTEMPTS} attempts: {last}"
    ) from last


# ---------------------------------------------------------------------------
# Query construction
# ---------------------------------------------------------------------------

def _ta(terms: Sequence[str]) -> str:
    """Restrict each term to title OR abstract, mirroring PubMed's [tiab].

    Without this, Europe PMC matches the term anywhere in the full text.
    See the module docstring: removing this is a 40-fold corpus inflation.
    """
    parts = []
    for term in terms:
        quoted = f'"{term}"' if " " in term or "-" in term else term
        parts.append(f"(TITLE:{quoted} OR ABSTRACT:{quoted})")
    return "(" + " OR ".join(parts) + ")"


# Term lists reproduced verbatim from the live-validated probe
# (.superpowers/sdd/2026-09-13-egm-screening/epmc-query-probe.py).
METHYLATION = _ta([
    "DNA methylation", "methylome", "EWAS", "epigenome-wide", "CpG",
    "5-methylcytosine", "hydroxymethylation",
])
HISTONE = _ta([
    "histone", "histones", "chromatin", "H3K4", "H3K27", "HDAC",
    "histone deacetylase",
])
CLOCK = _ta([
    "epigenetic clock", "epigenetic age", "DNAm age", "GrimAge", "PhenoAge",
    "Horvath clock", "biological age",
])
CORE = f"({METHYLATION} OR {HISTONE} OR {CLOCK})"
EXPOSURE = _ta([
    "diet", "dietary", "nutrition", "nutritional", "supplement",
    "supplementation", "exercise", "physical activity", "smoking", "tobacco",
    "alcohol", "air pollution", "particulate matter", "pesticide", "pesticides",
    "heavy metals", "psychosocial", "sleep", "weight loss", "intervention",
])
CLINICAL_USE = _ta([
    "screening", "early detection", "diagnosis", "diagnostic", "prognosis",
    "prognostic", "risk prediction", "risk stratification", "triage",
    "biomarker", "biomarkers", "treatment response", "monitoring",
])
DESIGN = _ta([
    "randomised", "randomized", "cohort", "case-control", "trial",
    "cross-sectional",
])
HUMAN = _ta([
    "human", "humans", "patients", "participants", "women", "men", "adults",
    "children",
])
YEARS = "(PUB_YEAR:[2015 TO 2026])"


def build_europepmc_query(exclude_medline: bool) -> str:
    """Compose the Europe PMC strategy. The flag is explicit by design.

    `exclude_medline=True` appends `NOT SRC:MED`, which is what the recorded
    amendment commits to: Europe PMC contributes coverage BEYOND the already
    executed native MEDLINE search, not a second pass over it.
    """
    base = (
        f"{CORE} AND {HUMAN} AND ({EXPOSURE} OR {CLINICAL_USE}) "
        f"AND {DESIGN} AND {YEARS}"
    )
    if exclude_medline:
        return f"({base}) NOT SRC:MED"
    return base


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def count(query: str) -> int:
    """Number of records matching `query`, without retrieving them."""
    body = _get({"query": query, "format": "json", "pageSize": 1,
                 "resultType": "lite"})
    if "hitCount" not in body:
        raise EuropePMCError(
            f"Europe PMC response missing 'hitCount' for query: {query!r}"
        )
    return int(body["hitCount"])


def _parse_year(pub_year: Any) -> Optional[int]:
    """Extract a 4-digit year, or None. Never guesses."""
    match = re.search(r"\b(19|20)\d{2}\b", str(pub_year or ""))
    return int(match.group(0)) if match else None


def _parse_authors(author_string: Any) -> list[str]:
    """Split Europe PMC's authorString. Absent -> empty list, never a stand-in."""
    text = (author_string or "").strip()
    if text.endswith("."):
        text = text[:-1]
    if not text:
        return []
    return [name.strip() for name in text.split(", ") if name.strip()]


def _parse_journal(result: dict[str, Any]) -> Optional[str]:
    journal = result.get("journalInfo", {}).get("journal", {}).get("title")
    return (journal or "").strip() or None


def _to_record(
    result: dict[str, Any], query_hash_value: str, retrieved_at: str
) -> SearchRecord:
    """Map one Europe PMC result. Absent optional fields become None; an
    absent title raises, because title is required and must never default."""
    source = (result.get("source") or "").strip()
    identifier = (result.get("id") or "").strip()
    if not source or not identifier:
        raise EuropePMCError(
            "Europe PMC result is missing 'source' and/or 'id'; source_id "
            f"cannot be formed: {result!r}"
        )
    source_id = f"{source}{SOURCE_ID_SEPARATOR}{identifier}"

    title = (result.get("title") or "").strip()
    if not title:
        raise EuropePMCError(
            f"Europe PMC result {source_id!r} (id {identifier!r}) has no title; "
            "title is a required field and must never be defaulted to an empty "
            "string -- two untitled records would collide under fuzzy matching"
        )

    return SearchRecord(
        source_db="europepmc",
        source_id=source_id,
        doi=(result.get("doi") or "").strip() or None,
        pmid=(result.get("pmid") or "").strip() or None,
        title=title,
        abstract=(result.get("abstractText") or "").strip() or None,
        year=_parse_year(result.get("pubYear")),
        journal=_parse_journal(result),
        authors=_parse_authors(result.get("authorString")),
        retrieved_at=retrieved_at,
        query_hash=query_hash_value,
    )


def search_records(
    query: str, query_hash_value: str, page_size: int = 1000
) -> list[SearchRecord]:
    """Retrieve every record matching `query`, paginating with cursorMark.

    Termination, and its trap: on a paged result set Europe PMC signals the end
    by returning the SAME cursorMark it was given. A naive `while next_cursor:`
    loop therefore never terminates -- it re-requests the final page forever.
    When the whole set fits in one page it instead omits nextCursorMark
    altogether. Both are honoured below, and both are cross-checked against
    hitCount so that "no more pages" can never mean "corpus truncated".

    `resultType=core` is required: `lite` omits abstractText, which would
    yield a corpus screenable on titles alone.
    """
    records: list[SearchRecord] = []
    cursor = "*"

    while True:
        body = _get({
            "query": query,
            "format": "json",
            "pageSize": page_size,
            "cursorMark": cursor,
            "resultType": "core",
        })

        if "hitCount" not in body:
            raise EuropePMCError(
                f"Europe PMC response missing 'hitCount' for query: {query!r}"
            )
        hit_count = int(body["hitCount"])

        result_list = body.get("resultList")
        if not isinstance(result_list, dict) or "result" not in result_list:
            raise EuropePMCError(
                "Europe PMC response missing 'resultList'/'result' at cursorMark "
                f"{cursor!r}; the page would otherwise vanish from the corpus "
                "with no error"
            )
        page = result_list["result"]

        next_cursor = body.get("nextCursorMark")

        if not page and len(records) < hit_count:
            raise EuropePMCError(
                f"Europe PMC returned 0 results at cursorMark {cursor!r} while "
                f"{hit_count - len(records)} of {hit_count} records were still "
                "outstanding; the corpus would be silently truncated"
            )

        retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for result in page:
            records.append(_to_record(result, query_hash_value, retrieved_at))

        if len(records) > hit_count:
            raise EuropePMCError(
                f"accumulated {len(records)} records but hitCount={hit_count}; "
                "the cursor is looping or the index shifted mid-run, so this is "
                "not the corpus that was counted"
            )

        # Europe PMC signals exhaustion in two ways, both observed live on
        # 2026-09-14 against this query:
        #   - pageSize=1000 (whole set on one page): nextCursorMark is OMITTED
        #     from the response body entirely;
        #   - pageSize=25 (paged): the final page echoes back the cursorMark it
        #     was sent.
        # Neither is treated as a bare stop signal. Exhaustion is only
        # believable if every counted record actually arrived; short of that,
        # accepting it would return a silently truncated corpus.
        if not next_cursor or next_cursor == cursor:
            if len(records) < hit_count:
                raise EuropePMCError(
                    f"Europe PMC signalled exhaustion at cursorMark {cursor!r} "
                    f"(nextCursorMark={next_cursor!r}) with only {len(records)} "
                    f"of {hit_count} records retrieved; the corpus would be "
                    "silently truncated"
                )
            return records

        cursor = next_cursor
        time.sleep(RATE_LIMIT_SECONDS)
