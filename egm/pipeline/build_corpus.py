"""End-to-end corpus build: search -> fetch -> deduplicate -> artefacts.

Run:
    python -m pipeline.build_corpus --output egm/search --retmax 10000
    python -m pipeline.build_corpus --output egm/search --dry-run

Ordering note: validation happens BEFORE anything touches disk. `flow.validate()`
is called explicitly right after deduplication, ahead of `write_artefact(...)`.
If it were called after the raw artefact was written, a zero-exclusion defect
would raise IntegrityError only after the (append-only) raw export already
existed on disk -- so a retry would then also hit FileExistsError, requiring
manual cleanup before the run could be repeated. Validating first means a
failed run leaves nothing behind to clean up.
"""
import argparse
import pathlib

from pipeline import pubmed
from pipeline.dedup import deduplicate
from pipeline.integrity import IntegrityError
from pipeline.prisma import PrismaFlow, PrismaStage
from pipeline.provenance import RunManifest, query_hash, write_artefact
from pipeline.query import build_pubmed_query


def build_corpus(output_dir: pathlib.Path, retmax: int, dry_run: bool) -> dict[str, int]:
    """Retrieve, deduplicate and persist the PubMed corpus."""
    output_dir = pathlib.Path(output_dir)
    query_string = build_pubmed_query(include_ncrna=False, date_limited=True)

    if dry_run:
        return {"available": pubmed.count(query_string)}

    # NCBI caps esearch retmax at 10,000. If more records are available than
    # retmax allows, the corpus would be silently truncated with no signal
    # anywhere in the artefacts -- so check BEFORE searching, not after.
    available = pubmed.count(query_string)
    if available > retmax:
        raise IntegrityError(
            f"{available} records available for this query but retmax={retmax}; "
            "the corpus would be silently truncated. Raise --retmax or narrow the query."
        )

    pmids = pubmed.search(query_string, retmax=retmax)
    expected = min(available, retmax)
    if len(pmids) != expected:
        raise IntegrityError(
            f"esearch returned {len(pmids)} pmids but expected {expected} "
            f"(available={available}, retmax={retmax})"
        )

    records = pubmed.fetch_summaries(pmids, query_hash_value=query_hash(query_string))
    deduped, counts = deduplicate(records)

    # Construct and validate the PRISMA flow BEFORE writing anything to disk.
    # validate() raises if nothing was excluded — see DEPRECATED.md for why.
    flow = PrismaFlow(stages=[
        PrismaStage(
            name="identification",
            identified=counts["input"],
            excluded=counts["removed_total"],
            reason=(
                f"duplicates removed (doi={counts['removed_doi']}, "
                f"pmid={counts['removed_pmid']}, fuzzy={counts['removed_fuzzy']})"
            ),
        )
    ])
    flow.validate()

    notes = (
        f"available={available}; retmax={retmax}; dedup rules: {counts}; "
        "abstracts: all null -- esummary.fcgi does not return abstract text; "
        "this corpus is NOT yet screened-ready for title/abstract screening "
        "until abstracts are backfilled via an efetch call keyed on pmid."
    )
    write_artefact(
        output_dir / "raw" / "pubmed_corpus.json",
        [record.model_dump() for record in deduped],
        RunManifest.create(
            query_string=query_string,
            source_db="pubmed",
            record_count=len(deduped),
            notes=notes,
        ),
    )

    flow.to_csv(output_dir / "prisma_counts.csv")

    (output_dir / "query_executed.txt").write_text(query_string, encoding="utf-8")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the EGM PubMed corpus")
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--retmax", type=int, default=10000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    counts = build_corpus(args.output, args.retmax, args.dry_run)
    for key, value in counts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
