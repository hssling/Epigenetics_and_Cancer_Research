"""Descriptive characterisation of the RETRIEVED corpus.

This is a pre-screening description of what the search returned, NOT findings.
Every number here counts records as retrieved by the registered search string.
No record described here has been assessed against the eligibility criteria, so
nothing in the output says anything about what the epigenetics literature
contains, how large any evidence base is, or where the gaps are. Those
statements can only be made after screening, and this module deliberately
cannot make them.

Run:
    python -m pipeline.describe_corpus \\
        --corpus search/raw/combined_corpus.json \\
        --output search/corpus_description.md

Quartiles are computed here by sorting and indexing rather than by importing
numpy/scipy/pandas: the pipeline does not need an array dependency to take a
median of a few thousand integers. The method is Tukey's (the median is
excluded from both halves when n is odd), which is stated in the report so the
numbers are reproducible by hand.

The report is a derived description, not a raw artefact: it may be regenerated
and overwritten, unlike the append-only corpus it reads.
"""
import argparse
import collections
import json
import pathlib
from typing import Any, Optional

from pipeline.integrity import IntegrityError
from pipeline.schema import DedupedRecord

YEAR_MIN = 2015
YEAR_MAX = 2026
TOP_JOURNALS = 20
EUROPEPMC_PREFIXES = ("PPR", "PMC", "ETH", "AGR")

NOT_FINDINGS = (
    "## What this is not\n\n"
    "These are records **retrieved by the search**, before any eligibility "
    "screening. No record here has been assessed for inclusion: not one has "
    "been read against the eligibility criteria, and the corpus certainly "
    "contains records that will be excluded. None of these counts is a finding "
    "about the epigenetics literature's content, size, or gaps -- they describe "
    "what a query returned from two bibliographic databases on one day, and "
    "nothing more. Counts of journals, years or abstracts characterise "
    "retrieval, not evidence."
)


def _median(values: list[float]) -> float:
    """Median of a pre-sorted list."""
    n = len(values)
    if n == 0:
        raise IntegrityError("median of an empty sample is undefined")
    middle = n // 2
    if n % 2:
        return float(values[middle])
    return (values[middle - 1] + values[middle]) / 2


def quartiles(sample: list[int]) -> tuple[float, float, float]:
    """(Q1, median, Q3) by Tukey's method: the median is excluded from the
    halves when n is odd. Sorted and indexed directly, with no array library.
    """
    if not sample:
        raise IntegrityError("quartiles of an empty sample are undefined")
    values = sorted(sample)
    n = len(values)
    median = _median(values)
    if n == 1:
        return median, median, median
    half = n // 2
    lower = values[:half]
    upper = values[half + 1:] if n % 2 else values[half:]
    return _median(lower), median, _median(upper)


def _load(corpus_path: pathlib.Path) -> list[DedupedRecord]:
    payload = json.loads(pathlib.Path(corpus_path).read_text(encoding="utf-8"))
    raw = payload.get("records")
    if raw is None:
        raise IntegrityError(f"{corpus_path} has no 'records' key; not a corpus artefact")
    if not raw:
        raise IntegrityError(f"{corpus_path} holds no records; nothing to describe")
    # Round-trip through the schema so a malformed record fails here rather
    # than silently skewing a count.
    return [DedupedRecord(**record) for record in raw]


def _prefix(source_id: str) -> Optional[str]:
    head = source_id.split(":", 1)[0]
    return head if head in EUROPEPMC_PREFIXES else None


def _percent(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 1)


