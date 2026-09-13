"""The human screening app. Durability and blindness are the properties."""
import json

import pytest

from pipeline import screen_app
from pipeline.screen_schema import CRITERIA, read_decisions


def _sample(tmp_path, n=3):
    path = tmp_path / "sample.json"
    path.write_text(json.dumps([
        {"record_id": f"egm-{i}", "pmid": str(i), "title": f"Study {i}",
         "abstract": f"Abstract {i}", "year": 2020, "journal": "J Epi"}
        for i in range(n)
    ]), encoding="utf-8")
    return path


def test_queue_starts_with_every_record(tmp_path):
    queue = screen_app.load_queue(_sample(tmp_path, 3), tmp_path / "out.jsonl")
    assert [r["record_id"] for r in queue] == ["egm-0", "egm-1", "egm-2"]


def test_queue_resumes_after_partial_screening(tmp_path):
    sample, out = _sample(tmp_path, 3), tmp_path / "out.jsonl"
    record = json.loads(sample.read_text(encoding="utf-8"))[0]
    screen_app.record_decision(out, record, "include", None, "calibration")

    assert [r["record_id"] for r in screen_app.load_queue(sample, out)] == [
        "egm-1", "egm-2"
    ]


def test_decision_is_written_immediately(tmp_path):
    sample, out = _sample(tmp_path, 1), tmp_path / "out.jsonl"
    record = json.loads(sample.read_text(encoding="utf-8"))[0]

    screen_app.record_decision(out, record, "exclude", "not_primary", "calibration")

    decisions = read_decisions(out)
    assert len(decisions) == 1
    assert decisions[0].decision == "exclude"
    assert decisions[0].criterion == "not_primary"
    assert decisions[0].screener == "human"
    assert decisions[0].model_id is None


def test_amending_a_decision_appends_with_supersedes(tmp_path):
    sample, out = _sample(tmp_path, 1), tmp_path / "out.jsonl"
    record = json.loads(sample.read_text(encoding="utf-8"))[0]

    screen_app.record_decision(out, record, "include", None, "calibration")
    screen_app.record_decision(out, record, "exclude", "not_human", "calibration")

    decisions = read_decisions(out)
    assert len(decisions) == 2
    assert decisions[1].supersedes == decisions[0].decided_at


def test_page_shows_the_record_and_all_seven_criteria(tmp_path):
    record = {"record_id": "egm-1", "pmid": "1", "title": "A Distinctive Title",
              "abstract": "A Distinctive Abstract", "year": 2020, "journal": "J Epi"}
    html = screen_app.build_page(record, position=5, total=300, elapsed_s=120.0)

    assert "A Distinctive Title" in html
    assert "A Distinctive Abstract" in html
    assert "5" in html and "300" in html
    for criterion in CRITERIA:
        assert criterion in html


def test_module_has_no_path_by_which_an_ai_decision_could_reach_the_page():
    """Blindness is structural, not a matter of discipline.

    Asserted on the interfaces rather than by grepping for the word
    "confidence" — record_decision legitimately writes confidence=None for a
    human decision, so a naive text scan would fail on correct code.
    """
    import inspect

    # build_page can only ever see one record and its position.
    assert list(inspect.signature(screen_app.build_page).parameters) == [
        "record", "position", "total", "elapsed_s",
    ]
    # No public function accepts a second decision log to read from.
    for name in ("load_queue", "record_decision", "serve"):
        params = list(inspect.signature(getattr(screen_app, name)).parameters)
        assert not any("ai" in p.lower() for p in params), f"{name} takes {params}"

    source = inspect.getsource(screen_app)
    assert 'screener == "ai"' not in source
    assert "ai_decisions" not in source


def test_missing_abstract_is_shown_explicitly(tmp_path):
    record = {"record_id": "egm-1", "pmid": "1", "title": "T", "abstract": None,
              "year": 2020, "journal": "J"}
    assert "no abstract" in screen_app.build_page(record, 1, 10, 0.0).lower()


def test_record_decision_rejects_an_exclusion_without_a_criterion(tmp_path):
    sample, out = _sample(tmp_path, 1), tmp_path / "out.jsonl"
    record = json.loads(sample.read_text(encoding="utf-8"))[0]
    with pytest.raises(Exception):
        screen_app.record_decision(out, record, "exclude", None, "calibration")
