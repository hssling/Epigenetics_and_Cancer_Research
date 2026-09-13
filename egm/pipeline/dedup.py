"""Deduplication: DOI, then PMID, then fuzzy title (spec section 5.3).

Counts are returned per rule so the PRISMA diagram reports real numbers.
"""
import re
from typing import Optional

from rapidfuzz import fuzz

from pipeline.schema import DedupedRecord, SearchRecord

_DOI_PREFIX = re.compile(r"^(https?://)?(dx\.)?doi\.org/", re.IGNORECASE)
_PUNCT = re.compile(r"[^a-z0-9 ]")
_SPACES = re.compile(r"\s+")


def normalise_doi(doi: Optional[str]) -> Optional[str]:
    if doi is None:
        return None
    cleaned = _DOI_PREFIX.sub("", doi.strip()).lower().strip()
    return cleaned or None


def normalise_title(title: str) -> str:
    return _SPACES.sub(" ", _PUNCT.sub("", title.lower())).strip()


def _first_author_surname(record: SearchRecord) -> str:
    return record.authors[0].split()[0].lower() if record.authors else ""


def _key(record: SearchRecord) -> str:
    return f"{record.source_db}:{record.source_id}"


def deduplicate(
    records: list[SearchRecord], fuzzy_threshold: int = 95
) -> tuple[list[DedupedRecord], dict[str, int]]:
    """Collapse duplicates, returning survivors and per-rule counts."""
    counts = {
        "input": len(records), "removed_doi": 0, "removed_pmid": 0,
        "removed_fuzzy": 0, "removed_total": 0, "output": 0,
    }

    by_doi: dict[str, int] = {}
    by_pmid: dict[str, int] = {}
    survivors: list[dict] = []

    for record in records:
        doi = normalise_doi(record.doi)
        pmid = (record.pmid or "").strip() or None
        index: Optional[int] = None
        rule = "unique"

        if doi is not None and doi in by_doi:
            index, rule = by_doi[doi], "doi"
            counts["removed_doi"] += 1
        elif pmid is not None and pmid in by_pmid:
            index, rule = by_pmid[pmid], "pmid"
            counts["removed_pmid"] += 1
        elif doi is None and pmid is None:
            norm_title = normalise_title(record.title)
            surname = _first_author_surname(record)
            for position, existing in enumerate(survivors):
                if existing["year"] != record.year or existing["surname"] != surname:
                    continue
                if fuzz.ratio(existing["norm_title"], norm_title) >= fuzzy_threshold:
                    index, rule = position, "fuzzy_title"
                    counts["removed_fuzzy"] += 1
                    break

        if index is not None:
            survivors[index]["merged_from"].append(_key(record))
            if survivors[index]["rule"] == "unique":
                survivors[index]["rule"] = rule
            continue

        survivors.append({
            "record": record,
            "merged_from": [_key(record)],
            "rule": "unique",
            "norm_title": normalise_title(record.title),
            "surname": _first_author_surname(record),
            "year": record.year,
        })
        position = len(survivors) - 1
        if doi is not None:
            by_doi[doi] = position
        if pmid is not None:
            by_pmid[pmid] = position

    deduped = [
        DedupedRecord(
            **entry["record"].model_dump(),
            record_id=f"egm-{n:06d}",
            merged_from=sorted(entry["merged_from"]),
            dedup_rule=entry["rule"],
        )
        for n, entry in enumerate(survivors, start=1)
    ]

    counts["removed_total"] = counts["removed_doi"] + counts["removed_pmid"] + counts["removed_fuzzy"]
    counts["output"] = len(deduped)
    return deduped, counts
