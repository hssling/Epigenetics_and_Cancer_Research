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


def assert_gate(agreement: AgreementReport) -> float:
    """Return kappa if the Stage 0 gate is passed; raise GateNotPassed if not."""
    if not agreement.gate_met:
        raise GateNotPassed(
            f"Stage 0 gate NOT passed: kappa={agreement.kappa:.3f} "
            f"(95% CI {agreement.kappa_ci_low:.3f} to "
            f"{agreement.kappa_ci_high:.3f}) against a gate of "
            f"{agreement.gate}, on n={agreement.n}. Protocol Section 5 permits "
            "refining the instrument and re-screening; it does not permit "
            "reporting screening results from a run that failed the gate."
        )
    return agreement.kappa


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Screening PRISMA counts (requires a passing Stage 0 gate)"
    )
    parser.add_argument("--decisions", type=pathlib.Path, required=True)
    parser.add_argument("--agreement", type=pathlib.Path, required=True)
    parser.add_argument("--identified", type=int, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()

    stage, summary = screening_stage(
        args.decisions, args.agreement, args.identified
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    for key in ("identified", "include", "exclude", "unclear"):
        print(f"{key}: {summary[key]}")
    print(f"kappa: {summary['kappa']:.3f} (n={summary['kappa_n']})")


if __name__ == "__main__":
    main()
