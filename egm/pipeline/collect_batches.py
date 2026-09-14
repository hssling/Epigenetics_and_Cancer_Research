"""Verify subagent screening decisions and commit them to the decision log.

The integrity gate for the subagent screening path. `pipeline.prepare_batches`
writes what a subagent reads; this module decides whether what came back is
admissible as data.

The specific failure being defended against is silent under-return: a subagent
that answers 94 of 100 records, or answers for a record_id it invented. Neither
leaves a trace anywhere else -- the PRISMA identification count would still
match the corpus, the log would simply be short, and no later stage recomputes
the difference. So coverage is checked explicitly against the batch input, and
a discrepancy raises rather than being reconciled.

Two ordering rules make the checks meaningful:

* every check runs BEFORE the first append. A check that raises after half the
  batch is already in an append-only log is not a check; it is a second way to
  corrupt the log.
* the log is consulted for prior decisions at this stage, so re-running a
  collection cannot double-count a batch.

A failure is never recorded as a decision, mirroring `pipeline.ai_screener`.

Run:
    python -m pipeline.collect_batches --batch batch_0001.json \\
        --decisions batch_0001_decisions.jsonl --log decisions.jsonl \\
        --model-id claude-opus-5
"""
import argparse
import json
import pathlib
from typing import Any

from pipeline.screen_schema import (
    ScreeningDecision,
    append_decision,
    read_decisions,
)

BATCH_GLOB = "batch_[0-9][0-9][0-9][0-9].json"


class CollectionError(Exception):
    """A batch failed verification. Never caught internally."""


def _shown(ids: set[str]) -> list[str]:
    """The first five ids, sorted, for an error message."""
    return sorted(ids)[:5]


