"""Drawing the two registered samples."""
import json

import pytest

from pipeline.draw_sample import (
    draw_calibration,
    draw_validation,
    screened_text,
    stratum_sizes,
)
from pipeline.screen_schema import ScreeningDecision, append_decision


def _corpus(tmp_path, n=1000):
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps({"manifest": {"record_count": n}, "records": [
        {"record_id": f"egm-{i:06d}", "pmid": str(i), "title": f"T{i}",
         "abstract": f"A{i}", "year": 2020, "journal": "J"} for i in range(n)
    ]}), encoding="utf-8")
    return path


def _batches(tmp_path, corpus_path, dirname="batches"):
    """Write the batch files the screener would have been given.

    The batch set is the only artefact that records the text the model was
    shown, so the validation draw is checked against it rather than against
    the corpus, which is rewritten by later pipeline steps.
    """
    records = json.loads(corpus_path.read_text(encoding="utf-8"))["records"]
    out = tmp_path / dirname
    out.mkdir()
    for number, start in enumerate(range(0, len(records), 500), start=1):
        (out / f"batch_{number:04d}.json").write_text(json.dumps({
            "batch_id": f"batch_{number:04d}",
            "stage": "screening",
            "prompt_sha256": "a" * 64,
            "records": [
                {k: r[k] for k in
                 ("record_id", "pmid", "title", "abstract", "year", "journal")}
                for r in records[start:start + 500]
            ],
        }), encoding="utf-8")
    return out


def test_calibration_draw_is_the_registered_size(tmp_path):
    out = tmp_path / "cal.json"
    counts = draw_calibration(_corpus(tmp_path), out, n=300, seed=20260913)
    assert counts["drawn"] == 300
    records = json.loads(out.read_text(encoding="utf-8"))
    assert len({r["record_id"] for r in records}) == 300


def test_calibration_draw_is_reproducible_from_the_seed(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    corpus = _corpus(tmp_path)
    draw_calibration(corpus, a, n=300, seed=20260913)
    draw_calibration(corpus, b, n=300, seed=20260913)
    assert a.read_text(encoding="utf-8") == b.read_text(encoding="utf-8")


def test_different_seed_draws_a_different_sample(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    corpus = _corpus(tmp_path)
    draw_calibration(corpus, a, n=300, seed=1)
    draw_calibration(corpus, b, n=300, seed=2)
    assert a.read_text(encoding="utf-8") != b.read_text(encoding="utf-8")


def test_refuses_to_overwrite_an_existing_sample(tmp_path):
    """A redrawn sample would silently invalidate screening already done."""
    out = tmp_path / "cal.json"
    corpus = _corpus(tmp_path)
    draw_calibration(corpus, out, n=300, seed=1)
    with pytest.raises(FileExistsError):
        draw_calibration(corpus, out, n=300, seed=2)


def _ai_exclusion(path, record_id, confidence):
    append_decision(path, ScreeningDecision(
        record_id=record_id, pmid=record_id.split("-")[1], decision="exclude",
        criterion="not_primary", confidence=confidence, reason="r", screener="ai",
        model_id="claude-opus-5", prompt_sha256="a" * 64, stage="screening",
        decided_at="2026-09-13T10:00:00Z", supersedes=None,
    ))


def test_stratum_sizes_counts_exclusions_by_confidence(tmp_path):
    decisions = tmp_path / "d.jsonl"
    for i in range(10):
        _ai_exclusion(decisions, f"egm-{i}", 0.2)
    for i in range(10, 40):
        _ai_exclusion(decisions, f"egm-{i}", 0.95)

    assert stratum_sizes(decisions) == {"low": 10, "mid": 0, "high": 30}


def test_validation_draw_oversamples_low_confidence(tmp_path):
    corpus, decisions = _corpus(tmp_path), tmp_path / "d.jsonl"
    for i in range(100):
        _ai_exclusion(decisions, f"egm-{i:06d}", 0.2)
    for i in range(100, 900):
        _ai_exclusion(decisions, f"egm-{i:06d}", 0.95)

    out = tmp_path / "val.json"
    counts = draw_validation(
        corpus, decisions, out, {"low": 50, "mid": 0, "high": 50}, seed=20260913,
        batches_dir=_batches(tmp_path, corpus),
    )

    assert counts["drawn"] == 100
    records = json.loads(out.read_text(encoding="utf-8"))
    assert len(records) == 100


def test_validation_draw_raises_when_a_stratum_is_too_small(tmp_path):
    corpus, decisions = _corpus(tmp_path), tmp_path / "d.jsonl"
    for i in range(5):
        _ai_exclusion(decisions, f"egm-{i:06d}", 0.2)

    with pytest.raises(ValueError, match="only 5 available"):
        draw_validation(
            corpus, decisions, tmp_path / "v.json", {"low": 50}, seed=1,
            batches_dir=_batches(tmp_path, corpus),
        )


# --- the corpus is a live artefact; the batch files are not ------------------


def test_a_corpus_edited_since_screening_refuses_the_draw(tmp_path):
    """The attack an audit landed: redraw after `backfill_abstracts` ran.

    The seed is deterministic and record_ids are stable, so the same ids come
    back and the sample looks correct. 82 of them carried an abstract the
    model had never seen. The investigator screens one text, the AI screened
    another, and every resulting disagreement is scored as a recall failure
    against the AI.
    """
    corpus, decisions = _corpus(tmp_path), tmp_path / "d.jsonl"
    for i in range(100):
        _ai_exclusion(decisions, f"egm-{i:06d}", 0.2)
    batches = _batches(tmp_path, corpus)

    # backfill: the corpus gains abstracts the screener never saw
    payload = json.loads(corpus.read_text(encoding="utf-8"))
    for record in payload["records"][:60]:
        record["abstract"] = "a newly backfilled abstract"
    corpus.write_text(json.dumps(payload), encoding="utf-8")

    out = tmp_path / "val.json"
    with pytest.raises(ValueError, match="differs from the text the screener"):
        draw_validation(
            corpus, decisions, out, {"low": 50}, seed=20260913,
            batches_dir=batches,
        )
    assert not out.exists(), "a refused draw must not leave a sample on disk"


def test_an_unchanged_corpus_draws_normally(tmp_path):
    """The check must not make a legitimate draw impossible."""
    corpus, decisions = _corpus(tmp_path), tmp_path / "d.jsonl"
    for i in range(100):
        _ai_exclusion(decisions, f"egm-{i:06d}", 0.2)

    counts = draw_validation(
        corpus, decisions, tmp_path / "val.json", {"low": 50}, seed=20260913,
        batches_dir=_batches(tmp_path, corpus),
    )
    assert counts["drawn"] == 50


def test_a_record_that_was_never_batched_refuses_the_draw(tmp_path):
    corpus, decisions = _corpus(tmp_path), tmp_path / "d.jsonl"
    for i in range(100):
        _ai_exclusion(decisions, f"egm-{i:06d}", 0.2)
    batches = _batches(tmp_path, corpus)
    for path in batches.glob("batch_*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["records"] = payload["records"][20:]
        path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="never in a batch file"):
        draw_validation(
            corpus, decisions, tmp_path / "val.json", {"low": 50}, seed=20260913,
            batches_dir=batches,
        )


def test_screened_text_refuses_a_directory_with_no_batches(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError, match="no batch files"):
        screened_text(empty)
