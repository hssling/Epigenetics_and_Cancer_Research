"""AI title/abstract screening against the frozen prompt.

Every decision carries the model id and the prompt hash, so it traces to the
exact instrument that produced it. An API failure raises; it is never recorded
as a screening decision, because a failure silently converted into an
exclusion corrupts both the PRISMA count and the recall estimate and is
undetectable afterwards.
"""
import pathlib
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from pipeline.prompt_loader import load_prompt
from pipeline.screen_schema import (
    Criterion,
    Decision,
    ScreeningDecision,
    Stage,
    append_decision,
    read_decisions,
)

# Classification needs little output. Opus 5 runs adaptive thinking by
# default and thinking bills as output, so this ceiling also bounds cost per
# record; the calibration run measures what is actually used.
MAX_TOKENS = 2048


class ScreenerError(Exception):
    """Screening failed for a record. Never caught internally."""


class ScreenerOutput(BaseModel):
    """The structured response required from the model."""

    model_config = ConfigDict(extra="forbid")

    decision: Decision
    criterion: Optional[Criterion]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class UsageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    model_id: str
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int


def _render(record: dict[str, Any]) -> str:
    abstract = record.get("abstract") or "[no abstract available]"
    return (
        f"Title: {record['title']}\n"
        f"Journal: {record.get('journal') or '[not reported]'}\n"
        f"Year: {record.get('year') or '[not reported]'}\n\n"
        f"Abstract:\n{abstract}"
    )


def screen_record(
    client: Any,
    record: dict[str, Any],
    model_id: str,
    prompt_text: str,
    prompt_sha: str,
    stage: Stage,
) -> tuple[ScreeningDecision, UsageRecord]:
    """Screen one record. Raises ScreenerError on any failure."""
    try:
        response = client.messages.parse(
            model=model_id,
            max_tokens=MAX_TOKENS,
            system=[{
                "type": "text",
                "text": prompt_text,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": _render(record)}],
            output_format=ScreenerOutput,
        )
    except Exception as exc:  # noqa: BLE001 - re-raised as ScreenerError
        raise ScreenerError(
            f"screening failed for pmid {record['pmid']}: {exc}"
        ) from exc

    parsed = response.parsed_output
    usage = response.usage

    try:
        decision = ScreeningDecision(
            record_id=record["record_id"],
            pmid=record["pmid"],
            decision=parsed.decision,
            criterion=parsed.criterion,
            confidence=parsed.confidence,
            reason=parsed.reason,
            screener="ai",
            model_id=model_id,
            prompt_sha256=prompt_sha,
            stage=stage,
            decided_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            supersedes=None,
        )
    except Exception as exc:  # noqa: BLE001 - schema violation from the model
        raise ScreenerError(
            f"model returned an invalid decision for pmid {record['pmid']} "
            f"({parsed.decision!r}, criterion={parsed.criterion!r}): {exc}"
        ) from exc

    return decision, UsageRecord(
        record_id=record["record_id"],
        model_id=model_id,
        input_tokens=getattr(usage, "input_tokens", 0),
        output_tokens=getattr(usage, "output_tokens", 0),
        cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
        cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
    )


def screen_sample(
    client: Any,
    records: list[dict[str, Any]],
    model_id: str,
    out_path: pathlib.Path,
    usage_path: pathlib.Path,
    stage: Stage,
    prompt_version: str = "v1",
) -> dict[str, int]:
    """Screen records, appending as it goes. Resumable; skips completed ids."""
    prompt_text, prompt_sha = load_prompt(prompt_version)

    done = {d.record_id for d in read_decisions(out_path) if d.screener == "ai"}
    screened = 0

    usage_path = pathlib.Path(usage_path)
    usage_path.parent.mkdir(parents=True, exist_ok=True)

    for record in records:
        if record["record_id"] in done:
            continue
        decision, usage = screen_record(
            client, record, model_id, prompt_text, prompt_sha, stage
        )
        append_decision(out_path, decision)
        with usage_path.open("a", encoding="utf-8") as handle:
            handle.write(usage.model_dump_json() + "\n")
        screened += 1

    return {
        "total": len(records),
        "screened": screened,
        "skipped": len(records) - screened,
    }
