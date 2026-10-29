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


# The fields whose drift would change a screening judgement. year and journal
# are carried in the batch too, but a corrected journal name does not make the
# investigator and the model disagree about eligibility; a changed abstract does.
JUDGEMENT_FIELDS: tuple[str, ...] = ("title", "abstract")


def screened_text(batches_dir: pathlib.Path) -> dict[str, dict[str, Any]]:
    """What the screener was actually shown, read from the batch files.

    The batch files are the only record of the text the model judged. The
    corpus is a live artefact: `backfill_abstracts` rewrites it, a re-run of
    the search rewrites it, and neither leaves a mark on the decision log.
    """
    batches_dir = pathlib.Path(batches_dir)
    if not batches_dir.is_dir():
        raise ValueError(
            f"no batch directory at {batches_dir}; the sample cannot be checked "
            "against the text the screener saw"
        )
    seen: dict[str, dict[str, Any]] = {}
    for path in sorted(batches_dir.glob("batch_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for record in payload["records"]:
            seen[record["record_id"]] = record
    if not seen:
        raise ValueError(f"{batches_dir} contains no batch files")
    return seen


def _assert_text_is_what_was_screened(
    drawn: list[dict[str, Any]], batches_dir: pathlib.Path
) -> None:
    """Refuse a sample whose text has drifted from what the AI was shown.

    An audit redrew this sample after the corpus had been updated. The same
    record_ids came back -- the seed is deterministic and the ids are stable --
    but 82 of them carried a title or abstract the model never saw. The
    investigator would have screened one text, the AI another, and every
    disagreement between them would have been scored as a recall failure.

    Nothing in the decision log records which corpus produced it, so this
    compares against the batch files instead: those are what the screener was
    handed, and they are written once and never overwritten.
    """
    seen = screened_text(batches_dir)
    drifted: list[str] = []
    missing: list[str] = []
    for record in drawn:
        rid = record["record_id"]
        if rid not in seen:
            missing.append(rid)
            continue
        if any(record.get(f) != seen[rid].get(f) for f in JUDGEMENT_FIELDS):
            drifted.append(rid)

    if missing:
        raise ValueError(
            f"{len(missing)} drawn record(s) were never in a batch file, so "
            f"there is no record of what the screener saw: {missing[:5]}"
        )
    if drifted:
        raise ValueError(
            f"{len(drifted)} of {len(drawn)} drawn records carry a title or "
            f"abstract that differs from the text the screener was shown "
            f"(e.g. {drifted[:5]}). The corpus has changed since screening ran. "
            "Screening this sample would score the investigator against text "
            "the model never saw. Draw from the batch files, or re-screen the "
            "affected records, and record the decision in the amendments log."
        )


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
    batches_dir: pathlib.Path,
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
    # Before writing: a sample that would be screened against drifted text
    # must not reach disk, where it looks indistinguishable from a good one.
    _assert_text_is_what_was_screened(drawn, batches_dir)
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


def draw_subsample(
    parent_path: pathlib.Path,
    decisions_path: pathlib.Path,
    out_path: pathlib.Path,
    per_stratum: dict[str, int],
    seed: int,
) -> dict[str, int]:
    """Draw a smaller validation sample from an already-drawn one (Amendment 7).

    Records are copied from the parent sample as they stand. The parent was
    checked against the batch files when it was drawn, so re-reading the
    corpus here could only reintroduce the drift that check exists to stop.
    A simple random subsample of a stratified random sample is itself a
    stratified random sample of the population, so the stratum-weighted
    estimate in `recall.py` applies unchanged.
    """
    parent = json.loads(pathlib.Path(parent_path).read_text(encoding="utf-8"))
    ai = {
        d.record_id: d for d in read_decisions(decisions_path) if d.screener == "ai"
    }

    strata: list[str] = []
    for record in parent:
        decision = ai.get(record["record_id"])
        if decision is None or decision.decision != "exclude":
            raise ValueError(
                f"{record['record_id']} in {parent_path} is not an AI exclusion "
                f"in {decisions_path}; recall is estimated from exclusions only"
            )
        strata.append(stratum_of(decision.confidence))

    drawn = stratified_sample(parent, strata, per_stratum, seed=seed)
    _write(out_path, drawn)

    counts = defaultdict(int)
    for stratum in strata:
        counts[stratum] += 1
    return {
        "parent_size": len(parent),
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
    val.add_argument(
        "--batches", type=pathlib.Path, required=True,
        help="the batch directory the screener was given; the drawn text is "
             "checked against it so a changed corpus cannot be screened blind",
    )

    sub_ = sub.add_parser(
        "subsample", help="draw a smaller sample from a drawn one (Amendment 7)"
    )
    sub_.add_argument("--parent", type=pathlib.Path, required=True)
    sub_.add_argument("--decisions", type=pathlib.Path, required=True)
    sub_.add_argument("--out", type=pathlib.Path, required=True)
    sub_.add_argument("--low", type=int, required=True)
    sub_.add_argument("--mid", type=int, required=True)
    sub_.add_argument("--high", type=int, required=True)
    sub_.add_argument("--seed", type=int, required=True)

    args = parser.parse_args()
    if args.which == "calibration":
        counts = draw_calibration(args.corpus, args.out, args.n, args.seed)
    elif args.which == "subsample":
        counts = draw_subsample(
            args.parent, args.decisions, args.out,
            {"low": args.low, "mid": args.mid, "high": args.high}, args.seed,
        )
    else:
        counts = draw_validation(
            args.corpus, args.decisions, args.out,
            {"low": args.low, "mid": args.mid, "high": args.high}, args.seed,
            args.batches,
        )
    for key, value in counts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
