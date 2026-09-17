"""Report the screening stage of the PRISMA flow — behind the Stage 0 gate.

Protocol Section 5 makes full screening conditional: "Proceed only when kappa
>= 0.75." `AgreementReport` already computes `gate_met`, but nothing consumed
it, so the gate was a matter of resolve rather than a mechanism.

That distinction matters more here than it looks. The AI screening pass can be
run before any human calibration exists — nothing stops it, and the decisions
it produces are perfectly well-formed. Thousands of completed decisions then
exert real pressure to accept them rather than re-screen if the kappa later
comes out below the gate. This module is where that pressure is refused: the
screening counts cannot be produced at all without an agreement report that
passes, so an ungated pass yields no reportable number.

It is deliberately impossible to satisfy this check with AI decisions alone.
`compare()` refuses a human-vs-human comparison and requires one human log and
one AI log, so a second model run cannot stand in for the investigator.
"""
import argparse
import hashlib
import json
import pathlib
from typing import Any, Optional

from pipeline.agreement import AgreementReport
from pipeline.prisma import PrismaStage
from pipeline.screen_schema import read_decisions, single_ai_provenance


class GateNotPassed(Exception):
    """Raised when screening results are requested before Stage 0 passes."""


def load_agreement(path: pathlib.Path) -> AgreementReport:
    path = pathlib.Path(path)
    if not path.exists():
        raise GateNotPassed(
            f"no agreement report at {path}. The registered Stage 0 gate is "
            "Cohen's kappa >= 0.75 between the investigator and the model "
            "(protocol Section 5). Until the investigator has screened the "
            "calibration sample blind, no kappa exists and no screening count "
            "may be reported."
        )
    return AgreementReport(**json.loads(path.read_text(encoding="utf-8")))


def _kappa_from_confusion(confusion: dict[str, int]) -> tuple[int, float, float]:
    """Recompute (n, observed agreement, kappa) from the confusion matrix alone.

    Keys are "human_label->ai_label". Reconstructing the marginals from the
    matrix lets the gate check the report against itself instead of taking its
    word for it.
    """
    n = sum(confusion.values())
    if n == 0:
        raise GateNotPassed("agreement report has an empty confusion matrix")

    agree = sum(v for k, v in confusion.items() if k.split("->")[0] == k.split("->")[1])
    observed = agree / n

    human_counts: dict[str, int] = {}
    ai_counts: dict[str, int] = {}
    for key, count in confusion.items():
        h, a = key.split("->")
        human_counts[h] = human_counts.get(h, 0) + count
        ai_counts[a] = ai_counts.get(a, 0) + count

    labels = set(human_counts) | set(ai_counts)
    expected = sum(
        (human_counts.get(l, 0) / n) * (ai_counts.get(l, 0) / n) for l in labels
    )
    if expected == 1.0:
        return n, observed, 1.0
    return n, observed, (observed - expected) / (1 - expected)


