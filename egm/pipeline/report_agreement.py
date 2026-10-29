"""CLI: compute Cohen's kappa between a human and an AI decision log."""
import argparse
import pathlib
from typing import Optional

from pipeline.agreement import AgreementReport, compare


def run(
    human_path: pathlib.Path,
    ai_path: pathlib.Path,
    out_path: pathlib.Path,
    gate: float = 0.75,
    sample_path: Optional[pathlib.Path] = None,
) -> AgreementReport:
    report = compare(human_path, ai_path, gate=gate, sample_path=sample_path)
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Human vs AI screening agreement")
    parser.add_argument("--human", type=pathlib.Path, required=True)
    parser.add_argument("--ai", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--gate", type=float, default=0.75)
    parser.add_argument(
        "--sample", type=pathlib.Path, default=None,
        help="the drawn sample the comparison is about. Required whenever the "
             "model has screened more records than the investigator sampled, "
             "which is the normal case once corpus screening has run.",
    )
    args = parser.parse_args()

    report = run(args.human, args.ai, args.out, args.gate, args.sample)
    if report.sample_path:
        print(f"sample:   {report.sample_path}")
    print(f"n:        {report.n}")
    print(f"kappa:    {report.kappa:.3f} "
          f"(95% CI {report.kappa_ci_low:.3f} to {report.kappa_ci_high:.3f})")
    print(f"agree:    {report.observed_agreement:.1%}")
    print(f"disagree: {len(report.disagreements)}")
    print(f"GATE {report.gate}: {'MET' if report.gate_met else 'NOT MET'}")


if __name__ == "__main__":
    main()