def _summarise(records: list[DedupedRecord]) -> dict[str, Any]:
    total = len(records)

    by_source_db = collections.Counter(r.source_db for r in records)
    by_prefix: collections.Counter = collections.Counter()
    unknown_prefix = 0
    for record in records:
        if record.source_db != "europepmc":
            continue
        prefix = _prefix(record.source_id)
        if prefix is None:
            unknown_prefix += 1
        else:
            by_prefix[prefix] += 1

    year_counts = {year: 0 for year in range(YEAR_MIN, YEAR_MAX + 1)}
    year_missing = 0
    year_outside = 0
    for record in records:
        if record.year is None:
            year_missing += 1
        elif YEAR_MIN <= record.year <= YEAR_MAX:
            year_counts[record.year] += 1
        else:
            year_outside += 1

    journals = collections.Counter(r.journal for r in records if r.journal)
    journal_missing = sum(1 for r in records if not r.journal)

    lengths = [len(r.abstract) for r in records if r.abstract is not None]
    with_abstract = len(lengths)
    if lengths:
        q1, median, q3 = quartiles(lengths)
    else:
        q1 = median = q3 = None

    with_doi = sum(1 for r in records if r.doi)
    with_pmid = sum(1 for r in records if r.pmid)

    return {
        "total": total,
        "by_source_db": dict(by_source_db),
        "by_europepmc_prefix": dict(by_prefix),
        "europepmc_unknown_prefix": unknown_prefix,
        "year_counts": year_counts,
        "year_missing": year_missing,
        "year_outside_range": year_outside,
        "top_journals": journals.most_common(TOP_JOURNALS),
        "distinct_journals": len(journals),
        "journal_missing": journal_missing,
        "with_abstract": with_abstract,
        "with_abstract_pct": _percent(with_abstract, total),
        "abstract_length_n": with_abstract,
        "abstract_length_median": median,
        "abstract_length_q1": q1,
        "abstract_length_q3": q3,
        "abstract_length_iqr": None if q1 is None else q3 - q1,
        "with_doi": with_doi,
        "with_doi_pct": _percent(with_doi, total),
        "with_pmid": with_pmid,
        "with_pmid_pct": _percent(with_pmid, total),
        "dedup_rule_counts": dict(collections.Counter(r.dedup_rule for r in records)),
        "merged_multi": sum(1 for r in records if len(r.merged_from) > 1),
    }


