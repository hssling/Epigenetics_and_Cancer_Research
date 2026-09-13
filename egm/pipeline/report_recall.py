"""CLI: estimate screening recall from hand-screened AI exclusions."""
import argparse
import pathlib

from pipeline.draw_sample import stratum_sizes
from pipeline.recall import RecallReport, validate_recall


def run(
    human_path: pathlib.Path,
    ai_path: pathlib.Path,
    out_path: pathlib.Path,
    confidence: float = 0.95,
) -> RecallReport:
    report = validate_recall(
        human_path, ai_path, stratum_sizes(ai_path), confidence=confidence
    )
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Screening recall validation")
    parser.add_argument("--human", type=pathlib.Path, required=True)
    parser.add_argument("--ai", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--confidence", type=float, default=0.95)
    args = parser.parse_args()

    report = run(args.human, args.ai, args.out, args.confidence)
    print(f"validated:        {report.n_validated}")
    print(f"false negatives:  {report.false_negatives}")
    print(f"sensitivity:      {report.sensitivity:.4f} "
          f"(95% CI {report.sensitivity_ci_low:.4f} to {report.sensitivity_ci_high:.4f})")
    print(f"FN rate:          {report.fn_rate:.4%} "
          f"(upper bound {report.fn_rate_ci_high:.4%})")
    print(f"weighted FN rate: {report.weighted_fn_rate:.4%}")
    print(f"implied missed:   {report.implied_missed_low:.0f} to "
          f"{report.implied_missed_high:.0f} of {report.total_excluded} exclusions")


if __name__ == "__main__":
    main()
