"""Validate the ALREADY-BUILT corpus artefact against the stricter invariants
introduced by the fix wave, without re-fetching from NCBI.

Skips cleanly if the artefact is absent (e.g. a checkout that has not run
build_corpus yet). This is deliberately read-only: it proves the delivered
9,088-record corpus satisfies Fix 3 (no empty titles), Fix 4 (retmax
reconciliation surfaced in prisma/manifest counts), and general identifier
uniqueness -- all without a live 9,088-record retrieval.
"""
import csv
import json
import pathlib

import pytest

from pipeline.query import build_pubmed_query

REPO = pathlib.Path(__file__).resolve().parents[2]
SEARCH_DIR = REPO / "egm" / "search"
CORPUS_PATH = SEARCH_DIR / "raw" / "pubmed_corpus.json"
PRISMA_PATH = SEARCH_DIR / "prisma_counts.csv"
QUERY_PATH = SEARCH_DIR / "query_executed.txt"


def _load_corpus():
    if not CORPUS_PATH.exists():
        pytest.skip(f"no corpus artefact at {CORPUS_PATH}; nothing to validate")
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def test_manifest_record_count_matches_records():
    payload = _load_corpus()
    assert payload["manifest"]["record_count"] == len(payload["records"])


def test_every_record_has_a_non_empty_title():
    """Proves Fix 3 would not have fired on the real run: esummary never
    returned an empty title for any of the 9,088 records actually retrieved.
    """
    payload = _load_corpus()
    records = payload["records"]
    assert records, "corpus artefact has no records"
    empty = [r["record_id"] for r in records if not (r.get("title") or "").strip()]
    assert empty == [], f"records with empty titles: {empty[:20]}"


def test_record_ids_are_unique():
    payload = _load_corpus()
    record_ids = [r["record_id"] for r in payload["records"]]
    assert len(record_ids) == len(set(record_ids))


def test_non_null_pmids_are_unique():
    payload = _load_corpus()
    pmids = [r["pmid"] for r in payload["records"] if r.get("pmid")]
    assert len(pmids) == len(set(pmids))


def test_prisma_counts_reconcile_and_match_manifest():
    if not PRISMA_PATH.exists():
        pytest.skip(f"no PRISMA counts at {PRISMA_PATH}; nothing to validate")
    payload = _load_corpus()

    with PRISMA_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows, "prisma_counts.csv has no stages"

    for row in rows:
        identified, excluded, included = (
            int(row["identified"]), int(row["excluded"]), int(row["included"])
        )
        assert identified - excluded == included, (
            f"stage {row['stage']!r} does not reconcile: "
            f"{identified} - {excluded} != {included}"
        )

    final_included = int(rows[-1]["included"])
    assert final_included == payload["manifest"]["record_count"]


def test_query_executed_matches_current_query_builder():
    if not QUERY_PATH.exists():
        pytest.skip(f"no query_executed.txt at {QUERY_PATH}; nothing to validate")
    on_disk = QUERY_PATH.read_text(encoding="utf-8")
    current = build_pubmed_query(include_ncrna=False, date_limited=True)
    assert on_disk == current, (
        "query_executed.txt no longer matches build_pubmed_query(include_ncrna=False, "
        "date_limited=True); either the corpus is stale or the query changed unnoticed"
    )
