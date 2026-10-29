"""Cohen's kappa between the investigator and an AI screener.

The registration gates further work at kappa >= 0.75 on a 300-record
calibration sample. This module computes it, reports its confidence interval,
and lists every disagreement so they can be inspected individually.
"""
import hashlib
import json
import math
import pathlib
from collections import Counter
from datetime import datetime
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
    # Which logs this report was computed from, and what they contained.
    #
    # An agreement report is the key to the Stage 0 gate: everything
    # downstream refuses to emit a screening count until one says the gate
    # passed. That makes it worth forging, and a plain JSON file with a
    # boolean in it is trivial to forge. Recording the inputs means a forged
    # report has to be accompanied by input files that hash to the recorded
    # values -- i.e. by an actual fabricated 300-record human log, which is a
    # deliberate act leaving an artefact, not a one-character edit.
    #
    # This does not make forgery impossible. Anyone who can write these files
    # can write all of them. It makes it expensive, multi-step, and visible.
    human_path: str
    human_sha256: str
    ai_path: str
    ai_sha256: str
    # Which records were compared, when that is narrower than "both logs".
    # None means the two logs covered exactly the same records and all of
    # them were used; a path means the comparison was restricted to a drawn
    # sample, and the reader can check that the restriction was the
    # registered one rather than a convenient subset.
    sample_path: Optional[str]
    sample_sha256: Optional[str]
    model_id: Optional[str]
    prompt_sha256: Optional[str]


def file_sha256(path: pathlib.Path) -> str:
    """SHA-256 of a file's bytes, for binding a report to its inputs."""
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


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


# A human reading a title and abstract and reaching a judgement cannot do it
# in under a few seconds, even skimming. The registered estimate for the
# 300-record calibration sample is 1.5-2.5 hours; this floor allows 15 minutes.
# It is set far below anything realistic on purpose -- it is here to catch a
# log that was written by a program, not to police how fast the investigator
# reads.
MIN_SECONDS_PER_DECISION = 3.0

# Below this many records, timing says nothing: a short log can legitimately
# be written quickly, and test fixtures are small by nature.
MIN_DECISIONS_FOR_TIMING = 20


def _parse_time(stamp: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def assert_human_log_is_plausibly_human(
    human: dict[str, ScreeningDecision]
) -> None:
    """Refuse a "human" log that was plainly not produced by a person screening.

    THIS IS A COST-RAISER, NOT A PROOF. Nothing in a local filesystem can
    establish that a person did the work. An audit demonstrated the attack it
    is aimed at: take the AI decision log, set `screener` to "human", strip
    `model_id` and `prompt_sha256`, flip 8% of the labels, and the gate opens
    at kappa 0.838. Every other check in this module passes, because every
    other check is about the log's shape and the shape is correct.

    What a real screening session leaves behind is time. `screen_app` stamps
    each decision as it is made, so 300 genuine judgements are spread over
    hours and carry hundreds of distinct timestamps. A transcribed log carries
    one timestamp, or a few, or an impossible number of decisions per minute.

    A forger who reads this docstring can fabricate timestamps. That is the
    honest limit: this raises the attack from a one-line `sed` to a deliberate
    fabrication of a screening session. The authenticity of the human log
    ultimately rests on the investigator's attestation, and the manuscript says
    so rather than implying that the repository verifies it.
    """
    if len(human) < MIN_DECISIONS_FOR_TIMING:
        return

    stamps = [_parse_time(d.decided_at) for d in human.values()]
    parsed = [s for s in stamps if s is not None]
    if len(parsed) < len(stamps):
        raise ValueError(
            f"{len(stamps) - len(parsed)} decision(s) in the --human log have "
            "an unparseable decided_at; a log written by screen_app never does"
        )

    distinct = len(set(parsed))
    if distinct == 1:
        raise ValueError(
            f"all {len(human)} decisions in the --human log carry the same "
            "timestamp. A person screening records reaches them one at a time; "
            "a single timestamp means the log was written in one go, by a "
            "program. If this is a legitimately regenerated log, regenerate it "
            "through screen_app so it records when each judgement was made."
        )

    span = (max(parsed) - min(parsed)).total_seconds()
    floor = (len(human) - 1) * MIN_SECONDS_PER_DECISION
    if span < floor:
        raise ValueError(
            f"the --human log records {len(human)} decisions across "
            f"{span:.0f} seconds ({span / max(len(human), 1):.1f}s each). "
            f"Reading a title and abstract and judging it takes longer than "
            f"{MIN_SECONDS_PER_DECISION:.0f}s, so this log was not produced by "
            "a person screening records. Kappa and recall are both measured "
            "against the investigator; a transcribed or generated log "
            "measures nothing."
        )


def compare(
    human_path: pathlib.Path,
    ai_path: pathlib.Path,
    gate: float = 0.75,
    sample_path: Optional[pathlib.Path] = None,
) -> AgreementReport:
    """Compare two decision logs over the same records.

    `sample_path` names the drawn sample the comparison is about. It exists
    because the two logs are legitimately different sizes: the investigator
    screens the 300-record calibration sample, while the model has screened
    the whole 9,786-record corpus, so an exact set-equality check makes the
    real gate command impossible to run.

    The restriction is by an explicit, committed sample file rather than by
    intersecting the logs. Intersecting would accept any overlap at all --
    including a handful of records -- and quietly report a kappa computed on
    whatever the two logs happened to share. Naming the sample means the
    comparison population is a registered artefact, and both logs must cover
    all of it.
    """
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

    # The gate is kappa against the investigator. Everything above checks the
    # log's shape; this checks that a person plausibly produced it.
    assert_human_log_is_plausibly_human(human)

    if sample_path is None:
        only_human = sorted(set(human) - set(ai))
        only_ai = sorted(set(ai) - set(human))
        if only_human or only_ai:
            raise ValueError(
                "decision logs cover different records; comparing them would "
                f"compute a meaningless statistic. Only in human: "
                f"{only_human[:5]}; only in ai: {only_ai[:5]}. If the model "
                "screened a larger corpus than the investigator sampled, pass "
                "--sample to name the records the comparison is about."
            )
        record_ids = sorted(human)
    else:
        sample_ids = [
            r["record_id"] for r in
            json.loads(pathlib.Path(sample_path).read_text(encoding="utf-8"))
        ]
        if not sample_ids:
            raise ValueError(f"{sample_path} contains no records to compare")
        missing_human = sorted(set(sample_ids) - set(human))
        missing_ai = sorted(set(sample_ids) - set(ai))
        if missing_human or missing_ai:
            raise ValueError(
                f"the sample has {len(sample_ids)} records, but the human log "
                f"is missing {len(missing_human)} of them and the ai log "
                f"{len(missing_ai)}. Every sampled record must have a decision "
                "in both logs, or the kappa is computed on a subset chosen by "
                f"what happens to be finished. Missing in human: "
                f"{missing_human[:5]}; missing in ai: {missing_ai[:5]}"
            )
        record_ids = sorted(set(sample_ids))
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
        human_path=str(human_path),
        human_sha256=file_sha256(human_path),
        ai_path=str(ai_path),
        ai_sha256=file_sha256(ai_path),
        sample_path=None if sample_path is None else str(sample_path),
        sample_sha256=None if sample_path is None else file_sha256(sample_path),
        model_id=model_id,
        prompt_sha256=prompt_sha256,
    )
