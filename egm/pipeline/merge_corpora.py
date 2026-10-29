"""Merge the PubMed and Europe PMC corpora into one deduplicated corpus.

Run:
    python -m pipeline.merge_corpora \\
        --pubmed search/raw/pubmed_corpus_with_abstracts.json \\
        --europepmc search/raw/europepmc_corpus.json \\
        --output search/raw/combined_corpus.json \\
        --prisma search/prisma_counts_combined.csv

The PubMed artefact holds `DedupedRecord`s (it has already been through one
dedup pass). Those are projected back down to `SearchRecord`s -- by selecting
the `SearchRecord` field names explicitly, never by deleting the known extras,
so a field added to `DedupedRecord` later cannot leak silently into the union.

Concatenation order is load-bearing. `deduplicate()` keeps the FIRST record of
a merged group as the survivor, so PubMed records go first: when a preprint and
its published version collapse, the peer-reviewed MEDLINE record is the one
that survives, carrying its journal and final title.

Record ids are renumbered across the union (egm-000001..egm-00000N). That is
safe only because nothing has been screened yet and no downstream artefact
references a record id; once screening decisions exist, renumbering would
orphan them.

PRISMA structure
----------------
`PrismaFlow.validate()` enforces a strict linear carry-forward: each stage's
`identified` must equal the previous stage's `included`. A two-source merge is
not linear -- the Europe PMC arm ADDS records at the join -- so no single chain
of stages can express it without inventing a number. Rather than fudge one,
TWO flows are built and BOTH validated:

    flow "pubmed"    identification_pubmed     9089 - 1 = 9088
    flow "combined"  identification_combined   9978 - N = final

The bridge between them is stated in the combined stage's own reason text
(PubMed survivors + Europe PMC retrieved = the union identified), so a reader
can reconcile 9088 + 890 = 9978 from the CSV alone. Both flows are written to
one CSV with a leading `flow` column naming which flow each row belongs to.

The PubMed stage numbers are read from the PubMed run's own
`search/prisma_counts.csv` (found next to the corpus artefact), not hardcoded,
and cross-checked against the record count actually present in the artefact.

Note that `PrismaFlow.validate()` refuses a flow with zero exclusions. If the
combined stage ever removed nothing at all, this module fails loudly rather
than writing a merge that silently deduplicated nothing.

Ordering note: both flows are validated BEFORE anything touches disk, and the
PRISMA CSV is written only after the (append-only) corpus artefact, so a
refused run leaves nothing behind to clean up.
"""
import argparse
import csv
import json
import pathlib
from typing import Any

from pipeline.dedup import deduplicate
from pipeline.integrity import IntegrityError
from pipeline.prisma import PrismaFlow, PrismaStage
from pipeline.provenance import RunManifest, write_artefact
from pipeline.schema import SearchRecord

PRISMA_FIELDNAMES = ["flow", "stage", "identified", "excluded", "included", "reason"]


def to_search_record(record: dict[str, Any]) -> SearchRecord:
    """Project a record dict onto exactly the `SearchRecord` fields.

    Selecting `SearchRecord.model_fields` explicitly means any extra key --
    `record_id`, `merged_from`, `dedup_rule`, or a field a future schema change
    adds -- is simply not carried over. Deleting known keys instead would let
    a new field through unnoticed. A MISSING field still fails loudly, because
    `SearchRecord` has no defaults.
    """
    missing = [name for name in SearchRecord.model_fields if name not in record]
    if missing:
        raise IntegrityError(
            f"record {record.get('source_id')!r} is missing required "
            f"SearchRecord fields: {missing}"
        )
    return SearchRecord(**{name: record[name] for name in SearchRecord.model_fields})


def _load(path: pathlib.Path) -> list[dict[str, Any]]:
    payload = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    records = payload.get("records")
    if records is None:
        raise IntegrityError(f"{path} has no 'records' key; not a corpus artefact")
    return records


def _pubmed_identification_stage(
    pubmed_path: pathlib.Path, survivors: int
) -> PrismaStage:
    """Read the PubMed identification numbers from that run's own PRISMA CSV.

    The CSV lives next to the corpus artefact (`search/prisma_counts.csv` for
    `search/raw/<corpus>.json`). Its final `included` must equal the number of
    records actually in the artefact, or the two disagree about what happened.
    """
    prisma_path = pathlib.Path(pubmed_path).parent.parent / "prisma_counts.csv"
    if not prisma_path.exists():
        raise IntegrityError(
            f"no PubMed PRISMA counts at {prisma_path}; the identification "
            "numbers for the PubMed arm cannot be stated without inventing them"
        )

    with prisma_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise IntegrityError(f"{prisma_path} has no stages")

    identified = int(rows[0]["identified"])
    excluded = sum(int(row["excluded"]) for row in rows)
    included = int(rows[-1]["included"])
    if identified - excluded != included:
        raise IntegrityError(
            f"{prisma_path} does not reconcile: {identified} - {excluded} != {included}"
        )
    if included != survivors:
        raise IntegrityError(
            f"{prisma_path} ends at {included} included but the PubMed artefact "
            f"holds {survivors} records"
        )

    reasons = "; ".join(
        row["reason"].strip() for row in rows if int(row["excluded"]) > 0
    )
    return PrismaStage(
        name="identification_pubmed",
        identified=identified,
        excluded=excluded,
        reason=f"PubMed-internal duplicates removed before the merge: {reasons}",
    )


