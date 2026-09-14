"""Slice the corpus into batch files for subagent screening.

The Anthropic API path (`pipeline.ai_screener`) needs an API key. Where none
is available the same screening is performed by Claude Code subagents: this
module writes what a subagent reads, `pipeline.collect_batches` verifies and
records what it returns. Only the caller of the model changes; the decision
log, its schema and its provenance fields are identical either way.

Two properties are load-bearing here:

* the batches PARTITION the selection -- every record exactly once, in corpus
  order. Nothing downstream can detect a record that was never put in a batch,
  because it simply never appears again.
* a null abstract is written as null. `ai_screener` substitutes a placeholder
  at render time for the API path, but a batch file is an artefact that is
  read and audited, and `"[no abstract available]"` in an artefact is
  indistinguishable from a record whose abstract really says that.

There is no randomness in this module. Batch membership is a function of
corpus order alone, so a rerun reproduces the same files byte for byte.

Run:
    python -m pipeline.prepare_batches --corpus egm/search/raw/corpus.json \\
        --out-dir egm/screening/batches --batch-size 50 --stage screening
"""
import argparse
import json
import pathlib
from typing import Any, Iterable, Optional

from pipeline.prompt_loader import load_prompt
from pipeline.screen_schema import Stage

# The fields a screener is allowed to see. Anything else in the corpus record
# (source_db, doi, merge history) is irrelevant to a title/abstract judgement
# and is withheld rather than passed through, so it cannot influence one.
BATCH_FIELDS: tuple[str, ...] = (
    "record_id", "pmid", "title", "abstract", "year", "journal"
)

STAGES: tuple[str, ...] = ("calibration", "screening", "validation")


class PrepareError(Exception):
    """The batch set could not be built. Never caught internally."""


def _corpus_records(corpus_path: pathlib.Path) -> list[dict[str, Any]]:
    payload = json.loads(pathlib.Path(corpus_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "records" not in payload:
        raise PrepareError(
            f"{corpus_path} is not a corpus artefact: expected an object with a "
            "'records' key"
        )
    return payload["records"]


def _select(
    records: list[dict[str, Any]], record_ids: Optional[Iterable[str]]
) -> list[dict[str, Any]]:
    """Records to batch, in corpus order.

    A requested id that is not in the corpus raises. Silently returning the
    subset that happened to match would shrink a calibration sample -- and the
    kappa denominator with it -- with no trace in any artefact.
    """
    if record_ids is None:
        return list(records)

    wanted = set(record_ids)
    selected = [r for r in records if r["record_id"] in wanted]
    missing = sorted(wanted - {r["record_id"] for r in selected})
    if missing:
        raise PrepareError(
            f"{len(missing)} requested record_id(s) are not in the corpus: "
            f"{missing[:5]}"
        )
    return selected


def _batch_record(record: dict[str, Any]) -> dict[str, Any]:
    absent = [field for field in BATCH_FIELDS if field not in record]
    if absent:
        raise PrepareError(
            f"record {record.get('record_id', '<unknown>')!r} is missing "
            f"{absent}; a malformed record must not be screened as though the "
            "field were simply null"
        )
    # Verbatim, including None. No placeholders: see the module docstring.
    return {field: record[field] for field in BATCH_FIELDS}


def prepare(
    corpus_path: pathlib.Path,
    out_dir: pathlib.Path,
    batch_size: int,
    stage: Stage,
    record_ids: Optional[Iterable[str]] = None,
    prompt_version: str = "v1",
) -> list[pathlib.Path]:
    """Write `out_dir/batch_NNNN.json` and return the paths written."""
    if batch_size < 1:
        raise PrepareError(f"batch_size must be at least 1, got {batch_size}")
    if stage not in STAGES:
        raise PrepareError(f"unknown stage {stage!r}; expected one of {list(STAGES)}")

    _, prompt_sha = load_prompt(prompt_version)
    selected = _select(_corpus_records(corpus_path), record_ids)
    if not selected:
        raise PrepareError(
            "selection contains no records; writing zero batches and exiting "
            "cleanly is indistinguishable from a successful run"
        )

    out_dir = pathlib.Path(out_dir)
    payloads: list[tuple[pathlib.Path, str]] = []
    for index in range(0, len(selected), batch_size):
        number = index // batch_size + 1
        batch_id = f"batch_{number:04d}"
        payloads.append((
            out_dir / f"{batch_id}.json",
            json.dumps(
                {
                    "batch_id": batch_id,
                    "stage": stage,
                    "prompt_sha256": prompt_sha,
                    "records": [
                        _batch_record(r) for r in selected[index:index + batch_size]
                    ],
                },
                indent=2,
                sort_keys=True,
            ),
        ))

    # Every existence check runs before the first write: a clash partway
    # through would otherwise leave a half-written batch set that looks
    # complete to anyone who lists the directory afterwards.
    for path, _ in payloads:
        if path.exists():
            raise FileExistsError(f"{path} exists; batch files are not overwritten")

    out_dir.mkdir(parents=True, exist_ok=True)
    for path, text in payloads:
        path.write_text(text, encoding="utf-8")
    return [path for path, _ in payloads]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Slice the corpus into batch files for subagent screening"
    )
    parser.add_argument("--corpus", type=pathlib.Path, required=True)
    parser.add_argument("--out-dir", type=pathlib.Path, required=True)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--stage", choices=list(STAGES), required=True)
    # Required, with no default. The prompt hash is stamped into every
    # decision in the batch, so a defaulted version would silently label a
    # run with a superseded instrument -- exactly the drift the hash exists
    # to make detectable.
    parser.add_argument("--prompt-version", required=True,
                        help="e.g. v2 -- must match the instrument actually used")
    parser.add_argument(
        "--record-ids", type=pathlib.Path,
        help="optional JSON list of record_ids to select",
    )
    args = parser.parse_args()

    record_ids = None
    if args.record_ids is not None:
        record_ids = json.loads(args.record_ids.read_text(encoding="utf-8"))
        if not isinstance(record_ids, list):
            raise PrepareError(
                f"{args.record_ids} must contain a JSON list of record_ids"
            )

    paths = prepare(
        args.corpus, args.out_dir, args.batch_size, args.stage, record_ids,
        args.prompt_version,
    )
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
