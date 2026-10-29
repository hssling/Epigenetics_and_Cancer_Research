"""Report the screening stage of the PRISMA flow — behind the screening gate.

The AI screening pass can be run before any human validation exists — nothing
stops it, and the decisions it produces are perfectly well-formed. Thousands of
completed decisions then exert real pressure to report them as they stand. This
module is where that pressure is refused: the screening counts cannot be
produced at all until the investigator's blind validation exists, so an
unvalidated pass yields no reportable number.

The gate was registered as Cohen's kappa >= 0.75 on a 300-record calibration
sample. Amendment 7 (OSF 3xtf2, approved 2026-10-29) withdrew it after a
calibration log failed the timing check, and made recall validation of 200
AI exclusions the investigator's verification step. The gate is now that
validation.

It is recomputed here from its inputs, not read from a report. The kappa gate
read an `AgreementReport` JSON and an audit opened it with a hand-typed one;
the fix was a stack of consistency and hash checks around a file that need not
have been trusted in the first place. Recomputing from the logs leaves the
human log itself as the only thing to forge, and `recall.validate_recall`
applies the same timing check to it that the kappa gate applied.
"""
import argparse
import hashlib
import json
import pathlib
from typing import Any, Optional

from pipeline.draw_sample import stratum_sizes
from pipeline.prisma import PrismaStage
from pipeline.recall import RecallReport, validate_recall
from pipeline.screen_schema import read_decisions, single_ai_provenance

# The Amendment 7 sample, `screening/validation_200.json`, identified by its
# record ids (sorted, newline-joined) rather than its bytes, so a CRLF checkout
# does not break the pin. Extending the sample under the registered rule
# changes this value; that is a deliberate edit with an amendments.md entry,
# never something an operator does by pointing --sample at another file.
REGISTERED_VALIDATION_SAMPLE_SHA256 = (
    "da38e8b98efa21a4d15ac413702c77b8e8514ab197e5aba5064c720311681c0b"
)

# Amendment 8: the extension, if the 200 trigger it, is the whole of
# `screening/validation_1000.json` (the registered 500/300/200 draw of
# 2026-09-17, of which the 200 are a subsample), screened in one step.
# Pinned the same way, before any of the 200 had been screened.
REGISTERED_EXTENSION_SAMPLE_SHA256 = (
    "54f0b35e59e5afe2d678a071b5a85758bc379ba8c1908be00a94fc5813689181"
)


class GateNotPassed(Exception):
    """Raised when screening results are requested before validation exists."""


def check_extension_rule(first_stage: RecallReport, extension_supplied: bool) -> None:
    """Enforce Amendment 8 given the 200-record result. Raises GateNotPassed to refuse.

    The registered rule: one or more false negatives in the 200 triggers blind
    screening of all 800 remaining records, and recall is then reported on the
    full 1,000. Zero false negatives means no extension; the 200 is final.

    An extension the 200 did not trigger is refused: accepting it would let
    whoever runs this choose, after seeing both, which estimate to report.

    A triggered extension not yet screened is NOT refused. Refusing would make
    the investigator's finding of missed studies the thing that withholds the
    screening counts, which this module exists to prevent. `screening_stage`
    produces the counts stamped provisional, with the 200-record estimate the
    rule says the 1,000 will replace.
    """
    if extension_supplied and first_stage.false_negatives == 0:
        raise GateNotPassed(
            "the 200-record first stage found no false negative, so under "
            "Amendment 8 it is final and there is no extension; recall is "
            "reported on the 200, not on whichever of two samples is supplied"
        )