def _write_prisma(
    path: pathlib.Path, flows: list[tuple[str, PrismaFlow]]
) -> None:
    """Write several validated flows into one CSV, tagged by flow name."""
    for _, flow in flows:
        flow.validate()
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(PRISMA_FIELDNAMES)
        for flow_name, flow in flows:
            for stage in flow.stages:
                writer.writerow([
                    flow_name, stage.name, stage.identified, stage.excluded,
                    stage.included, stage.reason,
                ])


def merge(
    pubmed_path: pathlib.Path,
    europepmc_path: pathlib.Path,
    output_path: pathlib.Path,
    prisma_path: pathlib.Path,
) -> dict[str, int]:
    """Deduplicate the union of the two corpora and persist it."""
    pubmed_path = pathlib.Path(pubmed_path)
    europepmc_path = pathlib.Path(europepmc_path)
    output_path = pathlib.Path(output_path)
    prisma_path = pathlib.Path(prisma_path)

    if prisma_path.exists():
        raise FileExistsError(
            f"{prisma_path} exists; PRISMA counts are append-only, write to a new path"
        )

    pubmed_raw = _load(pubmed_path)
    europepmc_raw = _load(europepmc_path)

    # PubMed FIRST: deduplicate() keeps the first record of a merged group.
    union = (
        [to_search_record(record) for record in pubmed_raw]
        + [to_search_record(record) for record in europepmc_raw]
    )
    deduped, counts = deduplicate(union)

    pubmed_stage = _pubmed_identification_stage(pubmed_path, len(pubmed_raw))
    flow_pubmed = PrismaFlow(stages=[pubmed_stage])
    flow_combined = PrismaFlow(stages=[
        PrismaStage(
            name="identification_combined",
            identified=len(union),
            excluded=counts["removed_total"],
            reason=(
                f"union = identification_pubmed included ({pubmed_stage.included}) "
                f"+ Europe PMC retrieved ({len(europepmc_raw)}) = {len(union)}; "
                f"cross-source duplicates removed (doi={counts['removed_doi']}, "
                f"pmid={counts['removed_pmid']}, fuzzy={counts['removed_fuzzy']})"
            ),
        )
    ])
    # Validate BEFORE writing anything to disk.
    flow_pubmed.validate()
    flow_combined.validate()

    notes = (
        f"combined corpus: {pubmed_path.name} ({len(pubmed_raw)} records, already "
        f"deduplicated within PubMed) + {europepmc_path.name} "
        f"({len(europepmc_raw)} records); union={len(union)}; "
        f"cross-source dedup rules: {counts}; "
        "Europe PMC was searched with `NOT SRC:MED`, so it contributes only "
        "coverage beyond MEDLINE (preprints, PMC-only, theses, agricola) and "
        "no MEDLINE record is imported twice. Record ids are renumbered across "
        "the union; this is safe only because no screening has occurred and no "
        "artefact references the previous ids."
    )
    write_artefact(
        output_path,
        [record.model_dump() for record in deduped],
        RunManifest.create(
            query_string=f"merge of {pubmed_path.name} + {europepmc_path.name}",
            source_db="combined",
            record_count=len(deduped),
            notes=notes,
        ),
    )

    _write_prisma(
        prisma_path, [("pubmed", flow_pubmed), ("combined", flow_combined)]
    )

    return {
        "pubmed_records": len(pubmed_raw),
        "europepmc_records": len(europepmc_raw),
        "union": len(union),
        "removed_doi": counts["removed_doi"],
        "removed_pmid": counts["removed_pmid"],
        "removed_fuzzy": counts["removed_fuzzy"],
        "removed_total": counts["removed_total"],
        "output": counts["output"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge the PubMed and Europe PMC corpora"
    )
    parser.add_argument("--pubmed", type=pathlib.Path, required=True)
    parser.add_argument("--europepmc", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--prisma", type=pathlib.Path, required=True)
    args = parser.parse_args()

    counts = merge(args.pubmed, args.europepmc, args.output, args.prisma)
    for key, value in counts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
