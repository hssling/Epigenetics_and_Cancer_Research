import json

import pytest

from pipeline import build_corpus as bc
from pipeline.integrity import IntegrityError
from pipeline.schema import SearchRecord


def _record(pmid, doi, title="A methylation study"):
    return SearchRecord(
        source_db="pubmed", source_id=pmid, doi=doi, pmid=pmid, title=title,
        abstract=None, year=2020, journal="J Epi", authors=["Smith J"],
        retrieved_at="2026-09-13T10:00:00Z", query_hash="h" * 12,
    )


def test_build_corpus_writes_artefacts_and_reconciles(tmp_path, mocker):
    mocker.patch.object(bc.pubmed, "search", return_value=["1", "2", "3"])
    mocker.patch.object(bc.pubmed, "fetch_summaries", return_value=[
        _record("1", "10.1/a"), _record("2", "10.1/a"), _record("3", "10.1/b"),
    ])

    counts = bc.build_corpus(output_dir=tmp_path, retmax=100, dry_run=False)

    assert counts["input"] == 3
    assert counts["output"] == 2
    assert counts["removed_total"] == 1

    payload = json.loads((tmp_path / "raw" / "pubmed_corpus.json").read_text(encoding="utf-8"))
    assert payload["manifest"]["record_count"] == 2
    assert payload["manifest"]["source_db"] == "pubmed"

    prisma = (tmp_path / "prisma_counts.csv").read_text(encoding="utf-8")
    assert "identification,3,1,2" in prisma


def test_dry_run_writes_nothing(tmp_path, mocker):
    mocker.patch.object(bc.pubmed, "count", return_value=9089)
    counts = bc.build_corpus(output_dir=tmp_path, retmax=100, dry_run=True)
    assert counts["available"] == 9089
    assert not (tmp_path / "raw").exists()


def test_zero_duplicates_across_a_real_corpus_raises(tmp_path, mocker):
    """A multi-thousand-record corpus with no duplicates means dedup silently failed."""
    records = [_record(str(n), f"10.1/{n}") for n in range(1200)]
    mocker.patch.object(bc.pubmed, "search", return_value=[str(n) for n in range(1200)])
    mocker.patch.object(bc.pubmed, "fetch_summaries", return_value=records)

    with pytest.raises(IntegrityError, match="zero exclusions"):
        bc.build_corpus(output_dir=tmp_path, retmax=2000, dry_run=False)


def test_zero_duplicates_raises_before_writing_raw_artefact(tmp_path, mocker):
    """Validation must happen before any artefact touches disk.

    If write_artefact ran first (the brief's original ordering), a retry after
    fixing the dedup defect would hit FileExistsError against the already-written
    raw export instead of allowing the run to simply be repeated.
    """
    records = [_record(str(n), f"10.1/{n}") for n in range(1200)]
    mocker.patch.object(bc.pubmed, "search", return_value=[str(n) for n in range(1200)])
    mocker.patch.object(bc.pubmed, "fetch_summaries", return_value=records)

    with pytest.raises(IntegrityError, match="zero exclusions"):
        bc.build_corpus(output_dir=tmp_path, retmax=2000, dry_run=False)

    assert not (tmp_path / "raw" / "pubmed_corpus.json").exists()
