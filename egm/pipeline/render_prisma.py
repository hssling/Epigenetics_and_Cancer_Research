"""Render the PRISMA flow document from the committed count artefacts.

Nothing here is transcribed. Identification and deduplication counts are read
from the PRISMA CSVs; the screening row is obtained by calling
`report_screening.screening_stage`, which means the figure is produced through
the screening gate rather than alongside it.

That is the point. A PRISMA diagram is the one figure a reader trusts on sight,
and it is exactly where an ungated number would do the most damage. If the gate
is closed, this renders the screening row as withheld and says why; it cannot
render a screening count the investigator has not validated, because it never
sees one. (The gate was kappa until Amendment 7; it is now recall validation.)
"""
import argparse
import csv
import json
import pathlib
from typing import Optional

from pipeline.report_screening import GateNotPassed, screening_stage
from pipeline.screen_schema import read_decisions


def _read_flow(path: pathlib.Path) -> list[dict[str, str]]:
    with pathlib.Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _merge_note(corpus_path: Optional[pathlib.Path]) -> str:
    """Describe the merges from the corpus itself, not from a remembered figure.

    An earlier hand-written draft of this line said "all 192 cross-source merges
    were inspected". 192 is the number of records REMOVED; only 184 of the 190
    merge groups were cross-source, the other 6 being within Europe PMC. Deriving
    it here means the sentence cannot drift from the artefact it describes.
    """
    if corpus_path is None or not pathlib.Path(corpus_path).exists():
        return (
            "Per-merge provenance is recorded in each surviving record's "
            "`merged_from` field and is auditable record by record."
        )
    records = json.loads(pathlib.Path(corpus_path).read_text(encoding="utf-8"))["records"]
    groups = [r for r in records if len(r["merged_from"]) > 1]
    cross = sum(
        1 for r in groups
        if len({m.split(":", 1)[0] for m in r["merged_from"]}) > 1
    )
    removed = sum(len(r["merged_from"]) - 1 for r in groups)
    return (
        f"{removed:,} records were removed across {len(groups):,} merge groups, of "
        f"which {cross:,} joined records from different databases and "
        f"{len(groups) - cross:,} were within a single database. Every "
        f"cross-source merge was inspected; the non-exact title matches differ "
        f"only by casing, dash style, an added word, or a conference-abstract "
        f"prefix. Each surviving record carries its `merged_from` provenance, so "
        f"any merge can be audited individually."
    )



def _registry_block(registry_path: Optional[pathlib.Path]) -> str:
    """Describe the register stream from its artefact, or say it is absent.

    PRISMA 2020 counts registers in their own identification column, separate
    from databases. The separation is not cosmetic here: a registration is not
    a publication, and a trial registered but never published is the ABSENCE of
    evidence. Folding these into the bibliographic corpus would let it be
    counted as evidence -- the exact inversion the registry stream exists to
    expose.

    Only identification counts appear here. The "registered but unreported"
    overlay is a finding about the evidence base, it needs the bibliographic
    corpus to confirm, and findings wait for the screening gate like every other.
    """
    if registry_path is None or not pathlib.Path(registry_path).exists():
        return (
            "### Identification from registers\n"
            "\n"
            "**Not searched.** Protocol Section 4.1 commits to ClinicalTrials.gov\n"
            "and WHO ICTRP; neither has been run.\n"
        )

    payload = json.loads(pathlib.Path(registry_path).read_text(encoding="utf-8"))
    records = payload["records"]
    by_type: dict[str, int] = {}
    for record in records:
        key = (record.get("study_type") or "unstated").lower()
        by_type[key] = by_type.get(key, 0) + 1
    rows = "\n".join(f"| {k} | {v:,} |" for k, v in sorted(by_type.items()))

    return (
        "### Identification from registers\n"
        "\n"
        "| register | n |\n"
        "|---|---:|\n"
        f"| ClinicalTrials.gov | {len(records):,} |\n"
        "| WHO ICTRP | not searched |\n"
        "\n"
        f"| study type | n |\n"
        "|---|---:|\n"
        f"{rows}\n"
        "\n"
        "These registrations are a separate identification stream under protocol\n"
        "Section 4.1 and are **not** part of the screening corpus counted above.\n"
        "A registration is not a publication: merging the streams would let a\n"
        "trial that was registered and never published count as evidence. WHO\n"
        "ICTRP was not searched: it has no endpoint callable unattended, and\n"
        "remains an outstanding manual step. See `protocol/amendments.md`,\n"
        "Amendment 6.\n"
    )


