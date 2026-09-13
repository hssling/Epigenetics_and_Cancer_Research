"""Fetch the Europe PMC corpus (the recorded substitution for Embase).

The registered protocol (OSF 3xtf2) lists Embase, to which the investigator has
no access. protocol/amendments.md records Europe PMC as the substitution, on the
basis that it adds coverage BEYOND MEDLINE -- preprints, PMC-only content,
theses, agricola. PubMed/MEDLINE was already searched natively on 2026-09-13
(9,088 deduplicated records).

The search is therefore restricted to `NOT SRC:MED` by default. `--include-medline`
exists only so the all-sources denominator can be reproduced for the count
verification record; it must NOT be used to build the screening corpus, because
Europe PMC's query syntax cannot express the `[pt]` and `[MeSH]` filters the
registered PubMed strategy used, so those records would enter on looser criteria
than the ones registered.

Raw exports are append-only: write_artefact refuses to overwrite.

Run:
    python -m pipeline.fetch_europepmc --output search/raw/europepmc_corpus.json
"""
import argparse
import pathlib

from pipeline import europepmc
from pipeline.provenance import RunManifest, query_hash, write_artefact

SRC_MED_NOTE = (
    "Search restricted with `NOT SRC:MED`. Reason: PubMed/MEDLINE was already "
    "searched natively (2026-09-13, 9,088 deduplicated records) with a precise "
    "field-tagged strategy. Europe PMC is the recorded substitution for Embase "
    "(no institutional access) and is included for the coverage it adds BEYOND "
    "MEDLINE -- preprints (SRC:PPR), PMC-only content (SRC:PMC), theses, "
    "agricola. Fetching MEDLINE records here and deduplicating would import "
    "records the registered PubMed strategy deliberately excluded via [pt] and "
    "[MeSH] filters that Europe PMC's syntax cannot express, silently loosening "
    "a registered strategy."
)

INCLUDE_MED_NOTE = (
    "SRC:MED NOT excluded (--include-medline). This corpus overlaps the native "
    "PubMed search and contains MEDLINE records admitted on looser criteria "
    "than the registered strategy, because Europe PMC cannot express its [pt] "
    "and [MeSH] filters. It is a denominator for count verification, not a "
    "screening corpus."
)


def fetch(output_path: pathlib.Path, include_medline: bool) -> dict[str, int]:
    """Retrieve the Europe PMC corpus and write a raw artefact."""
    output_path = pathlib.Path(output_path)
    exclude_medline = not include_medline

    query_string = europepmc.build_europepmc_query(exclude_medline=exclude_medline)
    hit_count = europepmc.count(query_string)

    records = europepmc.search_records(
        query_string, query_hash_value=query_hash(query_string)
    )

    # Europe PMC is a live index. hitCount is read once before paging and again
    # on every page; a small drift between the two is real, not a defect, so it
    # is recorded rather than silently smoothed over.
    drift = len(records) - hit_count
    with_abstract = sum(1 for r in records if r.abstract is not None)
    by_source: dict[str, int] = {}
    for record in records:
        prefix = record.source_id.split(":", 1)[0]
        by_source[prefix] = by_source.get(prefix, 0) + 1

    breakdown = "; ".join(f"{k}={v}" for k, v in sorted(by_source.items()))
    notes = (
        f"{INCLUDE_MED_NOTE if include_medline else SRC_MED_NOTE} "
        f"hitCount at count()={hit_count}; records retrieved={len(records)} "
        f"(drift={drift:+d}). Source breakdown: {breakdown}. "
        f"with_abstract={with_abstract}; without_abstract={len(records) - with_abstract} "
        "(records without an abstract carry null, not an empty string)."
    )

    write_artefact(
        output_path,
        [record.model_dump() for record in records],
        RunManifest.create(
            query_string=query_string,
            source_db="europepmc",
            record_count=len(records),
            notes=notes,
        ),
    )

    counts = {
        "hit_count": hit_count,
        "records_retrieved": len(records),
        "drift": drift,
        "with_abstract": with_abstract,
        "without_abstract": len(records) - with_abstract,
    }
    counts.update({f"source_{k}": v for k, v in sorted(by_source.items())})
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch the Europe PMC corpus (non-MEDLINE by default)"
    )
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument(
        "--include-medline",
        action="store_true",
        help=(
            "Do NOT append `NOT SRC:MED`. For count verification only: the "
            "resulting corpus duplicates the native PubMed search on looser "
            "criteria than the registered strategy."
        ),
    )
    args = parser.parse_args()

    counts = fetch(args.output, args.include_medline)
    for key, value in counts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
