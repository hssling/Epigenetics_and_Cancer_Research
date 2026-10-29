"""Merging the PubMed and Europe PMC corpora into one deduplicated corpus.

All fixtures are synthetic; nothing here touches the network or the real
artefacts.
"""
import csv
import json
import pathlib

import pytest

from pipeline import merge_corpora
from pipeline.schema import DedupedRecord, SearchRecord

PUBMED_DEFAULTS = dict(
    source_db="pubmed",
    doi=None,
    pmid=None,
    title="DNA methylation and diet in adults",
    abstract="An abstract.",
    year=2020,
    journal="Journal of Epigenetics",
    authors=["Smith J", "Jones A"],
    retrieved_at="2026-09-13T10:00:00Z",
    query_hash="h" * 12,
)


def _pubmed(source_id: str, **over) -> dict:
    """A DedupedRecord dict, as it appears inside the PubMed artefact."""
    payload = {
        **PUBMED_DEFAULTS,
        "source_id": source_id,
        "record_id": f"egm-{int(source_id):06d}",
        "merged_from": [f"pubmed:{source_id}"],
        "dedup_rule": "unique",
    }
    payload.update(over)
    return DedupedRecord(**payload).model_dump()


def _europepmc(source_id: str, **over) -> dict:
    """A SearchRecord dict, as it appears inside the Europe PMC artefact."""
    payload = {
        **PUBMED_DEFAULTS,
        "source_db": "europepmc",
        "source_id": source_id,
        "journal": "bioRxiv",
    }
    payload.update(over)
    return SearchRecord(**payload).model_dump()