def sample_ids_sha256(sample_path: pathlib.Path) -> str:
    records = json.loads(pathlib.Path(sample_path).read_text(encoding="utf-8"))
    ids = sorted(r["record_id"] for r in records)
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def assert_recall_validated(
    decisions_path: pathlib.Path,
    validation_path: pathlib.Path,
    sample_path: pathlib.Path,
    registered_sample_sha256: str = REGISTERED_VALIDATION_SAMPLE_SHA256,
    extension_path: Optional[pathlib.Path] = None,
    registered_extension_sha256: str = REGISTERED_EXTENSION_SAMPLE_SHA256,
) -> tuple[RecallReport, Optional[RecallReport]]:
    """Return (recall of record, first stage if extended) once validation is complete.

    There is no threshold on the result. Protocol Section 5: "A recall
    estimate that comes out poor is reported, not re-run until favourable."
    A gate that opened only on good recall would let the investigator's
    finding of missed studies hide the screening counts it qualifies; instead
    the estimate travels with the counts wherever they are reported.

    `sample_path` is always the 200. Under Amendment 8 `extension_path`, when
    given, is the 1,000 that contains them; the recall of record is then
    computed on the 1,000, and the 200 is returned beside it as the first
    stage. Whether an extension may or must be supplied is
    `check_extension_rule`'s decision, made from the 200's result.
    """
    validation_path = pathlib.Path(validation_path)
    sample_path = pathlib.Path(sample_path)
    if not validation_path.exists():
        raise GateNotPassed(
            f"no investigator validation log at {validation_path}. Under "
            "Amendment 7 the screening counts are reportable once the "
            "investigator has screened the 200-record validation sample blind "
            "(screening/RUNBOOK.md, step 7). Until then the AI decisions are "
            "provisional and no screening count may be reported."
        )
    if not sample_path.exists():
        raise GateNotPassed(f"no validation sample at {sample_path}")

    actual = sample_ids_sha256(sample_path)
    if actual != registered_sample_sha256:
        raise GateNotPassed(
            f"{sample_path} is not the registered validation sample (record-id "
            f"sha256 {actual[:12]}, registered {registered_sample_sha256[:12]}). "
            "Recall is estimated on the sample Amendment 7 fixed, not on "
            "whichever sample is supplied."
        )

    ids = {r["record_id"] for r in
           json.loads(sample_path.read_text(encoding="utf-8"))}
    sizes = stratum_sizes(decisions_path)
    try:
        first = validate_recall(validation_path, decisions_path, ids, sizes)
    except ValueError as exc:
        raise GateNotPassed(f"recall validation is not valid: {exc}") from exc

    check_extension_rule(first, extension_supplied=extension_path is not None)
    if extension_path is None:
        return first, None

    extension_path = pathlib.Path(extension_path)
    if not extension_path.exists():
        raise GateNotPassed(f"no extension sample at {extension_path}")
    actual = sample_ids_sha256(extension_path)
    if actual != registered_extension_sha256:
        raise GateNotPassed(
            f"{extension_path} is not the registered extension sample "
            f"(record-id sha256 {actual[:12]}, registered "
            f"{registered_extension_sha256[:12]}). Amendment 8 fixed the "
            "extension as the whole 1,000-record draw."
        )
    extended = {r["record_id"] for r in
                json.loads(extension_path.read_text(encoding="utf-8"))}
    if not ids <= extended:
        raise GateNotPassed(
            f"{len(ids - extended)} of the first-stage records are not in "
            f"{extension_path}; the extension must contain the 200 it extends"
        )
    try:
        final = validate_recall(validation_path, decisions_path, extended, sizes)
    except ValueError as exc:
        raise GateNotPassed(f"extended recall validation is not valid: {exc}") from exc
    return final, first


