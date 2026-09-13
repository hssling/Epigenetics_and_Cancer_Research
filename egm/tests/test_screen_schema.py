"""The decision record. Invalid combinations must be unconstructable."""
import pytest
from pydantic import ValidationError

from pipeline.screen_schema import (
    CRITERIA,
    ScreeningDecision,
    append_decision,
    read_decisions,
)


def _human(**overrides):
    base = dict(
        record_id="egm-000001", pmid="111", decision="include", criterion=None,
        confidence=None, reason=None, screener="human", model_id=None,
        prompt_sha256=None, stage="calibration",
        decided_at="2026-09-13T10:00:00Z", supersedes=None,
    )
    return {**base, **overrides}


def _ai(**overrides):
    return _human(**{
        "screener": "ai", "model_id": "claude-opus-5",
        "prompt_sha256": "a" * 64, "confidence": 0.9,
        "reason": "Measures DNA methylation after a dietary intervention.",
        **overrides,
    })


def test_there_are_exactly_seven_criteria_in_registered_order():
    assert CRITERIA == (
        "not_human", "not_primary", "no_measured_marker", "ncrna_only",
        "no_approach_link", "out_of_window", "not_english",
    )


def test_a_valid_human_include_is_accepted():
    assert ScreeningDecision(**_human()).decision == "include"


def test_exclude_without_a_criterion_is_rejected():
    """An exclusion with no reason is not reportable in a PRISMA diagram."""
    with pytest.raises(ValidationError, match="criterion"):
        ScreeningDecision(**_human(decision="exclude", criterion=None))


def test_include_with_a_criterion_is_rejected():
    with pytest.raises(ValidationError, match="criterion"):
        ScreeningDecision(**_human(decision="include", criterion="not_human"))


def test_unclear_with_a_criterion_is_rejected():
    with pytest.raises(ValidationError, match="criterion"):
        ScreeningDecision(**_human(decision="unclear", criterion="not_human"))


def test_ai_decision_without_model_id_is_rejected():
    """A decision that cannot be traced to a model is not auditable."""
    with pytest.raises(ValidationError, match="model_id"):
        ScreeningDecision(**_ai(model_id=None))


def test_ai_decision_without_prompt_hash_is_rejected():
    with pytest.raises(ValidationError, match="prompt_sha256"):
        ScreeningDecision(**_ai(prompt_sha256=None))


def test_ai_decision_without_confidence_is_rejected():
    """Confidence stratifies the validation sample; it cannot be optional for AI."""
    with pytest.raises(ValidationError, match="confidence"):
        ScreeningDecision(**_ai(confidence=None))


def test_human_decision_with_a_model_id_is_rejected():
    with pytest.raises(ValidationError, match="model_id"):
        ScreeningDecision(**_human(model_id="claude-opus-5"))


def test_confidence_outside_zero_to_one_is_rejected():
    with pytest.raises(ValidationError):
        ScreeningDecision(**_ai(confidence=1.5))


def test_omitting_a_nullable_field_raises_rather_than_defaulting():
    kwargs = _human()
    del kwargs["supersedes"]
    with pytest.raises(ValidationError, match="supersedes"):
        ScreeningDecision(**kwargs)


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        ScreeningDecision(**_human(notes="extra"))


def test_append_and_read_round_trip(tmp_path):
    path = tmp_path / "decisions.jsonl"
    append_decision(path, ScreeningDecision(**_human(record_id="egm-1")))
    append_decision(path, ScreeningDecision(**_ai(record_id="egm-2")))

    decisions = read_decisions(path)
    assert [d.record_id for d in decisions] == ["egm-1", "egm-2"]
    assert decisions[1].model_id == "claude-opus-5"


def test_append_never_rewrites_earlier_lines(tmp_path):
    """Append-only: an amendment adds a line, it does not edit one."""
    path = tmp_path / "decisions.jsonl"
    append_decision(path, ScreeningDecision(**_human(record_id="egm-1")))
    first_line = path.read_text(encoding="utf-8").splitlines()[0]

    append_decision(path, ScreeningDecision(
        **_human(record_id="egm-1", decision="exclude", criterion="not_human",
                 supersedes="2026-09-13T10:00:00Z")))

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[0] == first_line


def test_read_decisions_on_missing_file_returns_empty(tmp_path):
    assert read_decisions(tmp_path / "absent.jsonl") == []
