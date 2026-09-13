"""Cohen's kappa and the kappa >= 0.75 gate."""
import pytest

from pipeline.agreement import cohens_kappa, compare
from pipeline.screen_schema import ScreeningDecision, append_decision


def test_perfect_agreement_gives_kappa_one():
    labels = ["include", "exclude", "unclear", "include"]
    kappa, _, _ = cohens_kappa(labels, list(labels))
    assert kappa == pytest.approx(1.0)


def test_chance_level_agreement_gives_kappa_near_zero():
    """Agreement that is no better than chance must not look like skill."""
    human = ["include"] * 50 + ["exclude"] * 50
    ai = (["include", "exclude"] * 50)
    kappa, _, _ = cohens_kappa(human, ai)
    assert abs(kappa) < 0.1


def test_systematic_disagreement_gives_negative_kappa():
    kappa, _, _ = cohens_kappa(["include"] * 10 + ["exclude"] * 10,
                               ["exclude"] * 10 + ["include"] * 10)
    assert kappa < 0


def test_high_but_imperfect_agreement():
    human = ["include"] * 40 + ["exclude"] * 60
    ai = ["include"] * 38 + ["exclude"] * 2 + ["exclude"] * 58 + ["include"] * 2
    kappa, low, high = cohens_kappa(human, ai)
    assert 0.85 < kappa < 1.0
    assert low < kappa < high


def test_kappa_ci_is_clamped_to_the_valid_range():
    """Reconstructing the pre-fix behaviour: near-degenerate marginals push
    the normal-approximation CI outside kappa's [-1, 1] parameter space. For
    these inputs, kappa=0 and the raw (unclamped) bounds work out to about
    -1.79 and +1.79 — outside the domain kappa is even defined on, and it
    would be published as-is. Both bounds must be clamped to [-1, 1].
    """
    import math

    human = ["include"] * 6
    ai = ["include"] * 5 + ["exclude"]

    # The raw, unclamped formula (what the code computed before the fix),
    # reconstructed here to confirm this case actually breaks it.
    n = len(human)
    observed = sum(h == a for h, a in zip(human, ai)) / n
    from collections import Counter
    hc, ac = Counter(human), Counter(ai)
    expected = sum((hc[l] / n) * (ac[l] / n) for l in set(hc) | set(ac))
    kappa_raw = (observed - expected) / (1 - expected)
    se = math.sqrt(observed * (1 - observed) / (n * (1 - expected) ** 2))
    raw_low, raw_high = kappa_raw - 1.96 * se, kappa_raw + 1.96 * se
    assert raw_high > 1.0 and raw_low < -1.0, (
        "test input no longer reproduces an out-of-range CI"
    )

    kappa, low, high = cohens_kappa(human, ai)
    assert kappa == pytest.approx(kappa_raw)
    assert low == -1.0
    assert high == 1.0


def test_confidence_interval_narrows_with_more_data():
    """Imperfect agreement on purpose.

    At perfect agreement observed == 1, so the standard error is exactly zero
    and BOTH intervals have zero width — the comparison would be 0 < 0 and
    the test would fail on correct code.
    """
    small = cohens_kappa(["include"] * 18 + ["exclude"] * 2, ["include"] * 20)
    large = cohens_kappa(["include"] * 180 + ["exclude"] * 20, ["include"] * 200)
    assert (large[2] - large[1]) < (small[2] - small[1])


def test_mismatched_lengths_raise():
    with pytest.raises(ValueError, match="length"):
        cohens_kappa(["include"], ["include", "exclude"])


def test_empty_input_raises():
    with pytest.raises(ValueError, match="empty"):
        cohens_kappa([], [])


# --- compare() over decision logs ------------------------------------------


def _write(path, pairs, screener):
    for record_id, decision, criterion in pairs:
        append_decision(path, ScreeningDecision(
            record_id=record_id, pmid=record_id.split("-")[1], decision=decision,
            criterion=criterion, confidence=0.9 if screener == "ai" else None,
            reason="r" if screener == "ai" else None, screener=screener,
            model_id="claude-opus-5" if screener == "ai" else None,
            prompt_sha256="a" * 64 if screener == "ai" else None,
            stage="calibration", decided_at="2026-09-13T10:00:00Z", supersedes=None,
        ))


