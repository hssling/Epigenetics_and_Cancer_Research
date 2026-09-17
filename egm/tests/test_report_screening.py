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
from pipeline.agreement import AgreementReport, file_sha256
from pipeline.screen_schema import ScreeningDecision, append_decision

PROMPT = "a" * 64


def _consistent_confusion(n: int, agree: int) -> dict[str, int]:
    """A confusion matrix that really does describe `agree` of `n` agreeing.

    Both raters must use both labels. A matrix where one rater says "include"
    throughout is degenerate: chance agreement equals observed agreement and
    kappa collapses to 0 however high the raw agreement looks. An earlier
    version of this helper did exactly that and made every gate-passing test
    fail for a reason that had nothing to do with the gate.
    """
    disagree = n - agree
    a = agree // 2
    c = disagree // 2
    return {
        "include->include": a,
        "exclude->exclude": agree - a,
        "include->exclude": c,
        "exclude->include": disagree - c,
    }


def _kappa_of(confusion: dict[str, int]) -> tuple[int, float, float]:
    from pipeline.report_screening import _kappa_from_confusion

    return _kappa_from_confusion(confusion)


def _agreement(tmp_path, agree=280, n=300, gate_met=None, human=None, ai=None):
    """Build an agreement report that passes the gate's own consistency checks.

    The gate recomputes n, observed agreement and kappa from the confusion
    matrix and verifies the input logs still hash to what was recorded, so a
    fixture cannot just assert a kappa any more — it has to supply a matrix
    that produces one, and real files to hash.
    """
    human_path = human or (tmp_path / "human.jsonl")
    ai_path = ai or (tmp_path / "ai.jsonl")
    for f in (human_path, ai_path):
        if not f.exists():
            f.write_text(f"placeholder for {f.name}\n", encoding="utf-8")

    confusion = _consistent_confusion(n, agree)
    recomputed_n, observed, kappa = _kappa_of(confusion)
    assert recomputed_n == n

    report = AgreementReport(
        n=n,
        observed_agreement=observed,
        expected_agreement=0.0,
        kappa=kappa,
        kappa_ci_low=max(-1.0, kappa - 0.06),
        kappa_ci_high=min(1.0, kappa + 0.06),
        confusion=confusion,
        disagreements=[],
        gate=0.75,
        gate_met=kappa >= 0.75 if gate_met is None else gate_met,
        human_path=str(human_path),
        human_sha256=file_sha256(human_path),
        ai_path=str(ai_path),
        ai_sha256=file_sha256(ai_path),
        sample_path=None,
        sample_sha256=None,
        model_id="claude-opus-5",
        prompt_sha256=PROMPT,
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
    agreement = _agreement(tmp_path, agree=200)

    with pytest.raises(GateNotPassed) as excinfo:
        screening_stage(decisions, agreement, identified=3)

    assert "kappa=" in str(excinfo.value)
    assert "NOT passed" in str(excinfo.value)


def test_a_passing_gate_returns_the_kappa(tmp_path):
    assert assert_gate(load_agreement(_agreement(tmp_path, agree=290))) > 0.75


def test_a_report_claiming_a_failed_gate_is_believed(tmp_path):
    """REVERSAL, 2026-09-17. This test previously said the opposite.

    It used to read: "Trust the flag the agreement module computed, not a
    re-derivation here" — on the reasoning that two modules comparing a float
    to 0.75 is two chances to disagree at the boundary. That reasoning holds
    for trusted input and fails completely for a file anyone can edit.

    An adversarial audit opened the gate with a hand-typed agreement report
    carrying gate_met: true, kappa 0.10, n 1, an empty confusion matrix and a
    made-up model name — and rendered the real PRISMA table into a document
    whose header reads "No number in this document was typed by hand."

    The gate now recomputes. What survives of the original intent is only this
    direction: a report that says it FAILED is believed without argument. The
    asymmetry is deliberate — refusing is always safe, permitting never is.
    """
    agreement = load_agreement(_agreement(tmp_path, agree=299, gate_met=False))
    with pytest.raises(GateNotPassed, match="refusing to second-guess"):
        assert_gate(agreement)


# --- forgery: the attacks an adversarial audit actually landed --------------


def _forge(tmp_path, **overrides):
    """Hand-write an agreement report, the way a forger would."""
    path = _agreement(tmp_path, agree=200)          # genuinely failing
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc.update(overrides)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return path


def test_flipping_gate_met_does_not_open_the_gate(tmp_path):
    """The exact one-token edit the audit used."""
    forged = _forge(tmp_path, gate_met=True)

    with pytest.raises(GateNotPassed, match="NOT passed"):
        assert_gate(load_agreement(forged))


def test_a_claimed_kappa_that_the_matrix_does_not_support_is_refused(tmp_path):
    """Claiming 0.99 while the confusion matrix says otherwise."""
    forged = _forge(tmp_path, gate_met=True, kappa=0.99)

    with pytest.raises(GateNotPassed, match="internally inconsistent"):
        assert_gate(load_agreement(forged))


def test_an_empty_confusion_matrix_is_refused(tmp_path):
    """The audit's forged report carried n=1 and no matrix at all."""
    forged = _forge(tmp_path, gate_met=True, kappa=0.99, n=1, confusion={})

    with pytest.raises(GateNotPassed, match="empty confusion matrix"):
        assert_gate(load_agreement(forged))


def test_a_claimed_n_that_the_matrix_does_not_support_is_refused(tmp_path):
    forged = _forge(tmp_path, n=999)

    with pytest.raises(GateNotPassed, match="internally inconsistent"):
        assert_gate(load_agreement(forged))


def test_a_report_whose_human_log_has_changed_is_refused(tmp_path):
    """Recomputing kappa is not enough if the inputs can be swapped after."""
    agreement = _agreement(tmp_path, agree=290)
    (tmp_path / "human.jsonl").write_text("something else entirely\n", encoding="utf-8")

    with pytest.raises(GateNotPassed, match="has changed since"):
        assert_gate(load_agreement(agreement))


def test_a_report_whose_human_log_is_missing_is_refused(tmp_path):
    agreement = _agreement(tmp_path, agree=290)
    (tmp_path / "human.jsonl").unlink()

    with pytest.raises(GateNotPassed, match="is missing"):
        assert_gate(load_agreement(agreement))


def test_a_genuinely_consistent_passing_report_still_works(tmp_path):
    """The hardening must not make a real passing gate unusable."""
    assert assert_gate(load_agreement(_agreement(tmp_path, agree=290))) > 0.75


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
    agreement = _agreement(tmp_path, agree=285)

    stage, summary = screening_stage(path, agreement, identified=10)

    assert stage.identified == 10
    assert stage.excluded == 6
    assert stage.included == 4
    assert "no_measured_marker=6" in stage.reason
    assert "kappa=" in stage.reason
    assert summary["include"] == 4 and summary["exclude"] == 6
    assert summary["model_id"] == "claude-opus-5"
    assert summary["prompt_sha256"] == PROMPT
