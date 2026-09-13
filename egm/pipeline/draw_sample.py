"""Draw the two registered samples.

Both draws are seeded and reproducible, which the registration commits to: a
reader must be able to redraw the same sample from the published seed and
check the reported statistics.
"""
import argparse
import json
import pathlib
from collections import defaultdict
from typing import Any

from pipeline.recall import STRATUM_BOUNDARIES, stratum_of
from pipeline.sampling import stratified_sample
from pipeline.screen_schema import read_decisions


def _load_records(corpus_path: pathlib.Path) -> list[dict[str, Any]]:
    payload = json.loads(pathlib.Path(corpus_path).read_text(encoding="utf-8"))
    return payload["records"]


def _write(out_path: pathlib.Path, records: list[dict[str, Any]]) -> None:
    out_path = pathlib.Path(out_path)
    if out_path.exists():
        raise FileExistsError(
            f"{out_path} exists. Redrawing would invalidate any screening "
            "already done against the current sample; draw to a new path and "
            "record why in the amendments log."
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, indent=2), encoding="utf-8")


def draw_calibration(
    corpus_path: pathlib.Path,
    out_path: pathlib.Path,
    n: int = 300,
    seed: int = 20260913,
) -> dict[str, int]:
    """Draw the calibration sample: n records at random from the corpus."""
    records = _load_records(corpus_path)
    drawn = stratified_sample(
        records, ["corpus"] * len(records), {"corpus": n}, seed=seed
    )
    _write(out_path, drawn)
    return {"population": len(records), "drawn": len(drawn), "seed": seed}


def stratum_sizes(decisions_path: pathlib.Path) -> dict[str, int]:
    """Count AI exclusions in each confidence stratum."""
    sizes = {name: 0 for name, _ in STRATUM_BOUNDARIES}
    for decision in read_decisions(decisions_path):
        if decision.screener == "ai" and decision.decision == "exclude":
            sizes[stratum_of(decision.confidence)] += 1
    return sizes


def draw_validation(
    corpus_path: pathlib.Path,
    decisions_path: pathlib.Path,
    out_path: pathlib.Path,
    per_stratum: dict[str, int],
    seed: int,
) -> dict[str, int]:
    """Draw the validation sample from AI exclusions, stratified by confidence."""
    by_id = {r["record_id"]: r for r in _load_records(corpus_path)}

    excluded: list[dict[str, Any]] = []
    strata: list[str] = []
    for decision in read_decisions(decisions_path):
        if decision.screener != "ai" or decision.decision != "exclude":
            continue
        record = by_id.get(decision.record_id)
        if record is None:
            raise ValueError(
                f"decision log references {decision.record_id}, absent from the corpus"
            )
        excluded.append(record)
        strata.append(stratum_of(decision.confidence))

    drawn = stratified_sample(excluded, strata, per_stratum, seed=seed)
    _write(out_path, drawn)

    counts = defaultdict(int)
    for stratum in strata:
        counts[stratum] += 1
    return {
        "excluded_population": len(excluded),
        "drawn": len(drawn),
        "seed": seed,
        **{f"population_{k}": v for k, v in counts.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Draw a registered sample")
    sub = parser.add_subparsers(dest="which", required=True)

    cal = sub.add_parser("calibration")
    cal.add_argument("--corpus", type=pathlib.Path, required=True)
    cal.add_argument("--out", type=pathlib.Path, required=True)
    cal.add_argument("--n", type=int, default=300)
    cal.add_argument("--seed", type=int, default=20260913)

    val = sub.add_parser("validation")
    val.add_argument("--corpus", type=pathlib.Path, required=True)
    val.add_argument("--decisions", type=pathlib.Path, required=True)
    val.add_argument("--out", type=pathlib.Path, required=True)
    val.add_argument("--low", type=int, default=500)
    val.add_argument("--mid", type=int, default=300)
    val.add_argument("--high", type=int, default=200)
    val.add_argument("--seed", type=int, default=20260913)

    args = parser.parse_args()
    if args.which == "calibration":
        counts = draw_calibration(args.corpus, args.out, args.n, args.seed)
    else:
        counts = draw_validation(
            args.corpus, args.decisions, args.out,
            {"low": args.low, "mid": args.mid, "high": args.high}, args.seed,
        )
    for key, value in counts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