def test_compare_reports_gate_met_when_kappa_high(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    pairs = [(f"egm-{n}", "include" if n < 40 else "exclude",
              None if n < 40 else "not_primary") for n in range(100)]
    _write(human_p, pairs, "human")
    _write(ai_p, pairs, "ai")

    report = compare(human_p, ai_p, gate=0.75)
    assert report.n == 100
    assert report.kappa == pytest.approx(1.0)
    assert report.gate_met is True
    assert report.disagreements == []


def test_compare_lists_every_disagreement(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    _write(human_p, [("egm-1", "include", None), ("egm-2", "include", None)], "human")
    _write(ai_p, [("egm-1", "include", None),
                  ("egm-2", "exclude", "not_primary")], "ai")

    report = compare(human_p, ai_p, gate=0.75)
    assert len(report.disagreements) == 1
    d = report.disagreements[0]
    assert d["record_id"] == "egm-2"
    assert d["human"] == "include" and d["ai"] == "exclude"
    assert d["ai_criterion"] == "not_primary"


def test_compare_fails_the_gate_on_poor_agreement(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    hp = [(f"egm-{n}", "include" if n % 2 else "exclude",
           None if n % 2 else "not_primary") for n in range(100)]
    ap = [(f"egm-{n}", "exclude" if n % 3 else "include",
           "not_primary" if n % 3 else None) for n in range(100)]
    _write(human_p, hp, "human")
    _write(ai_p, ap, "ai")

    assert compare(human_p, ai_p, gate=0.75).gate_met is False


def test_compare_raises_when_records_do_not_align(tmp_path):
    """Comparing different record sets would silently compute nonsense."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    _write(human_p, [("egm-1", "include", None)], "human")
    _write(ai_p, [("egm-2", "include", None)], "ai")

    with pytest.raises(ValueError, match="egm-1"):
        compare(human_p, ai_p, gate=0.75)


def test_compare_uses_the_latest_decision_when_one_supersedes_another(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    _write(human_p, [("egm-1", "include", None)], "human")
    append_decision(human_p, ScreeningDecision(
        record_id="egm-1", pmid="1", decision="exclude", criterion="not_human",
        confidence=None, reason=None, screener="human", model_id=None,
        prompt_sha256=None, stage="calibration",
        decided_at="2026-09-13T11:00:00Z", supersedes="2026-09-13T10:00:00Z",
    ))
    _write(ai_p, [("egm-1", "exclude", "not_human")], "ai")

    assert compare(human_p, ai_p, gate=0.75).disagreements == []


# --- Fix 4: comparing a log against itself must not silently pass the gate -


def test_compare_rejects_the_same_log_passed_as_both_human_and_ai(tmp_path):
    """compare(human_log, human_log) must not report a perfect, meaningless
    kappa=1.0 gate pass — that is what an accidental --human/--ai swap, or
    passing one path twice, would otherwise produce silently.
    """
    human_p = tmp_path / "h.jsonl"
    pairs = [(f"egm-{n}", "include" if n < 5 else "exclude",
              None if n < 5 else "not_primary") for n in range(10)]
    _write(human_p, pairs, "human")

    with pytest.raises(ValueError, match="screener"):
        compare(human_p, human_p, gate=0.75)


def test_compare_rejects_ai_log_passed_as_human(tmp_path):
    """Swapping --human and --ai must be caught, not silently accepted."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    pairs = [(f"egm-{n}", "include" if n < 5 else "exclude",
              None if n < 5 else "not_primary") for n in range(10)]
    _write(human_p, pairs, "human")
    _write(ai_p, pairs, "ai")

    with pytest.raises(ValueError, match="screener"):
        compare(ai_p, human_p, gate=0.75)  # swapped


# --- Fix 6: reports carry provenance, and refuse to blend two runs ---------


def test_agreement_report_carries_model_and_prompt_provenance(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    pairs = [(f"egm-{n}", "include" if n < 5 else "exclude",
              None if n < 5 else "not_primary") for n in range(10)]
    _write(human_p, pairs, "human")
    _write(ai_p, pairs, "ai")

    report = compare(human_p, ai_p, gate=0.75)
    assert report.model_id == "claude-opus-5"
    assert report.prompt_sha256 == "a" * 64


def test_agreement_report_raises_when_ai_log_spans_two_models(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    pairs = [(f"egm-{n}", "include", None) for n in range(5)]
    _write(human_p, pairs, "human")
    _write(ai_p, pairs, "ai")
    append_decision(human_p, ScreeningDecision(
        record_id="egm-other", pmid="99", decision="include", criterion=None,
        confidence=None, reason=None, screener="human", model_id=None,
        prompt_sha256=None, stage="calibration",
        decided_at="2026-09-13T10:00:00Z", supersedes=None,
    ))
    append_decision(ai_p, ScreeningDecision(
        record_id="egm-other", pmid="99", decision="include", criterion=None,
        confidence=0.9, reason="r", screener="ai", model_id="claude-sonnet-5",
        prompt_sha256="a" * 64, stage="calibration",
        decided_at="2026-09-13T10:00:00Z", supersedes=None,
    ))

    with pytest.raises(ValueError, match="more than one AI model"):
        compare(human_p, ai_p, gate=0.75)