def _screening_block(
    decisions_path: pathlib.Path,
    validation_path: pathlib.Path,
    sample_path: pathlib.Path,
    identified: int,
    extension_path: Optional[pathlib.Path] = None,
) -> tuple[str, Optional[dict]]:
    """Return (markdown, summary). Summary is None when the gate is closed."""
    try:
        _, summary = screening_stage(
            decisions_path, validation_path, sample_path, identified,
            extension_path=extension_path,
        )
    except GateNotPassed as exc:
        # Do not assert coverage that has not been checked. An audit found
        # this block claiming "every one has a recorded decision" for a record
        # count read from a stale CSV, against a log covering a different set.
        decided = len({
            d.record_id for d in read_decisions(decisions_path)
            if d.stage == "screening"
        })
        if decided == identified:
            coverage = (
                f"{identified:,} records entered title/abstract screening. "
                "Every one has a recorded decision."
            )
        else:
            coverage = (
                f"{identified:,} records entered title/abstract screening; the "
                f"decision log covers {decided:,} of them. **These do not "
                "match** — the counts below would be wrong even if the gate "
                "were open, and the discrepancy must be resolved before either "
                "number is used."
            )
        return (
            "### Screening — counts WITHHELD\n\n"
            f"{coverage}\n\n"
            "**The counts are not shown here, and that is deliberate.** Under "
            "Amendment 7 (OSF, 2026-10-29) the screening counts are reportable "
            "once the investigator has screened 200 AI exclusions blind and the "
            "recall estimate has been computed from that log. That has not "
            "happened:\n\n"
            f"> {exc}\n\n"
            "This document is generated by calling the same gated function the "
            "manuscript would call. It has no path to a screening count that has "
            "not passed the gate, so a closed gate cannot be worked around by "
            "regenerating the figure. The decisions exist and are auditable in "
            "`screening/screening_decisions_sonnet.jsonl`; they are provisional "
            "until validated.\n",
            None,
        )
    return (
        "### Screening — title/abstract\n\n"
        f"| | n |\n|---|---:|\n"
        f"| entered screening | {summary['identified']:,} |\n"
        f"| excluded | {summary['exclude']:,} |\n"
        f"| routed to human (`unclear`) | {summary['unclear']:,} |\n"
        f"| **retained for full text** | **{summary['include']:,}** |\n\n"
        f"Recall validated on {summary['recall_n']} AI exclusions screened "
        f"blind by the investigator: {summary['recall_false_negatives']} false "
        f"negative(s); stratum-weighted false-negative rate "
        f"{summary['recall_weighted_fn_rate']:.2%} (95% CI "
        f"{summary['recall_weighted_fn_rate_ci_low']:.2%} to "
        f"{summary['recall_weighted_fn_rate_ci_high']:.2%}), up to "
        f"{summary['recall_implied_missed_high']:.0f} eligible studies "
        f"plausibly missed. Not calibrated against a human reviewer "
        f"(Amendment 7). Model `{summary['model_id']}`; instrument "
        f"`{summary['prompt_sha256'][:12]}`.\n\n"
        "Exclusion criteria: "
        + ", ".join(f"{k} {v:,}" for k, v in sorted(summary["criteria"].items()))
        + "\n",
        summary,
    )


