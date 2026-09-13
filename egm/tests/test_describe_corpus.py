"""Descriptive characterisation of the retrieved corpus.

These tests pin the arithmetic (quartiles computed by hand) and the framing
(the report must say, in terms, that it describes retrieval and not findings).
"""
import json
import pathlib

import pytest

from pipeline import describe_corpus
from pipeline.integrity import IntegrityError
from pipeline.schema import DedupedRecord

DEFAULTS = dict(
    source_db="pubmed",
    doi="10.1/a",
    pmid="1",
    title="A study",
    abstract="abc",
    year=2020,
    journal="Journal of Epigenetics",
    authors=["Smith J"],
    retrieved_at="2026-09-13T10:00:00Z",
    query_hash="h" * 12,
    dedup_rule="unique",
)


def _record(n: int, **over) -> dict:
    payload = {
        **DEFAULTS,
        "source_id": str(n),
        "record_id": f"egm-{n:06d}",
        "merged_from": [f"pubmed:{n}"],
    }
    payload.update(over)
    return DedupedRecord(**payload).model_dump()


def _corpus(tmp_path: pathlib.Path, records: list[dict]) -> pathlib.Path:
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps({
        "manifest": {"record_count": len(records)}, "records": records,
    }), encoding="utf-8")
    return path


def test_median_and_iqr_on_a_hand_checked_fixture(tmp_path):
    """Abstract lengths 1..9: median 5; Tukey hinges exclude the median, so
    the lower half is 1,2,3,4 (Q1 2.5) and the upper half 6,7,8,9 (Q3 7.5)."""
    records = [_record(n, abstract="x" * n) for n in range(1, 10)]
    corpus = _corpus(tmp_path, records)

    stats = describe_corpus.describe(corpus, tmp_path / "report.md")

    assert stats["abstract_length_median"] == 5
    assert stats["abstract_length_q1"] == 2.5
    assert stats["abstract_length_q3"] == 7.5
    assert stats["abstract_length_iqr"] == 5.0


def test_even_sample_median_is_the_midpoint_of_the_two_central_values(tmp_path):
    records = [_record(n, abstract="x" * n) for n in (1, 2, 3, 4)]
    corpus = _corpus(tmp_path, records)

    stats = describe_corpus.describe(corpus, tmp_path / "report.md")

    assert stats["abstract_length_median"] == 2.5


def test_records_without_an_abstract_are_excluded_from_length_stats(tmp_path):
    """A null abstract is absent, not zero-length: it must not drag the median
    down, but it must still count in the denominator."""
    records = [_record(n, abstract="x" * n) for n in range(1, 10)]
    records += [_record(100 + n, abstract=None) for n in range(3)]
    corpus = _corpus(tmp_path, records)

    stats = describe_corpus.describe(corpus, tmp_path / "report.md")

    assert stats["total"] == 12
    assert stats["with_abstract"] == 9
    assert stats["abstract_length_n"] == 9
    assert stats["abstract_length_median"] == 5, "a null abstract was treated as 0"
    assert stats["with_abstract_pct"] == pytest.approx(75.0)


def test_year_none_records_are_counted_separately_and_not_dropped(tmp_path):
    records = [
        _record(1, year=2020), _record(2, year=2020), _record(3, year=2015),
        _record(4, year=None), _record(5, year=None),
        _record(6, year=2011),
    ]
    corpus = _corpus(tmp_path, records)
    report_path = tmp_path / "report.md"

    stats = describe_corpus.describe(corpus, report_path)

    assert stats["year_missing"] == 2
    assert stats["year_outside_range"] == 1
    assert stats["year_counts"][2020] == 2
    assert stats["year_counts"][2015] == 1
    # Nothing may vanish between the table and the total.
    assert (
        sum(stats["year_counts"].values())
        + stats["year_missing"]
        + stats["year_outside_range"]
    ) == stats["total"]

    report = report_path.read_text(encoding="utf-8")
    assert "year absent" in report.lower()
    assert "2" in report


