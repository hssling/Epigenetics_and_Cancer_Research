"""Backfill abstracts into an existing corpus artefact.

The corpus is retrieved via esummary, which returns bibliographic metadata but
never abstracts, so every record arrives with `abstract: None`. Title-only
screening has materially worse recall than title-and-abstract screening, so the
registered protocol requires this backfill before screening begins.

Raw exports are append-only. This writes a NEW artefact rather than modifying
the one it reads.

Run:
    python -m pipeline.backfill_abstracts \\
        --corpus search/raw/pubmed_corpus.json \\
        --output search/raw/pubmed_corpus_with_abstracts.json
"""
import argparse
import json
import pathlib
from typing import Optional

from pipeline import pubmed
from pipeline.integrity import IntegrityError
from pipeline.provenance import RunManifest, write_artefact
from pipeline.schema import DedupedRecord

# Above this share of records lacking an abstract, the likeliest explanation is
# a parsing fault rather than genuine absence, so the run fails rather than
# writing a corpus that would silently be screened on titles alone.
MAX_MISSING_ABSTRACT_SHARE = 0.20


def backfill(
    corpus_path: pathlib.Path,
    output_path: pathlib.Path,
    batch_size: int = 200,
) -> dict[str, int]:
    """Fetch abstracts for a corpus and write a new artefact carrying them."""
    corpus_path = pathlib.Path(corpus_path)
    output_path = pathlib.Path(output_path)

    payload = json.loads(corpus_path.read_text(encoding="utf-8"))
    records = payload["records"]

    pmids = [r["pmid"] for r in records if r.get("pmid")]
    if len(pmids) != len(records):
        raise IntegrityError(
            f"{len(records) - len(pmids)} of {len(records)} records have no PMID; "
            "abstracts cannot be retrieved for them"
        )

    abstracts: dict[str, Optional[str]] = pubmed.fetch_abstracts(
        pmids, batch_size=batch_size
    )

    updated: list[dict] = []
    without_abstract = 0
    for record in records:
        abstract = abstracts.get(record["pmid"])
        if abstract is None:
            without_abstract += 1
        # Round-trip through the schema so a malformed record fails here
        # rather than downstream.
        updated.append(DedupedRecord(**{**record, "abstract": abstract}).model_dump())

    share = without_abstract / len(records) if records else 0.0
    if share > MAX_MISSING_ABSTRACT_SHARE:
        raise IntegrityError(
            f"{without_abstract} of {len(records)} records "
            f"({share:.0%}) have no abstract, above the "
            f"{MAX_MISSING_ABSTRACT_SHARE:.0%} threshold. Genuine absence is a "
            "minority; a share this high indicates a parsing fault. No artefact "
            "was written."
        )

    with_abstract = len(records) - without_abstract
    write_artefact(
        output_path,
        updated,
        RunManifest.create(
            query_string=f"efetch abstract backfill of {corpus_path.name}",
            source_db="pubmed",
            record_count=len(updated),
            notes=(
                f"abstract backfill via efetch; source={corpus_path.name}; "
                f"with_abstract={with_abstract}; without_abstract={without_abstract} "
                f"({share:.1%}). Records without an abstract carry null, not an "
                "empty string: many PubMed records legitimately have none."
            ),
        ),
    )

    return {
        "records": len(records),
        "with_abstract": with_abstract,
        "without_abstract": without_abstract,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill abstracts into a corpus")
    parser.add_argument("--corpus", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--batch-size", type=int, default=200)
    args = parser.parse_args()

    counts = backfill(args.corpus, args.output, args.batch_size)
    for key, value in counts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
