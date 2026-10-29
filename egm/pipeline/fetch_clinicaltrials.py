"""Fetch the ClinicalTrials.gov registry stream (registered protocol Section 4.1).

This is a SEPARATE PRISMA identification stream. Registry records do not join
the 9,786-record screening corpus and must not be merged into it: a
registration is not a publication, and a trial that was registered and never
published is the absence of evidence, not evidence. PRISMA 2020 gives registers
their own column for this reason.

WHO ICTRP, the other registry the protocol names, is not fetched here. Its
web service operates on an agreed-partner basis and its portal export is an
interactive step requiring acceptance of WHO's terms, so neither is callable
unattended. It remains an outstanding manual step, recorded as an amendment.

Raw exports are append-only: write_artefact refuses to overwrite.

Run:
    python -m pipeline.fetch_clinicaltrials --output search/raw/ctgov_registry.json
"""
import argparse
import pathlib

from pipeline import clinicaltrials
from pipeline.provenance import RunManifest, query_hash, write_artefact

STREAM_NOTE = (
    "ClinicalTrials.gov API v2, no credential of any kind. This is a registry "
    "stream under protocol Section 4.1, kept separate from the bibliographic "
    "corpus: registrations identify unpublished and ongoing studies and "
    "populate the 'registered but unreported' overlay, and merging them into "
    "the screening corpus would let an unpublished trial be counted as "
    "evidence. The registered PubMed strategy was translated clause by clause "
    "-- HUMAN and DESIGN dropped as vacuous in a registry of human studies, "
    "the [tiab] restriction kept as AREA[BriefTitle]/AREA[BriefSummary] "
    "(without it the core block returns 1,771 rather than 694), and the "
    "exposure/clinical-use block dropped because those concepts live in "
    "structured intervention and outcome fields rather than summary prose. "
    "See pipeline/clinicaltrials.py for the measured counts behind each "
    "decision. WHO ICTRP remains unsearched: no endpoint callable unattended; it is outstanding as a manual step, not impossible."
)


def fetch(output_path: pathlib.Path) -> dict[str, int]:
    """Retrieve the registry stream and write a raw artefact."""
    output_path = pathlib.Path(output_path)

    query_string = clinicaltrials.build_registry_query()
    total = clinicaltrials.count(query_string)

    records = clinicaltrials.search_records(
        query_string, query_hash_value=query_hash(query_string)
    )

    # The registry is a live index; totalCount is read before paging and the
    # drift between the two is real, so it is recorded rather than smoothed.
    drift = len(records) - total

    completed = sum(1 for r in records if r.status == "COMPLETED")
    with_posted_results = sum(1 for r in records if r.has_results)
    with_publication = sum(1 for r in records if r.result_pmids)
    # The overlay's candidate population: finished, with an ACTUAL completion
    # date, and no results posted and no linked result publication. This is a
    # count of candidates, not a finding -- whether each is genuinely unreported
    # is decided later, against the bibliographic corpus.
    unreported_candidates = sum(
        1 for r in records
        if r.status == "COMPLETED"
        and r.completion_is_actual is True
        and not r.has_results
        and not r.result_pmids
    )
    by_type: dict[str, int] = {}
    for record in records:
        key = record.study_type or "unstated"
        by_type[key] = by_type.get(key, 0) + 1

    notes = (
        f"{STREAM_NOTE} totalCount at count()={total}; records retrieved="
        f"{len(records)} (drift={drift:+d}). Study types: "
        + "; ".join(f"{k}={v}" for k, v in sorted(by_type.items()))
        + f". Completed={completed}; registry results posted={with_posted_results}; "
        f"linked result publication={with_publication}; "
        f"unreported-overlay candidates={unreported_candidates} (candidates "
        "only -- confirmation is against the bibliographic corpus, not this file)."
    )

    write_artefact(
        output_path,
        [record.model_dump() for record in records],
        RunManifest.create(
            query_string=query_string,
            source_db="ctgov",
            record_count=len(records),
            notes=notes,
        ),
    )

    counts = {
        "total_count": total,
        "records_retrieved": len(records),
        "drift": drift,
        "completed": completed,
        "results_posted_to_registry": with_posted_results,
        "linked_result_publication": with_publication,
        "unreported_overlay_candidates": unreported_candidates,
    }
    counts.update({f"type_{k.lower()}": v for k, v in sorted(by_type.items())})
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch the ClinicalTrials.gov registry stream"
    )
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    for key, value in fetch(args.output).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