def _inputs(tmp_path: pathlib.Path, pubmed_records, europepmc_records,
            pubmed_internal_duplicates: int = 1):
    """Lay out search/raw/*.json plus the PubMed-stage prisma_counts.csv."""
    search = tmp_path / "search"
    (search / "raw").mkdir(parents=True)

    pubmed_path = search / "raw" / "pubmed_corpus_with_abstracts.json"
    pubmed_path.write_text(json.dumps({
        "manifest": {"record_count": len(pubmed_records)},
        "records": pubmed_records,
    }), encoding="utf-8")

    europepmc_path = search / "raw" / "europepmc_corpus.json"
    europepmc_path.write_text(json.dumps({
        "manifest": {"record_count": len(europepmc_records)},
        "records": europepmc_records,
    }), encoding="utf-8")

    identified = len(pubmed_records) + pubmed_internal_duplicates
    with (search / "prisma_counts.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["stage", "identified", "excluded", "included", "reason"])
        writer.writerow([
            "identification", identified, pubmed_internal_duplicates,
            len(pubmed_records),
            f"duplicates removed (doi={pubmed_internal_duplicates}, pmid=0, fuzzy=0)",
        ])

    return pubmed_path, europepmc_path, search / "combined.json", search / "combined_prisma.csv"


def _records(path: pathlib.Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["records"]


def test_preprint_merges_into_its_published_version(tmp_path):
    """A preprint and its published version share a normalised title, first
    author and year. Neither carries a conflicting DOI, so they are one paper.

    A DOI-identical decoy pair rides along so the merge still excludes
    something if the fuzzy rule stops firing; that keeps the failure signal on
    this test's own assertions rather than on PrismaFlow.validate().
    """
    pubmed_records = [
        _pubmed("111", doi="10.1000/published"),
        _pubmed("222", doi="10.1000/decoy", title="An unrelated methylation study"),
    ]
    europepmc_records = [
        _europepmc("PPR:PPR1", doi=None, title="DNA methylation and diet in adults."),
        _europepmc("PPR:PPR2", doi="10.1000/decoy",
                   title="An unrelated methylation study"),
    ]
    pubmed_path, europepmc_path, out, prisma = _inputs(
        tmp_path, pubmed_records, europepmc_records)

    counts = merge_corpora.merge(pubmed_path, europepmc_path, out, prisma)

    kept = {r["source_id"]: r for r in _records(out)}
    assert "PPR:PPR1" not in kept, "the preprint survived as its own record"
    assert sorted(kept["111"]["merged_from"]) == ["europepmc:PPR:PPR1", "pubmed:111"]
    assert kept["111"]["source_db"] == "pubmed"
    assert counts["removed_fuzzy"] == 1


def test_conflicting_dois_do_not_merge_despite_identical_titles(tmp_path):
    """Two records that both carry a DOI, and disagree, are different papers.

    A genuinely duplicated pair rides along so the merge is a realistic one:
    PrismaFlow.validate() refuses a flow that excluded nothing at all, and a
    zero-removal merge of two real corpora would itself be a defect.

    The Europe PMC fixtures are deliberately PMC:, not PPR:. As of 2026-09-14
    the DOI-conflict guard is scoped to non-preprint pairs, because a preprint
    and its published version always disagree on DOI by construction (see
    test_preprint_with_conflicting_doi_DOES_merge in test_dedup.py). Written
    with PPR: fixtures this test would merge them and so would no longer
    exercise the guard at all -- it would pass or fail for the wrong reason.
    """
    pubmed_records = [
        _pubmed("111", doi="10.1000/published"),
        _pubmed("222", doi="10.1000/decoy", title="An unrelated methylation study"),
    ]
    europepmc_records = [
        _europepmc("PMC:PMC1", doi="10.1000/OTHER"),
        _europepmc("PMC:PMC2", doi="10.1000/decoy",
                   title="An unrelated methylation study"),
    ]
    pubmed_path, europepmc_path, out, prisma = _inputs(
        tmp_path, pubmed_records, europepmc_records)

    counts = merge_corpora.merge(pubmed_path, europepmc_path, out, prisma)

    kept = _records(out)
    merged_from = [set(r["merged_from"]) for r in kept]
    assert {"pubmed:111"} in merged_from, "the PubMed record was collapsed away"
    assert {"europepmc:PMC:PMC1"} in merged_from, "the PMC record was collapsed away"
    assert len(kept) == 3, "conflicting DOIs must not be collapsed"
    assert counts["removed_fuzzy"] == 0
    assert counts["removed_total"] == 1  # the decoy pair only


def test_pubmed_record_survives_not_the_preprint(tmp_path):
    """Concatenation order is load-bearing: deduplicate() keeps the FIRST
    record of a merged group, and the peer-reviewed MEDLINE record is the
    better survivor than the preprint it supersedes."""
    pubmed_records = [_pubmed(
        "111", doi=None,
        title="DNA methylation and diet in adults",
        journal="Journal of Epigenetics",
    )]
    europepmc_records = [_europepmc(
        "PPR:PPR1", doi=None,
        title="DNA methylation and diet in adults.",
        journal="bioRxiv",
    )]
    pubmed_path, europepmc_path, out, prisma = _inputs(
        tmp_path, pubmed_records, europepmc_records)

    merge_corpora.merge(pubmed_path, europepmc_path, out, prisma)

    kept = _records(out)
    assert len(kept) == 1
    assert kept[0]["source_db"] == "pubmed"
    assert kept[0]["title"] == "DNA methylation and diet in adults"
    assert kept[0]["journal"] == "Journal of Epigenetics"


def test_dropped_fields_do_not_leak(tmp_path):
    """DedupedRecord extras are dropped by selecting the SearchRecord field
    names, never by deleting known keys: a field added to DedupedRecord later
    must not silently leak into the union."""
    record = _pubmed("111")
    record["some_future_field"] = "must not leak"

    converted = merge_corpora.to_search_record(record)

    assert isinstance(converted, SearchRecord)
    dumped = converted.model_dump()
    for dropped in ("record_id", "merged_from", "dedup_rule", "some_future_field"):
        assert dropped not in dumped, f"{dropped} leaked into the SearchRecord"
    assert set(dumped) == set(SearchRecord.model_fields)


def test_record_ids_are_renumbered_contiguously(tmp_path):
    pubmed_records = [
        _pubmed("1", doi="10.1/a", title="Alpha study"),
        _pubmed("2", doi="10.1/b", title="Beta study"),
    ]
    europepmc_records = [
        _europepmc("PPR:1", doi="10.1/c", title="Gamma study"),
        _europepmc("PPR:2", doi="10.1/a", title="Alpha study"),
    ]
    pubmed_path, europepmc_path, out, prisma = _inputs(
        tmp_path, pubmed_records, europepmc_records)

    merge_corpora.merge(pubmed_path, europepmc_path, out, prisma)

    ids = [r["record_id"] for r in _records(out)]
    assert ids == [f"egm-{n:06d}" for n in range(1, len(ids) + 1)]
    assert ids[0] == "egm-000001"


def test_prisma_flow_validates(tmp_path):
    pubmed_records = [
        _pubmed("1", doi="10.1/a", title="Alpha study"),
        _pubmed("2", doi="10.1/b", title="Beta study"),
    ]
    europepmc_records = [_europepmc("PPR:2", doi="10.1/a", title="Alpha study")]
    pubmed_path, europepmc_path, out, prisma = _inputs(
        tmp_path, pubmed_records, europepmc_records, pubmed_internal_duplicates=1)

    counts = merge_corpora.merge(pubmed_path, europepmc_path, out, prisma)

    with prisma.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    by_stage = {row["stage"]: row for row in rows}
    assert set(by_stage) == {"identification_pubmed", "identification_combined"}

    for row in rows:
        assert int(row["identified"]) - int(row["excluded"]) == int(row["included"])
        assert row["reason"].strip()

    pubmed_stage = by_stage["identification_pubmed"]
    combined = by_stage["identification_combined"]
    assert int(pubmed_stage["identified"]) == len(pubmed_records) + 1
    assert int(pubmed_stage["excluded"]) == 1
    # The bridge: PubMed survivors + Europe PMC retrieved = the union.
    assert int(combined["identified"]) == (
        int(pubmed_stage["included"]) + len(europepmc_records)
    )
    assert int(combined["excluded"]) == counts["removed_total"]
    assert int(combined["included"]) == len(_records(out))


def test_refuses_to_overwrite_existing_output(tmp_path):
    pubmed_records = [_pubmed("1", doi="10.1/a")]
    europepmc_records = [_europepmc("PPR:1", doi="10.1/a")]
    pubmed_path, europepmc_path, out, prisma = _inputs(
        tmp_path, pubmed_records, europepmc_records)
    out.write_text("{}", encoding="utf-8")

    with pytest.raises(FileExistsError):
        merge_corpora.merge(pubmed_path, europepmc_path, out, prisma)

    assert not prisma.exists(), "a refused merge must leave no PRISMA file behind"
