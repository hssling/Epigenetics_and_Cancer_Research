"""The screening gate must be a mechanism, not a matter of resolve.

The hazard these tests pin: a full AI screening pass exists before any human
validation does. Thousands of well-formed decisions create pressure to report
them as they stand. Every test here asserts that the pressure has nowhere to
act -- the screening counts cannot be produced without the investigator's
blind recall validation of the registered sample.

Amendment 7 (OSF, 2026-10-29) withdrew the registered kappa gate. The gate is
now the recall validation that replaced it, recomputed from its inputs rather
than read from a report file.
"""
import json
import pathlib
from datetime import datetime, timedelta, timezone

import pytest

from pipeline.report_screening import (
    REGISTERED_VALIDATION_SAMPLE_SHA256,
    GateNotPassed,
    sample_ids_sha256,
    screening_stage,
)
from pipeline.screen_schema import ScreeningDecision, append_decision

PROMPT = "a" * 64
ROOT = pathlib.Path(__file__).resolve().parents[1]


def _ai(path, i, decision, confidence=0.9, prompt=PROMPT, stage="screening"):
    append_decision(path, ScreeningDecision(
        record_id=f"egm-{i:06d}", pmid=str(i), decision=decision,
        criterion="no_measured_marker" if decision == "exclude" else None,
        confidence=confidence, reason="r", screener="ai",
        model_id="claude-sonnet-5", prompt_sha256=prompt,
        stage=stage, decided_at="2026-09-14T00:00:00Z", supersedes=None,
    ))


def _world(tmp_path, n_include=40, n_exclude=60, n_sample=30):
    """A complete screening log, a drawn sample of its exclusions, no human log."""
    decisions = tmp_path / "decisions.jsonl"
    for i in range(n_include):
        _ai(decisions, i, "include")
    for i in range(n_include, n_include + n_exclude):
        _ai(decisions, i, "exclude", confidence=0.95)
    sample = tmp_path / "validation.json"
    sample.write_text(json.dumps([
        {"record_id": f"egm-{i:06d}", "title": "T", "abstract": "A"}
        for i in range(n_include, n_include + n_sample)
    ]), encoding="utf-8")
    return decisions, sample, n_include + n_exclude


def _screen(tmp_path, sample, step_seconds=20, include=(), only=None):
    """The investigator's validation log, stamped as screen_app stamps it."""
    human = tmp_path / "human_validation.jsonl"
    ids = [r["record_id"] for r in json.loads(sample.read_text(encoding="utf-8"))]
    start = datetime(2026, 10, 30, 9, 0, tzinfo=timezone.utc)
    for k, rid in enumerate(ids[:only]):
        verdict = "include" if rid in include else "exclude"
        append_decision(human, ScreeningDecision(
            record_id=rid, pmid=rid.split("-")[1], decision=verdict,
            criterion="no_measured_marker" if verdict == "exclude" else None,
            confidence=None, reason=None, screener="human", model_id=None,
            prompt_sha256=None, stage="validation",
            decided_at=(start + timedelta(seconds=step_seconds * k)).isoformat(),
            supersedes=None,
        ))
    return human


def _stage(decisions, human, sample, identified, registered=None):
    return screening_stage(
        decisions, human, sample, identified,
        registered_sample_sha256=registered or sample_ids_sha256(sample),
    )


# --- the gate itself --------------------------------------------------------


def test_no_validation_log_means_no_screening_count(tmp_path):
    """The state the project is actually in: AI screening done, no human step."""
    decisions, sample, n = _world(tmp_path)
    with pytest.raises(GateNotPassed, match="no investigator validation log"):
        _stage(decisions, tmp_path / "absent.jsonl", sample, n)


def test_a_sample_other_than_the_registered_one_is_refused(tmp_path):
    """A hand-picked small sample would skip the timing check altogether."""
    decisions, sample, n = _world(tmp_path)
    human = _screen(tmp_path, sample)
    with pytest.raises(GateNotPassed, match="not the registered"):
        _stage(decisions, human, sample, n, registered="0" * 64)


def test_a_log_faster_than_reading_pace_is_refused(tmp_path):
    decisions, sample, n = _world(tmp_path)
    human = _screen(tmp_path, sample, step_seconds=1.3)
    with pytest.raises(GateNotPassed, match="not produced by a person"):
        _stage(decisions, human, sample, n)


