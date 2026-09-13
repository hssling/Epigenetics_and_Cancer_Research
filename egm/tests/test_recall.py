"""Recall validation. This produces a number the registration publishes."""
import pytest

from pipeline.recall import clopper_pearson, validate_recall
from pipeline.screen_schema import ScreeningDecision, append_decision


def test_zero_events_in_one_thousand_matches_the_registered_figure():
    """The registration states 0.368% as the two-sided 95% upper bound."""
    low, high = clopper_pearson(0, 1000, confidence=0.95)
    assert low == 0.0
    assert high == pytest.approx(0.00368, abs=0.00002)


def test_all_successes_gives_upper_bound_one():
    low, high = clopper_pearson(1000, 1000, confidence=0.95)
    assert high == 1.0
    assert low > 0.99


def test_interval_brackets_the_point_estimate():
    low, high = clopper_pearson(50, 1000)
    assert low < 0.05 < high


def test_interval_narrows_as_n_grows():
    small = clopper_pearson(5, 100)
    large = clopper_pearson(50, 1000)
    assert (large[1] - large[0]) < (small[1] - small[0])


def test_successes_exceeding_n_raises():
    with pytest.raises(ValueError, match="exceed"):
        clopper_pearson(11, 10)


def test_zero_n_raises():
    with pytest.raises(ValueError, match="positive"):
        clopper_pearson(0, 0)


# --- validate_recall --------------------------------------------------------


def _decision(path, record_id, decision, screener, confidence=None, criterion=None):
    append_decision(path, ScreeningDecision(
        record_id=record_id, pmid=record_id.split("-")[1], decision=decision,
        criterion=criterion, confidence=confidence,
        reason="r" if screener == "ai" else None, screener=screener,
        model_id="claude-opus-5" if screener == "ai" else None,
        prompt_sha256="a" * 64 if screener == "ai" else None,
        stage="validation", decided_at="2026-09-13T10:00:00Z", supersedes=None,
    ))


def test_no_false_negatives_reports_perfect_sensitivity_with_an_upper_bound(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    for n in range(100):
        rid = f"egm-{n}"
        _decision(ai_p, rid, "exclude", "ai", confidence=0.9, criterion="not_primary")
        _decision(human_p, rid, "exclude", "human", criterion="not_primary")

    report = validate_recall(human_p, ai_p, {"high": 1000})

    assert report.false_negatives == 0
    assert report.sensitivity == 1.0
    assert report.fn_rate == 0.0
    assert report.fn_rate_ci_high > 0
    assert report.implied_missed_high > 0


def test_false_negatives_are_counted_and_reported(tmp_path):
    """A human include among AI excludes is a false negative."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    for n in range(100):
        rid = f"egm-{n}"
        _decision(ai_p, rid, "exclude", "ai", confidence=0.9, criterion="not_primary")
        _decision(human_p, rid, "include" if n < 3 else "exclude", "human",
                  criterion=None if n < 3 else "not_primary")

    report = validate_recall(human_p, ai_p, {"high": 1000})

    assert report.false_negatives == 3
    assert report.sensitivity == pytest.approx(0.97)
    assert report.fn_rate == pytest.approx(0.03)


def test_human_unclear_counts_as_a_false_negative(tmp_path):
    """An 'unclear' the AI excluded should have reached a human. That is a miss."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    for n in range(10):
        rid = f"egm-{n}"
        _decision(ai_p, rid, "exclude", "ai", confidence=0.9, criterion="not_primary")
        _decision(human_p, rid, "unclear" if n == 0 else "exclude", "human",
                  criterion=None if n == 0 else "not_primary")

    assert validate_recall(human_p, ai_p, {"high": 100}).false_negatives == 1


def test_validating_a_non_excluded_record_raises(tmp_path):
    """The validation sample is drawn from AI excludes only."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    _decision(ai_p, "egm-1", "include", "ai", confidence=0.9)
    _decision(human_p, "egm-1", "include", "human")

    with pytest.raises(ValueError, match="not excluded"):
        validate_recall(human_p, ai_p, {"high": 10})


def test_stratum_weighting_differs_from_the_raw_rate(tmp_path):
    """Low-confidence exclusions are over-sampled, so the raw rate is biased.

    50 low-confidence records sampled from a population of 100, with 5 misses;
    50 high-confidence sampled from 9,900, with 0. The raw rate is 5%, but the
    population rate is far lower because high-confidence records dominate.
    """
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    for n in range(50):
        rid = f"egm-low{n}"
        _decision(ai_p, rid, "exclude", "ai", confidence=0.2, criterion="not_primary")
        _decision(human_p, rid, "include" if n < 5 else "exclude", "human",
                  criterion=None if n < 5 else "not_primary")
    for n in range(50):
        rid = f"egm-high{n}"
        _decision(ai_p, rid, "exclude", "ai", confidence=0.95, criterion="not_primary")
        _decision(human_p, rid, "exclude", "human", criterion="not_primary")

    report = validate_recall(human_p, ai_p, {"low": 100, "high": 9900})

    assert report.fn_rate == pytest.approx(0.05)
    assert report.weighted_fn_rate < 0.002
    assert set(report.by_stratum) == {"low", "high"}
    assert report.by_stratum["low"]["false_negatives"] == 5


def test_report_has_no_option_to_drop_a_block(tmp_path):
    """The registration forbids re-running until the estimate looks good."""
    import inspect

    from pipeline import recall

    source = inspect.getsource(recall.validate_recall)
    for forbidden in ("exclude_block", "drop_", "ignore_", "min_rate"):
        assert forbidden not in source
