"""Deduplication: DOI, then PMID, then fuzzy title (spec section 5.3).

Counts are returned per rule so the PRISMA diagram reports real numbers.
"""
import re
from typing import Optional

from rapidfuzz import fuzz

from pipeline.config import PREPRINT_SOURCE_ID_PREFIX
from pipeline.schema import DedupedRecord, SearchRecord

_DOI_PREFIX = re.compile(r"^(https?://)?(dx\.)?doi\.org/", re.IGNORECASE)
_PUNCT = re.compile(r"[^a-z0-9 ]")
_SPACES = re.compile(r"\s+")

# A preprint precedes its journal version by 0-2 years, so the two never share
# a publication year. Applied ONLY when one record of a pair is a preprint.
PREPRINT_YEAR_WINDOW = 2


def normalise_doi(doi: Optional[str]) -> Optional[str]:
    if doi is None:
        return None
    cleaned = _DOI_PREFIX.sub("", doi.strip()).lower().strip()
    return cleaned or None


def normalise_title(title: str) -> str:
    return _SPACES.sub(" ", _PUNCT.sub("", title.lower())).strip()


def _first_author_surname(record: SearchRecord) -> str:
    if not record.authors:
        return ""
    parts = record.authors[0].split()
    return parts[0].lower() if parts else ""


def _key(record: SearchRecord) -> str:
    return f"{record.source_db}:{record.source_id}"


def _is_preprint(record: SearchRecord) -> bool:
    """True for a Europe PMC preprint record (`source_id` prefix `PPR:`)."""
    return record.source_id.startswith(PREPRINT_SOURCE_ID_PREFIX)


def _years_compatible(
    existing_year: Optional[int], candidate_year: Optional[int], preprint_pair: bool
) -> bool:
    """Whether two publication years may belong to the same study.

    The exact-year gate exists to stop similar-titled but DISTINCT papers --
    annual reports, serial trials, successive cohort waves -- from collapsing
    into one record, and it earns its keep for every ordinary pair. A preprint
    and its published version are by definition the same study, posted 0-2
    years apart, so for that pair the gate is wrong rather than merely strict:
    it double-counted 78 studies in the combined corpus (see
    protocol/amendments.md, 2026-09-14). The relaxation is therefore narrowed
    to pairs where at least one record is a preprint; everywhere else exact
    equality is unchanged.

    Absent years: an absent year is absence, never a wildcard and never a
    stand-in zero (spec section 8.3 rule 1). `abs(None - 2021)` would raise,
    so a pair in which either year is None falls back to the strict rule,
    under which None never equals a real year and the merge is blocked. Two
    records that both state no year compare equal under that rule, which is
    the pre-existing behaviour and is left untouched.
    """
    if preprint_pair and existing_year is not None and candidate_year is not None:
        return abs(existing_year - candidate_year) <= PREPRINT_YEAR_WINDOW
    return existing_year == candidate_year


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
        else:
            norm_title = normalise_title(record.title)
            surname = _first_author_surname(record)
            record_is_preprint = _is_preprint(record)
            for position, existing in enumerate(survivors):
                if existing["surname"] != surname:
                    continue
                preprint_pair = record_is_preprint or existing["is_preprint"]
                if not _years_compatible(
                    existing["year"], record.year, preprint_pair
                ):
                    continue
                # Two records that both carry an identifier, and disagree on it,
                # are different papers however similar their titles -- EXCEPT
                # when one of them is a preprint. A preprint and its published
                # version ALWAYS carry different DOIs (10.1101/... from bioRxiv
                # or medRxiv, 10.21203/rs.3.rs-... from Research Square, against
                # the journal's own), so for that pair a DOI disagreement is the
                # expected state and carries no evidence of difference. Applying
                # the guard there double-counted 136 studies in this corpus.
                #
                # What carries the merge instead is the conjunction that remains:
                # fuzzy title >= threshold, an identical first-author surname, and
                # a publication year within PREPRINT_YEAR_WINDOW. The preprint
                # designation itself is not inferred from the DOI prefix but taken
                # from Europe PMC's own source classification (SRC:PPR), which is
                # authoritative rather than heuristic.
                #
                # The PMID guard is NOT relaxed: Europe PMC preprint records carry
                # no PMID at all, so a preprint pair never reaches it, and any pair
                # that does is two indexed records disagreeing on a MEDLINE
                # identifier -- which remains decisive.
                if (
                    not preprint_pair
                    and doi is not None
                    and existing["doi"] is not None
                    and doi != existing["doi"]
                ):
                    continue
                if pmid is not None and existing["pmid"] is not None and pmid != existing["pmid"]:
                    continue
                # Empty titles must never match each other: rapidfuzz.fuzz.ratio("", "")
                # is 100.0, which would otherwise collapse distinct untitled records.
                if not norm_title or not existing["norm_title"]:
                    continue
                if fuzz.ratio(existing["norm_title"], norm_title) >= fuzzy_threshold:
                    index, rule = position, "fuzzy_title"
                    counts["removed_fuzzy"] += 1
                    break

        if index is not None:
            survivors[index]["merged_from"].append(_key(record))
            if survivors[index]["rule"] == "unique":
                survivors[index]["rule"] = rule
            # Backfill identifiers learned from the merged record. Without this a
            # survivor that was created identifier-free stays that way forever, and
            # can bridge two records whose identifiers actually conflict.
            if doi is not None:
                if survivors[index]["doi"] is None:
                    survivors[index]["doi"] = doi
                by_doi.setdefault(doi, index)
            if pmid is not None:
                if survivors[index]["pmid"] is None:
                    survivors[index]["pmid"] = pmid
                by_pmid.setdefault(pmid, index)
            continue

        survivors.append({
            "record": record,
            "merged_from": [_key(record)],
            "rule": "unique",
            "norm_title": normalise_title(record.title),
            "surname": _first_author_surname(record),
            "year": record.year,
            "is_preprint": _is_preprint(record),
            "doi": doi,
            "pmid": pmid,
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
