"""Agreement between two AI screening logs on the records they share.

This is model selection, not calibration. The registered Stage 0 gate is
Cohen's kappa between the INVESTIGATOR and a model; nothing here substitutes
for it, and `agreement.compare` refuses an AI-vs-AI comparison for exactly
that reason. What this answers is narrower and still worth knowing: if a
cheaper model is to screen the corpus, does it decide the same way as the
expensive one on records both have seen?

A disagreement here is not evidence that either model is right. It marks a
record where the instrument admits two readings, which is the same signal the
calibration rounds used.
"""
import argparse
import collections
import json
import pathlib

from pipeline.screen_schema import read_decisions, single_ai_provenance


def compare_models(a_path: pathlib.Path, b_path: pathlib.Path) -> dict:
    a = {d.record_id: d for d in read_decisions(a_path) if d.screener == "ai"}
    b = {d.record_id: d for d in read_decisions(b_path) if d.screener == "ai"}

    a_model, a_prompt = single_ai_provenance(list(a.values()))
    b_model, b_prompt = single_ai_provenance(list(b.values()))
    if a_model == b_model:
        raise ValueError(
            f"both logs are {a_model!r}; a model comparison needs two models"
        )
    if a_prompt != b_prompt:
        raise ValueError(
            f"logs used different instruments ({a_prompt[:12]} vs {b_prompt[:12]}); "
            "a disagreement would confound model with prompt"
        )

    shared = sorted(set(a) & set(b))
    if not shared:
        raise ValueError("the two logs share no records")

    agree = sum(1 for r in shared if a[r].decision == b[r].decision)
    matrix: collections.Counter = collections.Counter(
        (a[r].decision, b[r].decision) for r in shared
    )
    disagreements = [
        {
            "record_id": r,
            a_model: {"decision": a[r].decision, "criterion": a[r].criterion,
                      "confidence": a[r].confidence, "reason": a[r].reason},
            b_model: {"decision": b[r].decision, "criterion": b[r].criterion,
                      "confidence": b[r].confidence, "reason": b[r].reason},
        }
        for r in shared if a[r].decision != b[r].decision
    ]

    # The decision that matters asymmetrically: one model includes, the other
    # excludes. An include/unclear split still routes the record to a human.
    hard = sum(
        1 for r in shared
        if {a[r].decision, b[r].decision} == {"include", "exclude"}
    )

    return {
        "model_a": a_model,
        "model_b": b_model,
        "prompt_sha256": a_prompt,
        "n_shared": len(shared),
        "n_agree": agree,
        "raw_agreement": agree / len(shared),
        "n_disagree": len(shared) - agree,
        "n_include_vs_exclude": hard,
        "matrix": {f"{x}->{y}": n for (x, y), n in sorted(matrix.items())},
        "disagreements": disagreements,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Agreement between two AI screening logs")
    p.add_argument("--a", type=pathlib.Path, required=True)
    p.add_argument("--b", type=pathlib.Path, required=True)
    p.add_argument("--out", type=pathlib.Path, required=True)
    args = p.parse_args()

    result = compare_models(args.a, args.b)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"shared:            {result['n_shared']}")
    print(f"raw agreement:     {result['raw_agreement']:.1%}")
    print(f"disagreements:     {result['n_disagree']}")
    print(f"include vs exclude:{result['n_include_vs_exclude']}")


if __name__ == "__main__":
    main()