def test_a_partially_screened_sample_is_refused(tmp_path):
    decisions, sample, n = _world(tmp_path)
    human = _screen(tmp_path, sample, only=10)
    with pytest.raises(GateNotPassed, match="partial sample"):
        _stage(decisions, human, sample, n)


def test_a_missing_sample_file_is_refused(tmp_path):
    decisions, sample, n = _world(tmp_path)
    human = _screen(tmp_path, sample)
    sample.unlink()
    with pytest.raises(GateNotPassed, match="no validation sample"):
        _stage(decisions, human, sample, n, registered="0" * 64)


def test_the_pinned_sample_is_the_committed_amendment_7_draw():
    """The constant must name the file that was actually drawn and committed."""
    committed = ROOT / "screening/validation_200.json"
    assert sample_ids_sha256(committed) == REGISTERED_VALIDATION_SAMPLE_SHA256


def test_the_pin_ignores_line_endings_and_record_order(tmp_path):
    """Git may check the sample out with CRLF; the pin must survive that."""
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    records = [{"record_id": f"egm-{i}"} for i in range(5)]
    a.write_bytes(json.dumps(records, indent=2).encode())
    b.write_bytes(json.dumps(records[::-1], indent=2).replace("\n", "\r\n").encode())
    assert sample_ids_sha256(a) == sample_ids_sha256(b)


# --- a poor result is reported, not withheld --------------------------------


def test_false_negatives_do_not_withhold_the_counts(tmp_path):
    """Protocol Section 5: a poor recall estimate is reported as it stands.

    A gate that opened only on a good recall would make the investigator's
    finding of missed studies the thing that hides the screening result.
    """
    decisions, sample, n = _world(tmp_path)
    human = _screen(tmp_path, sample, include={"egm-000040", "egm-000041"})

    stage, summary = _stage(decisions, human, sample, n)

    assert summary["recall_false_negatives"] == 2
    assert "false negatives 2 of 30" in stage.reason


# --- completeness of the screening log --------------------------------------


def test_partial_screening_cannot_be_reported(tmp_path):
    decisions, sample, n = _world(tmp_path)
    human = _screen(tmp_path, sample)
    with pytest.raises(ValueError, match="9786 records entered screening"):
        _stage(decisions, human, sample, 9786)


def test_duplicated_decisions_are_refused(tmp_path):
    decisions, sample, n = _world(tmp_path)
    human = _screen(tmp_path, sample)
    _ai(decisions, 0, "include")
    with pytest.raises(ValueError, match="distinct"):
        _stage(decisions, human, sample, n)


def test_calibration_decisions_do_not_count_as_screening(tmp_path):
    """Rounds 1-3 were calibration; they must not fill the screening stage."""
    decisions, sample, n = _world(tmp_path)
    human = _screen(tmp_path, sample)
    _ai(decisions, 999, "include", stage="calibration")
    stage, summary = _stage(decisions, human, sample, n)
    assert summary["identified"] == n


def test_decisions_spanning_two_prompts_are_refused(tmp_path):
    """A log blending two instruments is two experiments, not one result."""
    decisions, sample, n = _world(tmp_path)
    human = _screen(tmp_path, sample)
    _ai(decisions, n, "include", prompt="b" * 64)
    with pytest.raises(ValueError, match="more than one prompt"):
        _stage(decisions, human, sample, n + 1)


# --- the happy path ---------------------------------------------------------


def test_a_complete_validated_run_produces_the_stage(tmp_path):
    decisions, sample, n = _world(tmp_path)
    human = _screen(tmp_path, sample)

    stage, summary = _stage(decisions, human, sample, n)

    assert stage.identified == 100
    assert stage.excluded == 60
    assert stage.included == 40
    assert "no_measured_marker=60" in stage.reason
    assert "recall validated on n=30" in stage.reason
    assert "kappa" not in stage.reason
    assert summary["include"] == 40 and summary["exclude"] == 60
    assert summary["recall_n"] == 30
    assert summary["recall_false_negatives"] == 0
    assert 0 < summary["recall_weighted_fn_rate_ci_high"] < 1
    assert summary["model_id"] == "claude-sonnet-5"
    assert summary["prompt_sha256"] == PROMPT
    assert "kappa" not in summary
