"""CLI: screen a sample or the full corpus with a named model."""
import argparse
import json
import pathlib
from typing import Any

import anthropic

from pipeline import ai_screener


def _load(path: pathlib.Path) -> list[dict[str, Any]]:
    """Accept either a corpus payload ({manifest, records}) or a bare list."""
    payload = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return payload["records"] if isinstance(payload, dict) else payload


def run(
    sample_path: pathlib.Path,
    model_id: str,
    out_path: pathlib.Path,
    usage_path: pathlib.Path,
    stage: str,
) -> dict[str, int]:
    client = anthropic.Anthropic()
    return ai_screener.screen_sample(
        client, _load(sample_path), model_id, out_path, usage_path, stage
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="AI title/abstract screening")
    parser.add_argument("--sample", type=pathlib.Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--usage", type=pathlib.Path, required=True)
    parser.add_argument(
        "--stage", choices=["calibration", "screening", "validation"], required=True
    )
    args = parser.parse_args()

    counts = run(args.sample, args.model, args.out, args.usage, args.stage)
    for key, value in counts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