def assert_gate(agreement: AgreementReport) -> float:
    """Return kappa if the Stage 0 gate is genuinely passed; raise otherwise.

    This does NOT simply read `gate_met`. An earlier version did, and that was
    the whole vulnerability: an agreement report is a plain JSON file, and the
    only thing standing between a fabricated one and a published PRISMA table
    was a boolean someone could type. An adversarial audit opened the gate with
    a hand-written report carrying kappa 0.10, n 1, an empty confusion matrix
    and a made-up model name.

    Three things are checked here, in order:

      1. The report is internally consistent. n, observed agreement and kappa
         are recomputed from the confusion matrix and must match what the
         report claims. A forger must now supply a confusion matrix that really
         does produce the kappa they want -- which means constructing plausible
         paired decisions, not editing one field.
      2. The inputs still hash to what was recorded. The human and AI logs the
         report names must exist and be unchanged.
      3. Only then, whether the gate was met.

    None of this defeats someone determined to fabricate a 300-record human
    log; nothing in a local filesystem can. It raises forgery from a one-token
    edit to a deliberate, multi-file act that leaves the fabricated log on disk
    where a reader can inspect it.
    """
    n, observed, kappa = _kappa_from_confusion(agreement.confusion)

    if n != agreement.n:
        raise GateNotPassed(
            f"agreement report is internally inconsistent: it claims n="
            f"{agreement.n} but its confusion matrix totals {n}. A report whose "
            "own numbers disagree cannot open the gate."
        )
    if abs(observed - agreement.observed_agreement) > 1e-9:
        raise GateNotPassed(
            f"agreement report is internally inconsistent: claims observed "
            f"agreement {agreement.observed_agreement:.6f}, confusion matrix "
            f"gives {observed:.6f}."
        )
    if abs(kappa - agreement.kappa) > 1e-6:
        raise GateNotPassed(
            f"agreement report is internally inconsistent: claims kappa "
            f"{agreement.kappa:.6f}, confusion matrix gives {kappa:.6f}. The "
            "gate is decided by the recomputed value, never by the stored one."
        )

    for role, path_str, expected_hash in (
        ("human", agreement.human_path, agreement.human_sha256),
        ("AI", agreement.ai_path, agreement.ai_sha256),
    ):
        path = pathlib.Path(path_str)
        if not path.exists():
            raise GateNotPassed(
                f"the {role} decision log this report was computed from "
                f"({path_str}) is missing. The gate cannot be verified against "
                "inputs that are not there."
            )
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected_hash:
            raise GateNotPassed(
                f"the {role} decision log ({path_str}) has changed since this "
                f"agreement report was computed (sha256 {actual[:12]} vs "
                f"{expected_hash[:12]}). Recompute the agreement report."
            )

    if kappa < agreement.gate:
        raise GateNotPassed(
            f"Stage 0 gate NOT passed: recomputed kappa={kappa:.3f} against a "
            f"gate of {agreement.gate}, on n={n}. Protocol Section 5 permits "
            "refining the instrument and re-screening; it does not permit "
            "reporting screening results from a run that failed the gate."
        )
    if not agreement.gate_met:
        raise GateNotPassed(
            f"report records gate_met=False despite a recomputed kappa of "
            f"{kappa:.3f}; refusing to second-guess it. Recompute the report."
        )
    return kappa


def screening_stage(
    decisions_path: pathlib.Path,
    agreement_path: pathlib.Path,
    identified: int,
) -> tuple[PrismaStage, dict[str, Any]]:
    """Build the screening PRISMA stage. Raises unless Stage 0 passed.

    `identified` is the number of records entering screening — the combined
    corpus size — passed in rather than inferred, so a decision log that
    covers only part of the corpus cannot silently redefine the denominator.
    """
    agreement = load_agreement(agreement_path)
    kappa = assert_gate(agreement)

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

    reason_parts = ", ".join(f"{k}={v}" for k, v in sorted(criteria.items()))
    stage = PrismaStage(
        name="screening_title_abstract",
        identified=identified,
        excluded=counts["exclude"],
        reason=(
            f"excluded at title/abstract ({reason_parts}); "
            f"kappa={kappa:.3f} vs investigator on n={agreement.n}; "
            f"model={model_id}; prompt={prompt_sha256[:12]}"
        ),
    )
    summary = {
        "identified": identified,
        **counts,
        "criteria": criteria,
        "kappa": kappa,
        "kappa_n": agreement.n,
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
        description="Screening PRISMA counts (requires a passing Stage 0 gate)"
    )
    parser.add_argument("--decisions", type=pathlib.Path, required=True)
    parser.add_argument("--agreement", type=pathlib.Path, required=True)
    parser.add_argument(
        "--corpus", type=pathlib.Path, required=True,
        help="the screened corpus; its record count is the PRISMA denominator",
    )
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()

    stage, summary = screening_stage(
        args.decisions, args.agreement, corpus_size(args.corpus)
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    for key in ("identified", "include", "exclude", "unclear"):
        print(f"{key}: {summary[key]}")
    print(f"kappa: {summary['kappa']:.3f} (n={summary['kappa_n']})")


if __name__ == "__main__":
    main()