def _load_batch(batch_path: pathlib.Path) -> dict[str, Any]:
    batch_path = pathlib.Path(batch_path)
    if not batch_path.exists():
        raise CollectionError(f"batch input {batch_path} does not exist")
    try:
        batch = json.loads(batch_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CollectionError(f"batch input {batch_path} is not valid JSON: {exc}") from exc

    missing = [k for k in ("batch_id", "stage", "prompt_sha256", "records") if k not in batch]
    if missing:
        raise CollectionError(f"batch input {batch_path} is missing {missing}")
    if not batch["records"]:
        raise CollectionError(f"batch input {batch_path} contains no records")
    return batch


def _parse_decisions(decisions_path: pathlib.Path) -> list[ScreeningDecision]:
    """Parse every line. A bad line raises; it is never skipped.

    Skipping an unparseable line would convert a malformed decision into a
    missing one, which the coverage check would then report as a lost record
    with no indication that the model had in fact answered.
    """
    decisions_path = pathlib.Path(decisions_path)
    if not decisions_path.exists():
        raise CollectionError(f"decisions file {decisions_path} does not exist")

    decisions: list[ScreeningDecision] = []
    for number, line in enumerate(
        decisions_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            decisions.append(ScreeningDecision(**json.loads(line)))
        except Exception as exc:  # noqa: BLE001 - re-raised as CollectionError
            raise CollectionError(
                f"{decisions_path}:{number} is not a valid ScreeningDecision: {exc}"
            ) from exc
    if not decisions:
        raise CollectionError(f"decisions file {decisions_path} is empty")
    return decisions


def _check_coverage(
    batch: dict[str, Any], decisions: list[ScreeningDecision], batch_path: pathlib.Path
) -> None:
    expected = {r["record_id"] for r in batch["records"]}
    got = [d.record_id for d in decisions]

    duplicates = {rid for rid in got if got.count(rid) > 1}
    if duplicates:
        raise CollectionError(
            f"{len(duplicates)} record_id(s) have more than one decision in this "
            f"batch: {_shown(duplicates)}; which judgement is the datum cannot be "
            "decided here"
        )

    missing = expected - set(got)
    extra = set(got) - expected

    # Both halves are reported together. A substituted record_id -- the
    # characteristic hallucination -- produces one missing id AND one extra
    # one, and naming only the first of those would hide the fabricated id
    # that explains it.
    faults: list[str] = []
    if missing:
        faults.append(
            f"{len(missing)} decision(s) missing: {_shown(missing)} -- an "
            "unanswered record would be silently dropped from the corpus"
        )
    if extra:
        faults.append(
            f"{len(extra)} decision(s) for records not in this batch: "
            f"{_shown(extra)} -- either a fabricated record_id or a crossed-over "
            "batch"
        )
    if faults:
        raise CollectionError(
            f"coverage check failed for batch {batch['batch_id']} "
            f"({len(expected)} records, {len(got)} decisions, input "
            f"{batch_path}): " + "; ".join(faults)
        )


def _check_provenance(
    batch: dict[str, Any], decisions: list[ScreeningDecision], model_id: str
) -> None:
    """Every decision must trace to this batch's prompt, stage and model.

    Blending decisions made under two prompts or two models into one log makes
    every statistic computed from it a mixture of two experiments, and nothing
    downstream can unmix them.
    """
    for decision in decisions:
        if decision.screener != "ai":
            raise CollectionError(
                f"{decision.record_id}: screener is {decision.screener!r}, "
                "expected 'ai'; a human decision must not be collected through "
                "the subagent path"
            )
        if decision.stage != batch["stage"]:
            raise CollectionError(
                f"{decision.record_id}: stage is {decision.stage!r} but the batch "
                f"is {batch['stage']!r}"
            )
        if decision.prompt_sha256 != batch["prompt_sha256"]:
            raise CollectionError(
                f"{decision.record_id}: prompt_sha256 is {decision.prompt_sha256!r} "
                f"but the batch was prepared against {batch['prompt_sha256']!r}"
            )
        if decision.model_id != model_id:
            raise CollectionError(
                f"{decision.record_id}: model_id is {decision.model_id!r} but this "
                f"collection is for {model_id!r}"
            )


def _check_pmids(batch: dict[str, Any], decisions: list[ScreeningDecision]) -> None:
    """pmid must match the batch record exactly, None included.

    None is legitimate -- Europe PMC preprints have no PMID -- so it is
    compared rather than skipped: a pmid appearing where the batch had none is
    fabricated, and one that differs means the wrong record was read.
    """
    by_id = {r["record_id"]: r["pmid"] for r in batch["records"]}
    for decision in decisions:
        expected = by_id[decision.record_id]
        if decision.pmid != expected:
            raise CollectionError(
                f"{decision.record_id}: decision pmid is {decision.pmid!r} but the "
                f"batch record has pmid {expected!r}"
            )


def _check_not_already_collected(
    batch: dict[str, Any], log_path: pathlib.Path
) -> None:
    expected = {r["record_id"] for r in batch["records"]}
    already = {
        d.record_id
        for d in read_decisions(log_path)
        if d.record_id in expected and d.stage == batch["stage"]
    }
    if already:
        raise CollectionError(
            f"{len(already)} record(s) in batch {batch['batch_id']} already have a "
            f"{batch['stage']!r} decision in {log_path}: {_shown(already)}; "
            "collecting again would double-count the batch"
        )


# Below this share of distinct `reason` strings, a batch is treated as
# mechanically generated rather than screened.
#
# This exists because it nearly happened. A subagent asked to screen 200
# records wrote a keyword-matching script -- "mouse" in text -> not_human --
# and had it emit all 200 decisions, stamped with the correct model_id and
# prompt_sha256. Every other check in this module would have passed it: the
# set-equality check, the schema validation, the provenance fields, the
# idempotence guard. The output would have been keyword heuristics recorded
# as model judgements, which is the same failure as the fabricated manuscript
# this project exists to correct, in a form that looks perfect on inspection.
#
# The signal is sharp. Across 34 genuine batches the distinct-reason ratio was
# 1.000 in every one -- a real screener writes a record-specific sentence each
# time. A templated generator emits a handful of fixed strings; the script
# above would have scored about 0.04. The threshold sits far below anything
# observed rather than close to it, so a batch with some genuine repetition is
# not caught by accident.
MIN_DISTINCT_REASON_RATIO = 0.5


def _check_reasons_are_not_templated(batch_id: str, decisions: list) -> None:
    reasons = [d.reason for d in decisions if d.reason is not None]
    if len(reasons) < 20:
        return  # too few to distinguish repetition from a small batch
    ratio = len(set(reasons)) / len(reasons)
    if ratio < MIN_DISTINCT_REASON_RATIO:
        raise CollectionError(
            f"batch {batch_id} has only {len(set(reasons))} distinct reasons "
            f"across {len(reasons)} decisions (ratio {ratio:.2f}, floor "
            f"{MIN_DISTINCT_REASON_RATIO}). Genuine screening writes a "
            "record-specific reason each time; a ratio this low means the "
            "decisions were generated by a template or script rather than by "
            "reading the records. Nothing was written."
        )


def _collection_state(batch: dict, log_path: pathlib.Path) -> str:
    """Whether a batch is absent from the log, fully in it, or partly in it.

    The three-way distinction is what makes a run resumable without weakening
    the double-counting guard. A long screening run gets interrupted -- a rate
    limit, a crash, a stopped session -- and the operator re-runs collection.
    Raising on a batch that is already complete would make resumption
    impossible and invite someone to delete the log and start over, which is
    far worse than the problem it was protecting against.

    A PARTIAL overlap is different in kind and still raises. collect() appends
    only after every check has passed, and append_decision fsyncs each line, so
    a batch that is half in the log means something tore mid-append. Those
    records cannot simply be topped up: the ones already there may belong to a
    different decisions file than the one now on disk.
    """
    expected = {r["record_id"] for r in batch["records"]}
    already = {
        d.record_id
        for d in read_decisions(log_path)
        if d.record_id in expected and d.stage == batch["stage"]
    }
    if not already:
        return "absent"
    if already == expected:
        return "complete"
    raise CollectionError(
        f"batch {batch['batch_id']} is PARTIALLY collected: {len(already)} of "
        f"{len(expected)} records already have a {batch['stage']!r} decision "
        f"({_shown(already)}). collect() writes only after all checks pass, so a "
        "partial batch means an append was interrupted; the log and this "
        "decisions file may disagree. Resolve by hand rather than topping up."
    )


def collect(
    batch_path: pathlib.Path,
    decisions_path: pathlib.Path,
    log_path: pathlib.Path,
    model_id: str,
) -> dict[str, int]:
    """Verify one batch's decisions and append them. Raises on any defect."""
    batch_path = pathlib.Path(batch_path)
    log_path = pathlib.Path(log_path)

    batch = _load_batch(batch_path)
    decisions = _parse_decisions(decisions_path)

    # Order matters only in that ALL of these precede the first append below.
    _check_coverage(batch, decisions, batch_path)
    _check_provenance(batch, decisions, model_id)
    _check_pmids(batch, decisions)
    _check_reasons_are_not_templated(batch["batch_id"], decisions)
    _check_not_already_collected(batch, log_path)

    for decision in decisions:
        append_decision(log_path, decision)

    counts = {"collected": len(decisions), "include": 0, "exclude": 0, "unclear": 0}
    for decision in decisions:
        counts[decision.decision] += 1
    return counts


def collect_all(
    batch_dir: pathlib.Path, log_path: pathlib.Path, model_id: str
) -> dict[str, Any]:
    """Collect every batch whose decisions file exists, in sorted order.

    Stops at the first integrity failure rather than continuing past it: the
    batches after a corrupt one are not more trustworthy for having been
    processed, and a partially collected run that reports success is exactly
    the outcome this module exists to prevent.
    """
    batch_dir = pathlib.Path(batch_dir)
    if not batch_dir.is_dir():
        raise CollectionError(f"batch directory {batch_dir} does not exist")

    totals = {"batches": 0, "collected": 0, "include": 0, "exclude": 0, "unclear": 0}
    pending: list[str] = []
    already_collected: list[str] = []

    for batch_path in sorted(batch_dir.glob(BATCH_GLOB)):
        stem = batch_path.stem
        decisions_path = batch_dir / f"{stem}_decisions.jsonl"
        if not decisions_path.exists():
            pending.append(stem)
            continue
        batch = _load_batch(batch_path)
        if _collection_state(batch, log_path) == "complete":
            already_collected.append(stem)
            continue
        counts = collect(batch_path, decisions_path, log_path, model_id)
        totals["batches"] += 1
        for key in ("collected", "include", "exclude", "unclear"):
            totals[key] += counts[key]

    return {**totals, "pending": pending, "already_collected": already_collected}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify and commit subagent screening decisions"
    )
    parser.add_argument("--batch", type=pathlib.Path, required=True)
    parser.add_argument("--decisions", type=pathlib.Path, required=True)
    parser.add_argument("--log", type=pathlib.Path, required=True)
    parser.add_argument("--model-id", required=True)
    args = parser.parse_args()

    counts = collect(args.batch, args.decisions, args.log, args.model_id)
    for key, value in counts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
