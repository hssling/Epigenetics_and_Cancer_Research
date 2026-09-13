from pipeline.dedup import deduplicate, normalise_doi, normalise_title
from pipeline.schema import SearchRecord


def _record(source_db, source_id, doi=None, pmid=None, title="A study", year=2020,
            authors=("Smith J",)):
    return SearchRecord(
        source_db=source_db, source_id=source_id, doi=doi, pmid=pmid, title=title,
        abstract=None, year=year, journal="J", authors=list(authors),
        retrieved_at="2026-09-13T10:00:00Z", query_hash="h" * 12,
    )


def test_normalise_doi_lowercases_and_strips_prefix():
    assert normalise_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert normalise_doi("  10.1000/ABC  ") == "10.1000/abc"


def test_normalise_doi_passes_through_none():
    assert normalise_doi(None) is None
    assert normalise_doi("   ") is None


def test_normalise_title_strips_punctuation_and_case():
    assert normalise_title("Epigenetics: A Review!") == "epigenetics a review"


def test_unique_records_all_survive():
    records = [_record("pubmed", "1", doi="10.1/a"), _record("embase", "2", doi="10.1/b")]
    kept, counts = deduplicate(records)
    assert len(kept) == 2
    assert counts["input"] == 2
    assert counts["removed_total"] == 0


def test_doi_duplicates_collapse():
    records = [
        _record("pubmed", "1", doi="10.1/a"),
        _record("embase", "2", doi="https://doi.org/10.1/A"),
    ]
    kept, counts = deduplicate(records)
    assert len(kept) == 1
    assert counts["removed_doi"] == 1
    assert kept[0].dedup_rule == "doi"
    assert sorted(kept[0].merged_from) == ["embase:2", "pubmed:1"]


def test_pmid_duplicates_collapse_when_doi_absent():
    records = [_record("pubmed", "1", pmid="999"), _record("central", "2", pmid="999")]
    kept, counts = deduplicate(records)
    assert len(kept) == 1
    assert counts["removed_pmid"] == 1


def test_fuzzy_title_duplicates_collapse():
    records = [
        _record("wos", "1", title="DNA methylation and diet in adults"),
        _record("embase", "2", title="DNA methylation and diet in adults."),
    ]
    kept, counts = deduplicate(records)
    assert len(kept) == 1
    assert counts["removed_fuzzy"] == 1


def test_same_title_different_year_kept_separate():
    records = [
        _record("wos", "1", title="Cohort study", year=2018),
        _record("embase", "2", title="Cohort study", year=2022),
    ]
    assert len(deduplicate(records)[0]) == 2


def test_counts_reconcile():
    records = [
        _record("pubmed", "1", doi="10.1/a"),
        _record("embase", "2", doi="10.1/a"),
        _record("wos", "3", doi="10.1/b"),
    ]
    kept, counts = deduplicate(records)
    assert counts["input"] - counts["removed_total"] == counts["output"] == len(kept)
