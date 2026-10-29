"""The human screening app. Durability and blindness are the properties."""
import json
import time

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


def test_stale_submission_over_http_is_refused_and_writes_nothing(tmp_path):
    """Drives the real /decide handler, because that is where the bug was.

    The previous version of this test called record_decision directly and
    passed against the pre-fix code, so it guarded nothing. A double keypress
    or key-repeat sends a second request for a record the queue has already
    advanced past; it must not be applied to the next record.
    """
    import threading
    import urllib.error
    import urllib.request

    sample = _sample(tmp_path, 3)
    out = tmp_path / "out.jsonl"

    thread = threading.Thread(
        target=screen_app.serve,
        args=(sample, out, "calibration", 8791),
        kwargs={"min_dwell_s": 0},
        daemon=True,
    )
    thread.start()

    def get(path):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:8791{path}", timeout=5) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    # Wait for the server to bind.
    for _ in range(50):
        try:
            get("/")
            break
        except Exception:
            time.sleep(0.1)

    # First decision for egm-0 is applied.
    status, _ = get("/decide?record_id=egm-0&decision=include&criterion=")
    assert status in (200, 303)
    assert len(read_decisions(out)) == 1

    after_first = out.read_text(encoding="utf-8")

    # The SAME request resent — a double keypress. The queue head is now egm-1.
    status, body = get("/decide?record_id=egm-0&decision=include&criterion=")
    assert status == 409, f"stale submission was accepted with status {status}"
    assert "Stale submission ignored" in body
    assert out.read_text(encoding="utf-8") == after_first, (
        "a stale submission wrote to the decision log"
    )

    decisions = read_decisions(out)
    assert len(decisions) == 1
    assert decisions[0].record_id == "egm-0", (
        "the stale decision was misattributed to the next record"
    )


def test_an_ai_decision_in_the_log_does_not_remove_a_record_from_the_human_queue(tmp_path):
    """Otherwise the sample silently shrinks and kappa is computed on a remainder."""
    from pipeline.screen_schema import ScreeningDecision, append_decision

    sample, out = _sample(tmp_path, 3), tmp_path / "out.jsonl"
    append_decision(out, ScreeningDecision(
        record_id="egm-0", pmid="0", decision="exclude", criterion="not_primary",
        confidence=0.9, reason="r", screener="ai", model_id="claude-opus-5",
        prompt_sha256="a" * 64, stage="calibration",
        decided_at="2026-09-13T10:00:00Z", supersedes=None,
    ))

    queue = screen_app.load_queue(sample, out)
    assert [r["record_id"] for r in queue] == ["egm-0", "egm-1", "egm-2"]


def test_page_renders_a_record_with_no_pmid(tmp_path):
    """Europe PMC preprints carry no PMID; the page must still render.

    698 of the 9,786 records in the combined corpus have pmid=None. Before this
    guard, build_page raised TypeError on the first of them -- which would have
    halted a human screening session partway through, after real work had
    already been done.
    """
    record = {"record_id": "egm-000123", "pmid": None, "source_id": "PPR:PPR9999",
              "title": "A Preprint Title", "abstract": "A Preprint Abstract",
              "year": 2025, "journal": None}

    html = screen_app.build_page(record, position=1, total=300, elapsed_s=0.0)

    assert "A Preprint Title" in html
    assert "PPR:PPR9999" in html, "the record must still be identifiable on screen"
    assert "PMID" not in html, "a record with no PMID must not be labelled with one"


def test_page_falls_back_to_a_stated_absence_when_there_is_no_identifier_at_all(tmp_path):
    record = {"record_id": "egm-000124", "pmid": None, "title": "T",
              "abstract": "A", "year": 2025, "journal": None}

    html = screen_app.build_page(record, position=1, total=300, elapsed_s=0.0)

    assert "no identifier" in html


def test_a_human_decision_on_a_pmid_less_record_round_trips(tmp_path):
    """The decision log must accept the absence, not just the page."""
    out = tmp_path / "decisions.jsonl"
    record = {"record_id": "egm-000123", "pmid": None, "source_id": "PPR:PPR9999",
              "title": "T", "abstract": "A", "year": 2025, "journal": None}

    screen_app.record_decision(out, record, "include", None, "calibration")

    (entry,) = read_decisions(out)
    assert entry.record_id == "egm-000123"
    assert entry.pmid is None
    assert entry.screener == "human"


def _start(sample, out, port, min_dwell_s):
    import threading
    import urllib.error
    import urllib.request

    threading.Thread(
        target=screen_app.serve,
        args=(sample, out, "calibration", port),
        kwargs={"min_dwell_s": min_dwell_s},
        daemon=True,
    ).start()

    def get(path):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    for _ in range(50):
        try:
            get("/favicon-probe-not-a-page")
            break
        except Exception:
            time.sleep(0.1)
    return get


def test_a_decision_faster_than_the_gate_floor_is_refused_and_writes_nothing(tmp_path):
    """A held key once wrote 300 includes in six minutes; the gate rejects that
    log after the fact, so the app must refuse it while it is happening."""
    out = tmp_path / "out.jsonl"
    get = _start(_sample(tmp_path, 3), out, 8792, min_dwell_s=1.0)

    get("/")
    status, body = get("/decide?record_id=egm-0&decision=include&criterion=")
    assert status == 429
    assert "Too fast" in body
    assert not out.exists() or read_decisions(out) == []

    time.sleep(1.1)
    status, _ = get("/decide?record_id=egm-0&decision=include&criterion=")
    assert status in (200, 303)
    assert [d.record_id for d in read_decisions(out)] == ["egm-0"]


def test_a_decision_for_a_record_never_shown_is_refused(tmp_path):
    """Typing the /decide URL directly must not bypass the dwell floor."""
    out = tmp_path / "out.jsonl"
    get = _start(_sample(tmp_path, 3), out, 8793, min_dwell_s=0.5)

    status, _ = get("/decide?record_id=egm-0&decision=include&criterion=")
    assert status == 429
    assert not out.exists() or read_decisions(out) == []


def test_reloading_the_page_does_not_restart_the_dwell_clock(tmp_path):
    out = tmp_path / "out.jsonl"
    get = _start(_sample(tmp_path, 3), out, 8794, min_dwell_s=0.6)

    get("/")
    time.sleep(0.7)
    get("/")  # reload: same record, clock keeps running
    status, _ = get("/decide?record_id=egm-0&decision=include&criterion=")
    assert status in (200, 303)


def test_page_ignores_key_repeat_and_early_keys(tmp_path):
    record = {"record_id": "egm-1", "pmid": "1", "year": 2020, "title": "T", "abstract": "A"}
    page = screen_app.build_page(record, 1, 300, 0.0)
    assert "ev.repeat || !ready" in page
    assert f"{screen_app.MIN_SECONDS_PER_DECISION * 1000:.0f}" in page