def render(
    identification_csv: pathlib.Path,
    decisions_path: pathlib.Path,
    validation_path: pathlib.Path,
    sample_path: pathlib.Path,
    out_path: pathlib.Path,
    corpus_path: Optional[pathlib.Path] = None,
    registry_path: Optional[pathlib.Path] = None,
    extension_path: Optional[pathlib.Path] = None,
) -> bool:
    """Write the flow document. Returns True if the screening counts were shown."""
    rows = _read_flow(identification_csv)
    by_flow = {r["flow"]: r for r in rows}
    pubmed = by_flow["pubmed"]
    combined = by_flow["combined"]

    identified_pubmed = int(pubmed["identified"])
    pubmed_dupes = int(pubmed["excluded"])
    after_pubmed = int(pubmed["included"])
    union = int(combined["identified"])
    cross_dupes = int(combined["excluded"])
    corpus = int(combined["included"])
    europepmc = union - after_pubmed

    merge_note = _merge_note(corpus_path)
    registry_md = _registry_block(registry_path)
    screening_md, summary = _screening_block(
        decisions_path, validation_path, sample_path, corpus, extension_path
    )

    body = f"""# PRISMA 2020 flow

Generated by `pipeline/render_prisma.py` from the committed count artefacts.
No number in this document was typed by hand: identification and deduplication
are read from `{identification_csv.name}`, and the screening row is produced by
the same gated function the manuscript calls.

Registration: OSF Registries [3xtf2](https://osf.io/3xtf2) · DOI
[10.17605/OSF.IO/3XTF2](https://doi.org/10.17605/OSF.IO/3XTF2).
Search reporting against all sixteen PRISMA-S items:
`PRISMA_S_search_report.md`.

---

## Identification

| source | n |
|---|---:|
| PubMed/MEDLINE | {identified_pubmed:,} |
| Europe PMC (`NOT SRC:MED`) | {europepmc:,} |
| **total identified** | **{identified_pubmed + europepmc:,}** |

(The deduplication table below starts from {union:,}, which is this total after
the one PubMed-internal duplicate has already been removed.)

Embase, Web of Science and Cochrane CENTRAL were **not searched** — no
institutional access. ClinicalTrials.gov was searched as a separate
register stream (below); WHO ICTRP remains outstanding. See
`protocol/amendments.md`, Amendment 1; the coverage cost is carried in
`METHODS.md` Section 11 rather than offset by a claim of equivalence.

## Deduplication

| step | identified | removed | remaining |
|---|---:|---:|---:|
| PubMed-internal | {identified_pubmed:,} | {pubmed_dupes:,} | {after_pubmed:,} |
| union with Europe PMC | {union:,} | {cross_dupes:,} | **{corpus:,}** |

Deduplication by exact normalised DOI, then PMID, then fuzzy title (rapidfuzz
>= 95) requiring an identical first-author surname and a compatible publication
year. Records that both carry an identifier and disagree on it are not merged —
except for preprint pairs, which always disagree on DOI by construction
(Amendment 2).

{merge_note}

{registry_md}
{screening_md}
---

## Flow

```mermaid
flowchart TD
    A["PubMed/MEDLINE<br/>n = {identified_pubmed:,}"] --> C
    B["Europe PMC, NOT SRC:MED<br/>n = {europepmc:,}"] --> C
    C["Records identified<br/>n = {identified_pubmed + europepmc:,}"] --> D
    D["Duplicates removed<br/>n = {pubmed_dupes + cross_dupes:,}"] --> E
    E["Records screened<br/>n = {corpus:,}"] --> F
    F["{'Title/abstract screening' if summary else 'Title/abstract screening COMPLETE<br/>counts withheld: recall validation not done'}"]
```

## What this diagram does not yet show

Full-text screening, eligibility, and included studies are absent because
those stages have not run. A PRISMA diagram is normally read as a completed
account of a finished review; this one is a partial flow for a review in
progress, and is labelled as such rather than padded to look complete.

See `STATUS.md` for the full list of what has and has not been done.
"""
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body, encoding="utf-8")
    return summary is not None


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the PRISMA flow document")
    parser.add_argument("--identification", type=pathlib.Path, required=True)
    parser.add_argument("--decisions", type=pathlib.Path, required=True)
    parser.add_argument("--validation", type=pathlib.Path, required=True)
    parser.add_argument("--sample", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--corpus", type=pathlib.Path, default=None)
    parser.add_argument("--registry", type=pathlib.Path, default=None)
    parser.add_argument("--extension", type=pathlib.Path, default=None)
    args = parser.parse_args()

    shown = render(
        args.identification, args.decisions, args.validation, args.sample,
        args.out,
        args.corpus, args.registry, args.extension,
    )
    print(f"wrote {args.out}")
    print("screening counts: " + ("SHOWN (recall validated)" if shown else "WITHHELD (gate closed)"))


if __name__ == "__main__":
    main()
