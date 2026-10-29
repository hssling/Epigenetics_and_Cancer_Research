"""Recall validation. This produces a number the registration publishes."""
import itertools
from datetime import datetime, timedelta, timezone

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


# A person reaches records one at a time, so human fixtures are stamped 30 s
# apart; the AI log is written in one go and keeps a single timestamp.
_human_clock = itertools.count()


def _human_stamp(step_seconds=30):
    start = datetime(2026, 9, 13, 10, 0, tzinfo=timezone.utc)
    return (start + timedelta(seconds=step_seconds * next(_human_clock))).isoformat()


def _decision(path, record_id, decision, screener, confidence=None, criterion=None,
              decided_at=None):
    if decided_at is None:
        decided_at = _human_stamp() if screener == "human" else "2026-09-13T10:00:00Z"
    append_decision(path, ScreeningDecision(
        record_id=record_id, pmid=record_id.split("-")[1], decision=decision,
        criterion=criterion, confidence=confidence,
        reason="r" if screener == "ai" else None, screener=screener,
        model_id="claude-opus-5" if screener == "ai" else None,
        prompt_sha256="a" * 64 if screener == "ai" else None,
        stage="validation", decided_at=decided_at, supersedes=None,
    ))


def test_no_false_negatives_reports_perfect_sensitivity_with_an_upper_bound(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    ids = set()
    for n in range(100):
        rid = f"egm-{n}"
        ids.add(rid)
        _decision(ai_p, rid, "exclude", "ai", confidence=0.9, criterion="not_primary")
        _decision(human_p, rid, "exclude", "human", criterion="not_primary")

    report = validate_recall(human_p, ai_p, ids, {"high": 1000})

    assert report.false_negatives == 0
    assert report.sensitivity == 1.0
    assert report.fn_rate == 0.0
    assert report.fn_rate_ci_high > 0
    assert report.implied_missed_high > 0


def test_false_negatives_are_counted_and_reported(tmp_path):
    """A human include among AI excludes is a false negative."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    ids = set()
    for n in range(100):
        rid = f"egm-{n}"
        ids.add(rid)
        _decision(ai_p, rid, "exclude", "ai", confidence=0.9, criterion="not_primary")
        _decision(human_p, rid, "include" if n < 3 else "exclude", "human",
                  criterion=None if n < 3 else "not_primary")

    report = validate_recall(human_p, ai_p, ids, {"high": 1000})

    assert report.false_negatives == 3
    assert report.sensitivity == pytest.approx(0.97)
    assert report.fn_rate == pytest.approx(0.03)


def test_human_unclear_counts_as_a_false_negative(tmp_path):
    """An 'unclear' the AI excluded should have reached a human. That is a miss."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    ids = set()
    for n in range(10):
        rid = f"egm-{n}"
        ids.add(rid)
        _decision(ai_p, rid, "exclude", "ai", confidence=0.9, criterion="not_primary")
        _decision(human_p, rid, "unclear" if n == 0 else "exclude", "human",
                  criterion=None if n == 0 else "not_primary")

    assert validate_recall(human_p, ai_p, ids, {"high": 100}).false_negatives == 1


def test_validating_a_non_excluded_record_raises(tmp_path):
    """The validation sample is drawn from AI excludes only."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    _decision(ai_p, "egm-1", "include", "ai", confidence=0.9)
    _decision(human_p, "egm-1", "include", "human")

    with pytest.raises(ValueError, match="not excluded"):
        validate_recall(human_p, ai_p, {"egm-1"}, {"high": 10})


def test_stratum_weighting_differs_from_the_raw_rate(tmp_path):
    """Low-confidence exclusions are over-sampled, so the raw rate is biased.

    50 low-confidence records sampled from a population of 100, with 5 misses;
    50 high-confidence sampled from 9,900, with 0. The raw rate is 5%, but the
    population rate is far lower because high-confidence records dominate.
    """
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    ids = set()
    for n in range(50):
        rid = f"egm-low{n}"
        ids.add(rid)
        _decision(ai_p, rid, "exclude", "ai", confidence=0.2, criterion="not_primary")
        _decision(human_p, rid, "include" if n < 5 else "exclude", "human",
                  criterion=None if n < 5 else "not_primary")
    for n in range(50):
        rid = f"egm-high{n}"
        ids.add(rid)
        _decision(ai_p, rid, "exclude", "ai", confidence=0.95, criterion="not_primary")
        _decision(human_p, rid, "exclude", "human", criterion="not_primary")

    report = validate_recall(human_p, ai_p, ids, {"low": 100, "high": 9900})

    assert report.fn_rate == pytest.approx(0.05)
    assert report.weighted_fn_rate < 0.002
    assert set(report.by_stratum) == {"low", "high"}
    assert report.by_stratum["low"]["false_negatives"] == 5


# --- Fix 1: implied_missed must come from the weighted rate, not the raw one --


def test_implied_missed_uses_the_weighted_rate_not_the_raw_sample_rate(tmp_path):
    """Reconstructing the pre-fix behaviour: implied_missed = fn_rate * total.

    Low confidence is oversampled (50 of a 100-record stratum) and misses
    heavily there (10 of 50); high confidence is undersampled relative to its
    huge population (50 of a 9,000-record stratum) and never misses. The raw
    sample rate (10/100 = 10%) wildly overstates the population rate once the
    9,000 near-perfect high-confidence records are weighted in, so a correct
    implied_missed must be far below what the raw rate would imply.
    """
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    ids = set()
    for n in range(50):
        rid = f"egm-low{n}"
        ids.add(rid)
        _decision(ai_p, rid, "exclude", "ai", confidence=0.2, criterion="not_primary")
        _decision(human_p, rid, "include" if n < 10 else "exclude", "human",
                  criterion=None if n < 10 else "not_primary")
    for n in range(50):
        rid = f"egm-high{n}"
        ids.add(rid)
        _decision(ai_p, rid, "exclude", "ai", confidence=0.95, criterion="not_primary")
        _decision(human_p, rid, "exclude", "human", criterion="not_primary")

    stratum_sizes = {"low": 100, "high": 9000}
    total_excluded = sum(stratum_sizes.values())
    report = validate_recall(human_p, ai_p, ids, stratum_sizes)

    # The raw (unweighted) sample false-negative rate, applied naively —
    # this is what the pre-fix code produced.
    raw_fn_low, raw_fn_high = clopper_pearson(
        report.false_negatives, report.n_validated, 0.95
    )
    raw_implied_high = raw_fn_high * total_excluded

    # The weighted rate must diverge sharply from the raw rate here (that is
    # the whole point of stratification), so the correct implied_missed must
    # sit far below the raw-rate projection.
    assert report.implied_missed_high < raw_implied_high * 0.5

    # And it must be internally consistent with the reported weighted bounds.
    assert report.implied_missed_low == pytest.approx(
        report.weighted_fn_rate_ci_low * total_excluded
    )
    assert report.implied_missed_high == pytest.approx(
        report.weighted_fn_rate_ci_high * total_excluded
    )
    assert report.rate_basis == (
        "implied_missed is derived from the stratum-weighted rate; fn_rate "
        "is the unweighted sample rate"
    )


# --- Fix 2: a partial sample must not silently become the denominator ------


def test_partial_human_screening_raises_instead_of_shrinking_the_denominator(tmp_path):
    """200 of 1,000 drawn records screened must not silently report n=200."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    drawn_ids = set()
    for n in range(1000):
        rid = f"egm-{n}"
        drawn_ids.add(rid)
        _decision(ai_p, rid, "exclude", "ai", confidence=0.9, criterion="not_primary")
    for n in range(200):
        rid = f"egm-{n}"
        _decision(human_p, rid, "exclude", "human", criterion="not_primary")

    with pytest.raises(ValueError, match="partial sample"):
        validate_recall(human_p, ai_p, drawn_ids, {"high": 1000})


def test_full_human_screening_of_the_drawn_sample_succeeds(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    ids = set()
    for n in range(20):
        rid = f"egm-{n}"
        ids.add(rid)
        _decision(ai_p, rid, "exclude", "ai", confidence=0.9, criterion="not_primary")
        _decision(human_p, rid, "exclude", "human", criterion="not_primary")

    report = validate_recall(human_p, ai_p, ids, {"high": 100})
    assert report.n_validated == 20


def test_records_outside_the_drawn_sample_are_not_counted(tmp_path):
    """Amendment 8 appends the extension to the same human log. The 200-record
    first stage must still be computed on the 200, or the trigger reads the
    1,000 and an extension's false negative would count towards it."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    ids = set()
    for n in range(40):
        rid = f"egm-{n}"
        if n < 20:
            ids.add(rid)
        _decision(ai_p, rid, "exclude", "ai", confidence=0.9, criterion="not_primary")
        if n == 30:
            _decision(human_p, rid, "include", "human")
        else:
            _decision(human_p, rid, "exclude", "human", criterion="not_primary")

    report = validate_recall(human_p, ai_p, ids, {"high": 100})
    assert report.n_validated == 20
    assert report.false_negatives == 0


def test_truncated_ai_log_raises(tmp_path):
    """Same failure as a partial human sample, on the other log."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    expected = {f"egm-{n}" for n in range(20)}
    for n in range(20):
        _decision(human_p, f"egm-{n}", "exclude", "human", criterion="not_primary")
    for n in range(5):          # AI log truncated
        _decision(ai_p, f"egm-{n}", "exclude", "ai", confidence=0.9,
                  criterion="not_primary")

    with pytest.raises(ValueError, match="no AI decision"):
        validate_recall(human_p, ai_p, expected, {"high": 100})


# --- Amendment 7: the human log must pass the agreement gate's checks ------


def _screened_pair(tmp_path, n, step_seconds):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    start = datetime(2026, 10, 30, 9, 0, tzinfo=timezone.utc)
    for i in range(n):
        rid = f"egm-{i}"
        _decision(ai_p, rid, "exclude", "ai", confidence=0.9, criterion="not_primary")
        _decision(human_p, rid, "exclude", "human", criterion="not_primary",
                  decided_at=(start + timedelta(seconds=step_seconds * i)).isoformat())
    return human_p, ai_p, {f"egm-{i}" for i in range(n)}


def test_a_log_faster_than_a_person_can_read_is_refused(tmp_path):
    """The 2026-10-29 calibration log ran at 1.3 s per record.

    Amendment 7 removed the kappa gate but kept its validity check for the
    recall sample. Without it, a log of 200 instant `exclude`s would report
    a perfect recall bound, which is the most favourable number this module
    can produce.
    """
    human_p, ai_p, ids = _screened_pair(tmp_path, 200, step_seconds=1.3)
    with pytest.raises(ValueError, match="not produced by a person"):
        validate_recall(human_p, ai_p, ids, {"high": 1000})


def test_a_log_at_reading_pace_is_accepted(tmp_path):
    human_p, ai_p, ids = _screened_pair(tmp_path, 200, step_seconds=20)
    report = validate_recall(human_p, ai_p, ids, {"high": 1000})
    assert report.n_validated == 200


def test_ai_decisions_in_the_human_log_are_refused(tmp_path):
    """Passing the AI log as --human would score the model against itself."""
    ai_p = tmp_path / "a.jsonl"
    ids = set()
    for i in range(30):
        rid = f"egm-{i}"
        ids.add(rid)
        _decision(ai_p, rid, "exclude", "ai", confidence=0.9, criterion="not_primary")
    with pytest.raises(ValueError, match="not made by a human"):
        validate_recall(ai_p, ai_p, ids, {"high": 1000})


def test_timing_is_judged_on_the_drawn_sample_only(tmp_path):
    """Decisions outside the sample cannot dilute a fast run inside it."""
    human_p, ai_p, ids = _screened_pair(tmp_path, 200, step_seconds=1.3)
    # one stray, much later decision stretches the whole log's span
    _decision(human_p, "egm-99999", "exclude", "human", criterion="not_primary",
              decided_at="2026-12-31T00:00:00+00:00")
    with pytest.raises(ValueError, match="not produced by a person"):
        validate_recall(human_p, ai_p, ids, {"high": 1000})


# --- Fix 3: a stratum must never silently vanish or be assumed perfect -----


def test_sample_stratum_absent_from_stratum_sizes_raises(tmp_path):
    """A stratum in the sample but not in stratum_sizes would be dropped."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    ids = set()
    for n in range(10):
        rid = f"egm-{n}"
        ids.add(rid)
        _decision(ai_p, rid, "exclude", "ai", confidence=0.2, criterion="not_primary")
        _decision(human_p, rid, "include" if n < 5 else "exclude", "human",
                  criterion=None if n < 5 else "not_primary")

    with pytest.raises(ValueError, match="absent from stratum_sizes"):
        # "low" is the sampled stratum but stratum_sizes only knows "high".
        validate_recall(human_p, ai_p, ids, {"high": 1000})


def test_unsampled_stratum_is_never_assumed_zero(tmp_path):
    """A stratum with population but zero sampled records is fully uncertain."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    ids = set()
    for n in range(10):
        rid = f"egm-{n}"
        ids.add(rid)
        _decision(ai_p, rid, "exclude", "ai", confidence=0.95, criterion="not_primary")
        _decision(human_p, rid, "exclude", "human", criterion="not_primary")

    # "mid" has population but zero sampled records.
    report = validate_recall(human_p, ai_p, ids, {"high": 100, "mid": 900})

    assert report.by_stratum["high"]["fn_rate"] == 0.0
    # The unsampled "mid" stratum contributes full uncertainty (0.0 to 1.0),
    # not a substituted 0 — so the upper bound must reflect it being nearly
    # entirely unknown, dominating the tiny sampled "high" contribution.
    assert report.weighted_fn_rate_ci_high > 0.85


# --- Fix 6: reports carry provenance, and refuse to blend two runs ---------


def test_recall_report_carries_model_and_prompt_provenance(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    ids = set()
    for n in range(10):
        rid = f"egm-{n}"
        ids.add(rid)
        _decision(ai_p, rid, "exclude", "ai", confidence=0.9, criterion="not_primary")
        _decision(human_p, rid, "exclude", "human", criterion="not_primary")

    report = validate_recall(human_p, ai_p, ids, {"high": 100})
    assert report.model_id == "claude-opus-5"
    assert report.prompt_sha256 == "a" * 64


def test_recall_report_raises_when_sample_spans_two_models(tmp_path):
    from pipeline.screen_schema import append_decision

    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    ids = set()
    for n in range(5):
        rid = f"egm-{n}"
        ids.add(rid)
        _decision(ai_p, rid, "exclude", "ai", confidence=0.9, criterion="not_primary")
        _decision(human_p, rid, "exclude", "human", criterion="not_primary")
    rid = "egm-other-model"
    ids.add(rid)
    append_decision(ai_p, ScreeningDecision(
        record_id=rid, pmid="99", decision="exclude", criterion="not_primary",
        confidence=0.9, reason="r", screener="ai", model_id="claude-sonnet-5",
        prompt_sha256="a" * 64, stage="validation",
        decided_at="2026-09-13T10:00:00Z", supersedes=None,
    ))
    _decision(human_p, rid, "exclude", "human", criterion="not_primary")

    with pytest.raises(ValueError, match="more than one AI model"):
        validate_recall(human_p, ai_p, ids, {"high": 100})


def test_report_has_no_option_to_drop_a_block(tmp_path):
    """The registration forbids re-running until the estimate looks good."""
    import inspect

    from pipeline import recall

    source = inspect.getsource(recall.validate_recall)
    for forbidden in ("exclude_block", "drop_", "ignore_", "min_rate"):
        assert forbidden not in source


def test_matches_scipy_across_a_grid_when_scipy_is_available():
    """Cross-check the hand-rolled incomplete beta against a reference.

    The continued fraction is easy to get subtly wrong — an earlier draft of
    this module was wrong for most inputs while still looking plausible. This
    pins the implementation to an independent reference wherever one exists.
    """
    scipy_stats = pytest.importorskip("scipy.stats")

    cases = [(s, 1000) for s in (0, 1, 2, 5, 10, 50, 100, 500, 999, 1000)]
    cases += [(s, n) for n in (5, 10, 30) for s in (0, 1, n // 2, n)]
    cases += [(0, 10000), (37, 10000), (10000, 10000)]

    worst = 0.0
    for successes, n in cases:
        low, high = clopper_pearson(successes, n, 0.95)
        expected_low = (
            0.0 if successes == 0
            else scipy_stats.beta.ppf(0.025, successes, n - successes + 1)
        )
        expected_high = (
            1.0 if successes == n
            else scipy_stats.beta.ppf(0.975, successes + 1, n - successes)
        )
        worst = max(worst, abs(low - expected_low), abs(high - expected_high))

    assert worst < 1e-9, f"max deviation from scipy: {worst:g}"
