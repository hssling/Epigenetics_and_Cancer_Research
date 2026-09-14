"""The Stage 0 gate must be a mechanism, not a matter of resolve.

The hazard these tests pin: a full AI screening pass can be run before any
human calibration exists. Thousands of well-formed decisions then create
pressure to accept them rather than re-screen if the kappa comes out below the
gate. Every test here asserts that the pressure has nowhere to act — the
screening counts cannot be produced at all.
"""
import json

import pytest

from pipeline.report_screening import (
    GateNotPassed,
    assert_gate,
    load_agreement,
    screening_stage,
)
from pipeline.agreement import AgreementReport
from pipeline.screen_schema import ScreeningDecision, append_decision

PROMPT = "a" * 64


def _agreement(tmp_path, kappa=0.82, gate_met=True, n=300):
    report = AgreementReport(
        n=n, observed_agreement=0.9, expected_agreement=0.45, kappa=kappa,
        kappa_ci_low=kappa - 0.06, kappa_ci_high=kappa + 0.06,
        confusion={"include_include": 100}, disagreements=[],
        gate=0.75, gate_met=gate_met,
        model_id="claude-opus-5", prompt_sha256=PROMPT,
    )
    path = tmp_path / "agreement.json"
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path


def _decisions(tmp_path, n=3, stage="screening", decision="include"):
    path = tmp_path / "decisions.jsonl"
    for i in range(n):
        append_decision(path, ScreeningDecision(
            record_id=f"egm-{i:06d}", pmid=str(i), decision=decision,
            criterion="not_primary" if decision == "exclude" else None,
            confidence=0.9, reason="r", screener="ai",
            model_id="claude-opus-5", prompt_sha256=PROMPT,
            stage=stage, decided_at="2026-09-14T00:00:00Z", supersedes=None,
        ))
    return path


# --- the gate itself --------------------------------------------------------


def test_no_agreement_report_means_no_screening_count(tmp_path):
    """The state the project is actually in: a pass run before any calibration."""
    decisions = _decisions(tmp_path, 3)

    with pytest.raises(GateNotPassed, match="no agreement report"):
        screening_stage(decisions, tmp_path / "absent.json", identified=3)


def test_a_failed_gate_blocks_the_count_and_names_the_kappa(tmp_path):
    decisions = _decisions(tmp_path, 3)
    agreement = _agreement(tmp_path, kappa=0.61, gate_met=False)

    with pytest.raises(GateNotPassed) as excinfo:
        screening_stage(decisions, agreement, identified=3)

    assert "0.610" in str(excinfo.value)
    assert "NOT passed" in str(excinfo.value)


def test_a_passing_gate_returns_the_kappa(tmp_path):
    assert assert_gate(load_agreement(_agreement(tmp_path, kappa=0.88))) == 0.88


def test_gate_met_is_what_decides_not_the_kappa_value(tmp_path):
    """Trust the flag the agreement module computed, not a re-derivation here.

    Two modules independently comparing a float to 0.75 is two chances to
    disagree at the boundary. If this test fails, report_screening has started
    second-guessing agreement.compare rather than deferring to it.
    """
    agreement = load_agreement(_agreement(tmp_path, kappa=0.99, gate_met=False))
    with pytest.raises(GateNotPassed):
        assert_gate(agreement)


# --- completeness of the screening log --------------------------------------


def test_partial_screening_cannot_be_reported(tmp_path):
    """A log covering 3 of 9,786 records must not yield a PRISMA count."""
    decisions = _decisions(tmp_path, 3)
    agreement = _agreement(tmp_path)

    with pytest.raises(ValueError, match="9786 records entered screening"):
        screening_stage(decisions, agreement, identified=9786)


def test_duplicated_decisions_are_refused(tmp_path):
    decisions = _decisions(tmp_path, 2)
    append_decision(decisions, ScreeningDecision(
        record_id="egm-000000", pmid="0", decision="exclude",
        criterion="not_primary", confidence=0.8, reason="r", screener="ai",
        model_id="claude-opus-5", prompt_sha256=PROMPT, stage="screening",
        decided_at="2026-09-14T00:00:00Z", supersedes=None,
    ))
    agreement = _agreement(tmp_path)

    with pytest.raises(ValueError, match="distinct"):
        screening_stage(decisions, agreement, identified=2)


def test_calibration_decisions_do_not_count_as_screening(tmp_path):
    """Rounds 1-3 were calibration; they must not fill the screening stage."""
    decisions = _decisions(tmp_path, 3, stage="calibration")
    agreement = _agreement(tmp_path)

    with pytest.raises(ValueError, match="no decisions at stage 'screening'"):
        screening_stage(decisions, agreement, identified=3)


def test_decisions_spanning_two_prompts_are_refused(tmp_path):
    """A log blending two instruments is two experiments, not one result."""
    decisions = _decisions(tmp_path, 2)
    append_decision(decisions, ScreeningDecision(
        record_id="egm-000002", pmid="2", decision="include", criterion=None,
        confidence=0.8, reason="r", screener="ai", model_id="claude-opus-5",
        prompt_sha256="b" * 64, stage="screening",
        decided_at="2026-09-14T00:00:00Z", supersedes=None,
    ))
    agreement = _agreement(tmp_path)

    with pytest.raises(ValueError, match="more than one prompt"):
        screening_stage(decisions, agreement, identified=3)


# --- the happy path ---------------------------------------------------------


def test_a_complete_gated_run_produces_the_stage(tmp_path):
    path = tmp_path / "decisions.jsonl"
    for i in range(10):
        append_decision(path, ScreeningDecision(
            record_id=f"egm-{i:06d}", pmid=str(i),
            decision="exclude" if i < 6 else "include",
            criterion="no_measured_marker" if i < 6 else None,
            confidence=0.9, reason="r", screener="ai",
            model_id="claude-opus-5", prompt_sha256=PROMPT, stage="screening",
            decided_at="2026-09-14T00:00:00Z", supersedes=None,
        ))
    agreement = _agreement(tmp_path, kappa=0.81)

    stage, summary = screening_stage(path, agreement, identified=10)

    assert stage.identified == 10
    assert stage.excluded == 6
    assert stage.included == 4
    assert "no_measured_marker=6" in stage.reason
    assert "kappa=0.810" in stage.reason
    assert summary["include"] == 4 and summary["exclude"] == 6
    assert summary["model_id"] == "claude-opus-5"
    assert summary["prompt_sha256"] == PROMPT
