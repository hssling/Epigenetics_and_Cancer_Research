"""Cohen's kappa between the investigator and an AI screener.

The registration gates further work at kappa >= 0.75 on a 300-record
calibration sample. This module computes it, reports its confidence interval,
and lists every disagreement so they can be inspected individually.
"""
import math
import pathlib
from collections import Counter
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from pipeline.screen_schema import (
    ScreeningDecision,
    read_decisions,
    single_ai_provenance,
)


class AgreementReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n: int
    observed_agreement: float
    expected_agreement: float
    kappa: float
    kappa_ci_low: float
    kappa_ci_high: float
    confusion: dict[str, int]
    disagreements: list[dict[str, Any]]
    gate: float
    gate_met: bool
    model_id: Optional[str]
    prompt_sha256: Optional[str]


def cohens_kappa(human: list[str], ai: list[str]) -> tuple[float, float, float]:
    """Return (kappa, ci_low, ci_high) with a normal-approximation interval."""
    if len(human) != len(ai):
        raise ValueError(
            f"length mismatch: {len(human)} human vs {len(ai)} ai decisions"
        )
    if not human:
        raise ValueError("cannot compute kappa on empty input")

    n = len(human)
    observed = sum(h == a for h, a in zip(human, ai)) / n

    human_counts, ai_counts = Counter(human), Counter(ai)
    labels = set(human_counts) | set(ai_counts)
    expected = sum(
        (human_counts[label] / n) * (ai_counts[label] / n) for label in labels
    )

    if expected == 1.0:
        # Both raters used a single identical label throughout: agreement is
        # total but kappa is undefined. Report 1.0 with a degenerate interval
        # rather than dividing by zero.
        return 1.0, 1.0, 1.0

    kappa = (observed - expected) / (1 - expected)

    # Conservative on purpose: an independent sweep found this normal-
    # approximation SE conservative (wider than a bootstrap) near the gate,
    # which is disclosed in the methods rather than replaced here.
    se = math.sqrt(observed * (1 - observed) / (n * (1 - expected) ** 2))
    low = max(-1.0, kappa - 1.96 * se)
    high = min(1.0, kappa + 1.96 * se)
    return kappa, low, high


def _latest(decisions: list[ScreeningDecision]) -> dict[str, ScreeningDecision]:
    """Last decision wins: the log is append-only and amendments append."""
    latest: dict[str, ScreeningDecision] = {}
    for decision in decisions:
        latest[decision.record_id] = decision
    return latest


def compare(
    human_path: pathlib.Path,
    ai_path: pathlib.Path,
    gate: float = 0.75,
) -> AgreementReport:
    """Compare two decision logs over the same records."""
    human = _latest(read_decisions(human_path))
    ai = _latest(read_decisions(ai_path))

    bad_human = sorted(
        f"{r} (screener={d.screener})" for r, d in human.items() if d.screener != "human"
    )
    if bad_human:
        raise ValueError(
            "--human log contains decisions not made by a human screener, e.g. "
            f"{bad_human[:5]}; comparing a log against itself (or with "
            "--human/--ai swapped) would silently pass the gate"
        )
    bad_ai = sorted(
        f"{r} (screener={d.screener})" for r, d in ai.items() if d.screener != "ai"
    )
    if bad_ai:
        raise ValueError(
            "--ai log contains decisions not made by the ai screener, e.g. "
            f"{bad_ai[:5]}; comparing a log against itself (or with "
            "--human/--ai swapped) would silently pass the gate"
        )

    only_human = sorted(set(human) - set(ai))
    only_ai = sorted(set(ai) - set(human))
    if only_human or only_ai:
        raise ValueError(
            "decision logs cover different records; comparing them would "
            f"compute a meaningless statistic. Only in human: {only_human[:5]}; "
            f"only in ai: {only_ai[:5]}"
        )

    record_ids = sorted(human)
    human_labels = [human[r].decision for r in record_ids]
    ai_labels = [ai[r].decision for r in record_ids]

    kappa, low, high = cohens_kappa(human_labels, ai_labels)

    n = len(record_ids)
    observed = sum(h == a for h, a in zip(human_labels, ai_labels)) / n
    hc, ac = Counter(human_labels), Counter(ai_labels)
    expected = sum((hc[l] / n) * (ac[l] / n) for l in set(hc) | set(ac))

    confusion = Counter(
        f"{h}->{a}" for h, a in zip(human_labels, ai_labels)
    )

    disagreements = [
        {
            "record_id": r,
            "pmid": human[r].pmid,
            "human": human[r].decision,
            "human_criterion": human[r].criterion,
            "ai": ai[r].decision,
            "ai_criterion": ai[r].criterion,
            "ai_confidence": ai[r].confidence,
            "ai_reason": ai[r].reason,
        }
        for r in record_ids
        if human[r].decision != ai[r].decision
    ]

    model_id, prompt_sha256 = single_ai_provenance([ai[r] for r in record_ids])

    return AgreementReport(
        n=n,
        observed_agreement=observed,
        expected_agreement=expected,
        kappa=kappa,
        kappa_ci_low=low,
        kappa_ci_high=high,
        confusion=dict(confusion),
        disagreements=disagreements,
        gate=gate,
        gate_met=kappa >= gate,
        model_id=model_id,
        prompt_sha256=prompt_sha256,
    )
