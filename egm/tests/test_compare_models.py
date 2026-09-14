"""Model comparison must not be mistakable for calibration."""
import pytest

from pipeline.compare_models import compare_models
from pipeline.screen_schema import ScreeningDecision, append_decision

SHA = "a" * 64


def _log(tmp_path, name, model, rows, sha=SHA):
    path = tmp_path / name
    for rid, decision, criterion in rows:
        append_decision(path, ScreeningDecision(
            record_id=rid, pmid=None, decision=decision, criterion=criterion,
            confidence=0.8, reason="r", screener="ai", model_id=model,
            prompt_sha256=sha, stage="screening",
            decided_at="2026-09-14T00:00:00Z", supersedes=None,
        ))
    return path


def test_reports_agreement_and_the_asymmetric_split(tmp_path):
    a = _log(tmp_path, "a.jsonl", "opus", [
        ("r1", "include", None), ("r2", "exclude", "not_primary"),
        ("r3", "include", None), ("r4", "unclear", None)])
    b = _log(tmp_path, "b.jsonl", "haiku", [
        ("r1", "include", None), ("r2", "exclude", "not_primary"),
        ("r3", "exclude", "no_measured_marker"), ("r4", "include", None)])

    result = compare_models(a, b)

    assert result["n_shared"] == 4
    assert result["n_agree"] == 2
    assert result["n_disagree"] == 2
    # r3 is include-vs-exclude; r4 is unclear-vs-include, which still reaches a human
    assert result["n_include_vs_exclude"] == 1
    assert len(result["disagreements"]) == 2


def test_two_logs_from_the_same_model_are_refused(tmp_path):
    """Re-running one model is a reliability check, not a model comparison."""
    a = _log(tmp_path, "a.jsonl", "opus", [("r1", "include", None)])
    b = _log(tmp_path, "b.jsonl", "opus", [("r1", "exclude", "not_primary")])

    with pytest.raises(ValueError, match="a model comparison needs two models"):
        compare_models(a, b)


def test_logs_from_different_prompts_are_refused(tmp_path):
    """Otherwise a disagreement confounds the model with the instrument."""
    a = _log(tmp_path, "a.jsonl", "opus", [("r1", "include", None)])
    b = _log(tmp_path, "b.jsonl", "haiku", [("r1", "exclude", "not_primary")],
             sha="b" * 64)

    with pytest.raises(ValueError, match="different instruments"):
        compare_models(a, b)


def test_no_shared_records_is_refused(tmp_path):
    a = _log(tmp_path, "a.jsonl", "opus", [("r1", "include", None)])
    b = _log(tmp_path, "b.jsonl", "haiku", [("r2", "include", None)])

    with pytest.raises(ValueError, match="share no records"):
        compare_models(a, b)
