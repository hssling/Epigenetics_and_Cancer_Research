"""The screening decision record.

One schema for every judgement, human or AI. The cross-field rules are
enforced here rather than checked later: an exclusion without a criterion, or
an AI decision that cannot be traced to a model and a prompt, cannot be
constructed at all.
"""
import json
import os
import pathlib
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

Decision = Literal["include", "exclude", "unclear"]
Criterion = Literal[
    "not_human",
    "not_primary",
    "no_measured_marker",
    "ncrna_only",
    "no_approach_link",
    "out_of_window",
    "not_english",
]
Screener = Literal["human", "ai"]
Stage = Literal["calibration", "screening", "validation"]

# Registered order. Index 0 is criterion 1 on the screening keypad.
CRITERIA: tuple[Criterion, ...] = (
    "not_human",
    "not_primary",
    "no_measured_marker",
    "ncrna_only",
    "no_approach_link",
    "out_of_window",
    "not_english",
)

CRITERION_LABELS: dict[Criterion, str] = {
    "not_human": "Not a human study (animal, in vitro, cell-line only)",
    "not_primary": "Not a primary study (review, editorial, comment, letter, abstract without data)",
    "no_measured_marker": "No directly measured epigenetic marker",
    "ncrna_only": "Non-coding RNA as the sole marker",
    "no_approach_link": "No modifiable exposure/intervention and no clinical or public health decision",
    "out_of_window": "Outside 2015-2026",
    "not_english": "Not in English",
}


class ScreeningDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    pmid: str
    decision: Decision
    criterion: Optional[Criterion]
    confidence: Optional[float] = Field(ge=0.0, le=1.0)
    reason: Optional[str]
    screener: Screener
    model_id: Optional[str]
    prompt_sha256: Optional[str]
    stage: Stage
    decided_at: str
    supersedes: Optional[str]

    @model_validator(mode="after")
    def _cross_field_rules(self) -> "ScreeningDecision":
        if self.decision == "exclude" and self.criterion is None:
            raise ValueError(
                "criterion is required when decision is 'exclude': an exclusion "
                "without a stated reason cannot be reported in a PRISMA diagram"
            )
        if self.decision != "exclude" and self.criterion is not None:
            raise ValueError(
                f"criterion must be None when decision is {self.decision!r}"
            )

        if self.screener == "ai":
            if not self.model_id:
                raise ValueError("model_id is required for an AI decision")
            if not self.prompt_sha256:
                raise ValueError("prompt_sha256 is required for an AI decision")
            if self.confidence is None:
                raise ValueError(
                    "confidence is required for an AI decision: it stratifies "
                    "the validation sample"
                )
        else:
            if self.model_id is not None:
                raise ValueError("model_id must be None for a human decision")
            if self.prompt_sha256 is not None:
                raise ValueError("prompt_sha256 must be None for a human decision")
        return self


def append_decision(path: pathlib.Path, decision: ScreeningDecision) -> None:
    """Append one decision and flush it to disk before returning.

    The fsync matters: human screening is irreplaceable work, and a decision
    that is buffered rather than written is lost on a crash.
    """
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(decision.model_dump(), sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def single_ai_provenance(
    decisions: list[ScreeningDecision],
) -> tuple[str, str]:
    """Return the (model_id, prompt_sha256) shared by every AI decision.

    A report is one comparison between one investigator and one model run
    against one prompt. If the decisions being summarised span more than one
    model or prompt, the report would silently blend two different
    experiments under a single statistic — that is refused rather than
    averaged away.
    """
    non_ai = [d.record_id for d in decisions if d.screener != "ai"]
    if non_ai:
        raise ValueError(
            f"provenance requested from non-AI decisions: {sorted(non_ai)[:5]}"
        )
    if not decisions:
        raise ValueError("cannot determine provenance from an empty decision list")

    model_ids = {d.model_id for d in decisions}
    prompt_hashes = {d.prompt_sha256 for d in decisions}
    if len(model_ids) > 1:
        raise ValueError(
            f"decisions span more than one AI model: {sorted(model_ids)}"
        )
    if len(prompt_hashes) > 1:
        raise ValueError(
            f"decisions span more than one prompt: {sorted(prompt_hashes)}"
        )
    return next(iter(model_ids)), next(iter(prompt_hashes))


def read_decisions(path: pathlib.Path) -> list[ScreeningDecision]:
    """Read a decision log. A missing file is an empty log, not an error."""
    path = pathlib.Path(path)
    if not path.exists():
        return []
    return [
        ScreeningDecision(**json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
