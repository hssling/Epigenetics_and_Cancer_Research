"""The three CLI wrappers. Thin, but they must not swallow failures."""
import json

import pytest

from pipeline import report_agreement, report_recall, run_screening
from pipeline.screen_schema import ScreeningDecision, append_decision


def _ai(path, record_id, decision, confidence, criterion=None):
    append_decision(path, ScreeningDecision(
        record_id=record_id, pmid=record_id.split("-")[1], decision=decision,
        criterion=criterion, confidence=confidence, reason="r", screener="ai",
        model_id="claude-opus-5", prompt_sha256="a" * 64, stage="screening",
        decided_at="2026-09-13T10:00:00Z", supersedes=None,
    ))


def _human(path, record_id, decision, criterion=None, stage="validation"):
    append_decision(path, ScreeningDecision(
        record_id=record_id, pmid=record_id.split("-")[1], decision=decision,
        criterion=criterion, confidence=None, reason=None, screener="human",
        model_id=None, prompt_sha256=None, stage=stage,
        decided_at="2026-09-13T10:00:00Z", supersedes=None,
    ))


def test_run_screening_loads_records_from_a_corpus_payload(tmp_path, mocker):
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps({"manifest": {}, "records": [
        {"record_id": "egm-1", "pmid": "1", "title": "T", "abstract": "A",
         "year": 2020, "journal": "J"}]}), encoding="utf-8")

    screen = mocker.patch.object(
        run_screening.ai_screener, "screen_sample",
        return_value={"total": 1, "screened": 1, "skipped": 0},
    )
    mocker.patch.object(run_screening.anthropic, "Anthropic")

    run_screening.run(corpus, "claude-opus-5", tmp_path / "d.jsonl",
                      tmp_path / "u.jsonl", "screening")

    assert screen.call_args.args[1][0]["record_id"] == "egm-1"


def test_run_screening_accepts_a_bare_list_sample(tmp_path, mocker):
    """Drawn samples are a bare list; the corpus is {manifest, records}."""
    sample = tmp_path / "sample.json"
    sample.write_text(json.dumps([
        {"record_id": "egm-9", "pmid": "9", "title": "T", "abstract": "A",
         "year": 2020, "journal": "J"}]), encoding="utf-8")

    screen = mocker.patch.object(
        run_screening.ai_screener, "screen_sample",
        return_value={"total": 1, "screened": 1, "skipped": 0},
    )
    mocker.patch.object(run_screening.anthropic, "Anthropic")

    run_screening.run(sample, "claude-opus-5", tmp_path / "d.jsonl",
                      tmp_path / "u.jsonl", "calibration")

    assert screen.call_args.args[1][0]["record_id"] == "egm-9"


def test_run_screening_propagates_a_screener_error(tmp_path, mocker):
    """A failed run must fail, not report a partial success."""
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps({"records": [
        {"record_id": "egm-1", "pmid": "1", "title": "T", "abstract": "A",
         "year": 2020, "journal": "J"}]}), encoding="utf-8")

    mocker.patch.object(run_screening.anthropic, "Anthropic")
    mocker.patch.object(
        run_screening.ai_screener, "screen_sample",
        side_effect=run_screening.ai_screener.ScreenerError("boom"),
    )

    with pytest.raises(run_screening.ai_screener.ScreenerError):
        run_screening.run(corpus, "claude-opus-5", tmp_path / "d.jsonl",
                          tmp_path / "u.jsonl", "screening")


def test_report_agreement_writes_a_json_report(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    for n in range(20):
        rid = f"egm-{n}"
        decision = "include" if n < 8 else "exclude"
        criterion = None if n < 8 else "not_primary"
        _human(human_p, rid, decision, criterion, stage="calibration")
        _ai(ai_p, rid, decision, 0.9, criterion)

    out = tmp_path / "agreement.json"
    report = report_agreement.run(human_p, ai_p, out, gate=0.75)

    assert report.gate_met is True
    assert json.loads(out.read_text(encoding="utf-8"))["kappa"] == 1.0


def test_report_recall_writes_a_json_report(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    records = []
    for n in range(50):
        rid = f"egm-{n}"
        _ai(ai_p, rid, "exclude", 0.9, "not_primary")
        _human(human_p, rid, "exclude", "not_primary")
        records.append({"record_id": rid})

    sample_p = tmp_path / "sample.json"
    sample_p.write_text(json.dumps(records), encoding="utf-8")

    out = tmp_path / "recall.json"
    report = report_recall.run(human_p, ai_p, sample_p, out)

    assert report.false_negatives == 0
    assert json.loads(out.read_text(encoding="utf-8"))["sensitivity"] == 1.0


def test_report_recall_raises_on_a_partial_sample(tmp_path):
    """The registered denominator is the full drawn sample, not whatever
    subset happens to have a human decision recorded."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    records = []
    for n in range(50):
        rid = f"egm-{n}"
        _ai(ai_p, rid, "exclude", 0.9, "not_primary")
        records.append({"record_id": rid})
        if n < 10:
            _human(human_p, rid, "exclude", "not_primary")

    sample_p = tmp_path / "sample.json"
    sample_p.write_text(json.dumps(records), encoding="utf-8")

    with pytest.raises(ValueError, match="partial sample"):
        report_recall.run(human_p, ai_p, sample_p, tmp_path / "recall.json")