def screening_stage(
    decisions_path: pathlib.Path,
    validation_path: pathlib.Path,
    sample_path: pathlib.Path,
    identified: int,
    registered_sample_sha256: str = REGISTERED_VALIDATION_SAMPLE_SHA256,
    extension_path: Optional[pathlib.Path] = None,
    registered_extension_sha256: str = REGISTERED_EXTENSION_SAMPLE_SHA256,
) -> tuple[PrismaStage, dict[str, Any]]:
    """Build the screening PRISMA stage. Raises unless validation is complete.

    `identified` is the number of records entering screening — the combined
    corpus size — passed in rather than inferred, so a decision log that
    covers only part of the corpus cannot silently redefine the denominator.
    """
    recall, first_stage = assert_recall_validated(
        decisions_path, validation_path, sample_path, registered_sample_sha256,
        extension_path, registered_extension_sha256,
    )

    decisions = [d for d in read_decisions(decisions_path) if d.stage == "screening"]
    if not decisions:
        raise ValueError(
            f"no decisions at stage 'screening' in {decisions_path}; the "
            "screening stage cannot be reported from an empty log"
        )

    covered = {d.record_id for d in decisions}
    if len(covered) != len(decisions):
        raise ValueError(
            f"{len(decisions)} decisions cover only {len(covered)} distinct "
            "records; a duplicated decision would be double-counted"
        )
    if len(covered) != identified:
        raise ValueError(
            f"{identified} records entered screening but the log covers "
            f"{len(covered)}. Screening is incomplete; a PRISMA count reported "
            "now would omit the difference without saying so."
        )

    counts = {"include": 0, "exclude": 0, "unclear": 0}
    criteria: dict[str, int] = {}
    for decision in decisions:
        counts[decision.decision] += 1
        if decision.criterion is not None:
            criteria[decision.criterion] = criteria.get(decision.criterion, 0) + 1

    model_id, prompt_sha256 = single_ai_provenance(
        [d for d in decisions if d.screener == "ai"]
    )
    # Amendment 8: false negatives in the 200 with no extension screened yet.
    # Reported, never withheld, but marked so it cannot pass as final.
    extension_owed = first_stage is None and recall.false_negatives > 0

    reason_parts = ", ".join(f"{k}={v}" for k, v in sorted(criteria.items()))
    stage = PrismaStage(
        name="screening_title_abstract",
        identified=identified,
        excluded=counts["exclude"],
        reason=(
            f"excluded at title/abstract ({reason_parts}); "
            f"recall validated on n={recall.n_validated} AI exclusions screened "
            f"blind by the investigator, false negatives "
            f"{recall.false_negatives} of {recall.n_validated}, weighted FN "
            f"rate {recall.weighted_fn_rate:.4f} (95% CI "
            f"{recall.weighted_fn_rate_ci_low:.4f}-"
            f"{recall.weighted_fn_rate_ci_high:.4f}); "
            + (
                "PROVISIONAL: Amendment 8 extension to the full 1,000 is "
                "required and not yet screened; "
                if extension_owed else ""
            )
            + (
                f"extended under Amendment 8 after a first stage of "
                f"{first_stage.false_negatives} of {first_stage.n_validated}; "
                if first_stage is not None else ""
            )
            + f"model={model_id}; prompt={prompt_sha256[:12]}"
        ),
    )
    summary = {
        "identified": identified,
        **counts,
        "criteria": criteria,
        "recall_n": recall.n_validated,
        "recall_false_negatives": recall.false_negatives,
        "recall_fn_rate_ci_high": recall.fn_rate_ci_high,
        "recall_weighted_fn_rate": recall.weighted_fn_rate,
        "recall_weighted_fn_rate_ci_low": recall.weighted_fn_rate_ci_low,
        "recall_weighted_fn_rate_ci_high": recall.weighted_fn_rate_ci_high,
        "recall_implied_missed_high": recall.implied_missed_high,
        "recall_extended": first_stage is not None,
        "recall_extension_owed": extension_owed,
        "first_stage_n": first_stage.n_validated if first_stage else None,
        "first_stage_false_negatives":
            first_stage.false_negatives if first_stage else None,
        "first_stage_weighted_fn_rate_ci_high":
            first_stage.weighted_fn_rate_ci_high if first_stage else None,
        "model_id": model_id,
        "prompt_sha256": prompt_sha256,
    }
    return stage, summary


def corpus_size(corpus_path: pathlib.Path) -> int:
    """How many records entered screening, read from the corpus itself.

    The denominator used to be a command-line integer. That made the most
    important number in the PRISMA flow the one thing an operator typed: an
    audit ran the reporter with `--identified 1700` against a log covering
    1,700 of 9,786 records and got a complete, internally consistent,
    entirely wrong screening row, because the completeness check compares the
    log against the number supplied rather than against the corpus.

    Reading it from the corpus does not make the number unforgeable -- the
    corpus is a file too -- but it removes the case that matters, where a
    partial run is reported in good faith because the operator passed the
    count that matched it.
    """
    corpus_path = pathlib.Path(corpus_path)
    if not corpus_path.exists():
        raise ValueError(
            f"no corpus at {corpus_path}; the number of records entering "
            "screening is read from the corpus, not supplied by the operator"
        )
    return len(json.loads(corpus_path.read_text(encoding="utf-8"))["records"])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Screening PRISMA counts (requires the investigator's "
        "recall validation, Amendment 7)"
    )
    parser.add_argument("--decisions", type=pathlib.Path, required=True)
    parser.add_argument(
        "--validation", type=pathlib.Path, required=True,
        help="the investigator's blind validation log (screen_app output)",
    )
    parser.add_argument(
        "--sample", type=pathlib.Path, required=True,
        help="the registered validation sample, screening/validation_200.json",
    )
    parser.add_argument(
        "--extension", type=pathlib.Path, default=None,
        help="Amendment 8 extension, screening/validation_1000.json; only "
        "once the 200 have triggered it and all 1,000 are screened",
    )
    parser.add_argument(
        "--corpus", type=pathlib.Path, required=True,
        help="the screened corpus; its record count is the PRISMA denominator",
    )
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()

    stage, summary = screening_stage(
        args.decisions, args.validation, args.sample, corpus_size(args.corpus),
        extension_path=args.extension,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    for key in ("identified", "include", "exclude", "unclear"):
        print(f"{key}: {summary[key]}")
    if summary["recall_extension_owed"]:
        print("PROVISIONAL: false negatives in the 200 -- Amendment 8 requires "
              "screening the rest of validation_1000.json (RUNBOOK step 8)")
    print(f"recall: {summary['recall_false_negatives']} false negatives in "
          f"{summary['recall_n']}; weighted FN rate upper bound "
          f"{summary['recall_weighted_fn_rate_ci_high']:.4%}")


if __name__ == "__main__":
    main()