def _render(stats: dict[str, Any], corpus_path: pathlib.Path) -> str:
    total = stats["total"]
    lines: list[str] = []

    lines.append(
        "**This is a pre-screening description of the retrieved corpus, not "
        "findings.**"
    )
    lines.append("")
    lines.append("# Corpus description")
    lines.append("")
    lines.append(f"Source artefact: `{corpus_path.name}`")
    lines.append("")
    lines.append(f"**Total records retrieved: {total}**")
    lines.append("")

    lines.append("## Records by source database")
    lines.append("")
    lines.append("| source_db | records | % |")
    lines.append("| --- | ---: | ---: |")
    for name, count in sorted(stats["by_source_db"].items(), key=lambda kv: -kv[1]):
        lines.append(f"| {name} | {count} | {_percent(count, total)} |")
    lines.append("")

    if stats["by_europepmc_prefix"]:
        lines.append("### Europe PMC records by source prefix")
        lines.append("")
        lines.append(
            "Derived from `source_id`. PPR = preprint, PMC = PubMed Central "
            "(non-MEDLINE), ETH = thesis, AGR = Agricola."
        )
        lines.append("")
        lines.append("| prefix | records |")
        lines.append("| --- | ---: |")
        for prefix in EUROPEPMC_PREFIXES:
            if prefix in stats["by_europepmc_prefix"]:
                lines.append(f"| {prefix} | {stats['by_europepmc_prefix'][prefix]} |")
        if stats["europepmc_unknown_prefix"]:
            lines.append(
                f"| (unrecognised prefix) | {stats['europepmc_unknown_prefix']} |"
            )
        lines.append("")

    lines.append("## Publication year")
    lines.append("")
    lines.append("| year | records |")
    lines.append("| --- | ---: |")
    for year in range(YEAR_MIN, YEAR_MAX + 1):
        lines.append(f"| {year} | {stats['year_counts'][year]} |")
    lines.append(f"| year absent (null) | {stats['year_missing']} |")
    lines.append(
        f"| year outside {YEAR_MIN}-{YEAR_MAX} | {stats['year_outside_range']} |"
    )
    lines.append("")
    lines.append(
        "Records with no year are counted on their own row, never folded into a "
        "year bucket and never dropped: the rows above sum to "
        f"{total}."
    )
    lines.append("")

    lines.append("## Journals")
    lines.append("")
    lines.append(
        f"Distinct journals: **{stats['distinct_journals']}**. "
        f"Records with no journal recorded: **{stats['journal_missing']}**."
    )
    lines.append("")
    lines.append(f"Top {TOP_JOURNALS} journals by record count:")
    lines.append("")
    lines.append("| # | journal | records |")
    lines.append("| ---: | --- | ---: |")
    for rank, (journal, count) in enumerate(stats["top_journals"], start=1):
        lines.append(f"| {rank} | {journal} | {count} |")
    lines.append("")

    lines.append("## Abstract availability")
    lines.append("")
    lines.append(
        f"Records with an abstract: **{stats['with_abstract']} / {total} "
        f"({stats['with_abstract_pct']}%)**."
    )
    lines.append("")
    if stats["abstract_length_median"] is None:
        lines.append("No abstract lengths to summarise: no record carries an abstract.")
    else:
        lines.append(
            "Abstract length in characters, over the "
            f"{stats['abstract_length_n']} records that HAVE one (records with a "
            "null abstract are excluded from these statistics, not counted as "
            "zero-length):"
        )
        lines.append("")
        lines.append("| statistic | characters |")
        lines.append("| --- | ---: |")
        lines.append(f"| median | {stats['abstract_length_median']} |")
        lines.append(f"| Q1 | {stats['abstract_length_q1']} |")
        lines.append(f"| Q3 | {stats['abstract_length_q3']} |")
        lines.append(f"| IQR | {stats['abstract_length_iqr']} |")
        lines.append("")
        lines.append(
            "Quartiles use Tukey's method (the median is excluded from both "
            "halves when n is odd), computed by sorting and indexing."
        )
    lines.append("")

    lines.append("## Identifier availability")
    lines.append("")
    lines.append("| identifier | records | % |")
    lines.append("| --- | ---: | ---: |")
    lines.append(f"| DOI | {stats['with_doi']} | {stats['with_doi_pct']} |")
    lines.append(f"| PMID | {stats['with_pmid']} | {stats['with_pmid_pct']} |")
    lines.append("")

    lines.append("## Deduplication")
    lines.append("")
    lines.append(
        "`dedup_rule` records the rule under which a record absorbed at least "
        "one duplicate; `unique` means it absorbed none."
    )
    lines.append("")
    lines.append("| dedup_rule | records |")
    lines.append("| --- | ---: |")
    for rule, count in sorted(
        stats["dedup_rule_counts"].items(), key=lambda kv: -kv[1]
    ):
        lines.append(f"| {rule} | {count} |")
    lines.append("")
    lines.append(
        f"Records built from more than one retrieved record "
        f"(`len(merged_from) > 1`): **{stats['merged_multi']}**."
    )
    lines.append("")

    lines.append(NOT_FINDINGS)
    lines.append("")
    return "\n".join(lines)


def describe(corpus_path: pathlib.Path, output_path: pathlib.Path) -> dict[str, Any]:
    """Describe a retrieved corpus and write the markdown report."""
    corpus_path = pathlib.Path(corpus_path)
    output_path = pathlib.Path(output_path)

    records = _load(corpus_path)
    stats = _summarise(records)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render(stats, corpus_path), encoding="utf-8")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Describe a retrieved corpus (pre-screening, not findings)"
    )
    parser.add_argument("--corpus", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    stats = describe(args.corpus, args.output)
    for key in (
        "total", "by_source_db", "by_europepmc_prefix", "with_abstract",
        "with_abstract_pct", "abstract_length_median", "abstract_length_q1",
        "abstract_length_q3", "with_doi", "with_doi_pct", "with_pmid",
        "with_pmid_pct", "distinct_journals", "year_missing",
        "year_outside_range", "dedup_rule_counts", "merged_multi",
    ):
        print(f"{key}: {stats[key]}")


if __name__ == "__main__":
    main()