def test_what_this_is_not_paragraph_is_present(tmp_path):
    corpus = _corpus(tmp_path, [_record(1), _record(2, doi=None, pmid=None)])
    report_path = tmp_path / "report.md"

    describe_corpus.describe(corpus, report_path)
    report = report_path.read_text(encoding="utf-8")

    assert "What this is not" in report
    lowered = report.lower()
    for phrase in (
        "before any eligibility screening",
        "no record here has been assessed for inclusion",
        "is a finding about the epigenetics literature",
    ):
        assert phrase in lowered, f"missing from the report: {phrase!r}"


def test_first_line_states_this_is_pre_screening_description(tmp_path):
    corpus = _corpus(tmp_path, [_record(1)])
    report_path = tmp_path / "report.md"

    describe_corpus.describe(corpus, report_path)
    first_line = report_path.read_text(encoding="utf-8").splitlines()[0]

    assert "pre-screening description" in first_line.lower()
    assert "not findings" in first_line.lower()


def test_source_breakdown_counts_europepmc_prefixes(tmp_path):
    records = [
        _record(1),
        _record(2, source_db="europepmc", source_id="PPR:PPR1", pmid=None),
        _record(3, source_db="europepmc", source_id="PPR:PPR2", pmid=None),
        _record(4, source_db="europepmc", source_id="PMC:PMC1", pmid=None),
        _record(5, source_db="europepmc", source_id="ETH:ETH1", pmid=None),
        _record(6, source_db="europepmc", source_id="XYZ:1", pmid=None),
    ]
    corpus = _corpus(tmp_path, records)

    stats = describe_corpus.describe(corpus, tmp_path / "report.md")

    assert stats["by_source_db"] == {"pubmed": 1, "europepmc": 5}
    assert stats["by_europepmc_prefix"] == {"PPR": 2, "PMC": 1, "ETH": 1}, (
        "an unrecognised prefix was reported as if it were a known source"
    )
    assert stats["europepmc_unknown_prefix"] == 1


def test_identifier_and_dedup_rule_availability(tmp_path):
    records = [
        _record(1, doi="10.1/a", pmid="1", dedup_rule="unique"),
        _record(2, doi=None, pmid="2", dedup_rule="doi"),
        _record(3, doi="10.1/c", pmid=None, dedup_rule="fuzzy_title",
                merged_from=["pubmed:3", "europepmc:PPR:9"]),
        _record(4, doi=None, pmid=None, dedup_rule="unique"),
    ]
    corpus = _corpus(tmp_path, records)

    stats = describe_corpus.describe(corpus, tmp_path / "report.md")

    assert stats["with_doi"] == 2
    assert stats["with_doi_pct"] == pytest.approx(50.0)
    assert stats["with_pmid"] == 2
    assert stats["dedup_rule_counts"] == {"unique": 2, "doi": 1, "fuzzy_title": 1}
    assert stats["merged_multi"] == 1


def test_top_journals_and_distinct_count(tmp_path):
    records = (
        [_record(n, journal="Journal A") for n in range(1, 4)]
        + [_record(n, journal="Journal B") for n in range(4, 6)]
        + [_record(6, journal="Journal C"), _record(7, journal=None)]
    )
    corpus = _corpus(tmp_path, records)

    stats = describe_corpus.describe(corpus, tmp_path / "report.md")

    assert stats["top_journals"][0] == ("Journal A", 3)
    assert stats["top_journals"][1] == ("Journal B", 2)
    assert stats["distinct_journals"] == 3, "a null journal is not a journal"
    assert stats["journal_missing"] == 1


def test_empty_corpus_fails_loudly(tmp_path):
    """Named failure, not an incidental ZeroDivisionError deeper in."""
    corpus = _corpus(tmp_path, [])
    with pytest.raises(IntegrityError, match="no records"):
        describe_corpus.describe(corpus, tmp_path / "report.md")
