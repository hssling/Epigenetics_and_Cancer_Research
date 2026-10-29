"""Collecting subagent decisions into the append-only log.

This is the integrity gate for the whole subagent screening path. The failure
it exists to catch is quiet: a subagent that returns 49 decisions for a
50-record batch, or invents a record_id, loses or corrupts records with no
other signal anywhere in the pipeline. Every check below is therefore tested
for the raise AND for leaving the log untouched.
"""
import json
import pathlib

import pytest

from pipeline import collect_batches
from pipeline.screen_schema import ScreeningDecision, append_decision, read_decisions

SHA = "a" * 64
MODEL = "claude-opus-5"


def _batch(tmp_path, n=50, stage="screening", sha=SHA, name="batch_0001.json",
           pmid=True, start=0):
    records = [
        {
            "record_id": f"egm-{i:06d}",
            "pmid": str(1000 + i) if pmid else None,
            "title": f"Title {i}",
            "abstract": "An abstract.",
            "year": 2020,
            "journal": "J Epigenet",
        }
        for i in range(start, start + n)
    ]
    path = tmp_path / name
    path.write_text(
        json.dumps({
            "batch_id": name.removesuffix(".json"),
            "stage": stage,
            "prompt_sha256": sha,
            "records": records,
        }, indent=2),
        encoding="utf-8",
    )
    return path


def _decision(record, decision="exclude", criterion="not_primary", **overrides):
    base = dict(
        record_id=record["record_id"],
        pmid=record["pmid"],
        decision=decision,
        criterion=criterion,
        confidence=0.9,
        reason="Narrative review, no primary data.",
        screener="ai",
        model_id=MODEL,
        prompt_sha256=SHA,
        stage="screening",
        decided_at="2026-09-14T10:00:00Z",
        supersedes=None,
    )
    return {**base, **overrides}


def _write_decisions(path, rows):
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def _all(batch_path, **overrides):
    records = json.loads(batch_path.read_text(encoding="utf-8"))["records"]
    return [_decision(r, **overrides) for r in records]


def _snapshot(path):
    return path.read_bytes() if path.exists() else None


# --- coverage: the load-bearing checks ------------------------------------

def test_missing_decision_raises(tmp_path):
    """49 decisions for a 50-record batch is a lost record, not a short batch."""
    batch = _batch(tmp_path, 50)
    rows = _all(batch)
    dropped = rows.pop(17)
    decisions = _write_decisions(tmp_path / "d.jsonl", rows)
    log = tmp_path / "log.jsonl"

    with pytest.raises(collect_batches.CollectionError) as excinfo:
        collect_batches.collect(batch, decisions, log, MODEL)

    message = str(excinfo.value)
    assert "1" in message
    assert dropped["record_id"] in message
    assert not log.exists()


def test_missing_decisions_message_names_a_count_and_five_ids(tmp_path):
    batch = _batch(tmp_path, 50)
    rows = _all(batch)[:42]
    decisions = _write_decisions(tmp_path / "d.jsonl", rows)

    with pytest.raises(collect_batches.CollectionError, match="8 decision"):
        collect_batches.collect(batch, decisions, tmp_path / "log.jsonl", MODEL)


def test_hallucinated_record_id_raises(tmp_path):
    """A decision for a record not in this batch is a fabricated id or a
    crossed-over batch; either way the log must not absorb it."""
    batch = _batch(tmp_path, 10)
    rows = _all(batch)
    rows[3]["record_id"] = "egm-999999"
    decisions = _write_decisions(tmp_path / "d.jsonl", rows)
    log = tmp_path / "log.jsonl"

    with pytest.raises(collect_batches.CollectionError) as excinfo:
        collect_batches.collect(batch, decisions, log, MODEL)

    assert "egm-999999" in str(excinfo.value)
    assert not log.exists()


def test_extra_decision_beyond_the_batch_raises(tmp_path):
    batch = _batch(tmp_path, 10)
    rows = _all(batch)
    rows.append(_decision(
        {"record_id": "egm-000999", "pmid": "9999"}
    ))
    decisions = _write_decisions(tmp_path / "d.jsonl", rows)

    with pytest.raises(collect_batches.CollectionError, match="egm-000999"):
        collect_batches.collect(batch, decisions, tmp_path / "log.jsonl", MODEL)


def test_duplicate_record_id_in_the_decisions_raises(tmp_path):
    """Two judgements for one record inside one batch: which one is the datum?"""
    batch = _batch(tmp_path, 10)
    rows = _all(batch)
    rows.append(_decision(
        {"record_id": "egm-000004", "pmid": "1004"}, decision="include",
        criterion=None,
    ))
    decisions = _write_decisions(tmp_path / "d.jsonl", rows)

    with pytest.raises(collect_batches.CollectionError, match="egm-000004"):
        collect_batches.collect(batch, decisions, tmp_path / "log.jsonl", MODEL)


def test_nothing_is_written_when_a_check_fails(tmp_path):
    """The most important test here: a check that raises AFTER appending half
    the batch is not a check. The log must be byte-identical afterwards."""
    batch = _batch(tmp_path, 50)
    log = tmp_path / "log.jsonl"

    # A pre-existing, unrelated log so the assertion is about content, not
    # merely about the file staying absent.
    append_decision(log, ScreeningDecision(**_decision(
        {"record_id": "egm-unrelated", "pmid": "42"}
    )))
    before = _snapshot(log)

    rows = _all(batch)[:-1]
    decisions = _write_decisions(tmp_path / "d.jsonl", rows)

    with pytest.raises(collect_batches.CollectionError):
        collect_batches.collect(batch, decisions, log, MODEL)

    assert _snapshot(log) == before
    assert len(read_decisions(log)) == 1


def test_nothing_is_written_when_the_last_check_fails(tmp_path):
    """The idempotence guard is the final check; a failure there must also
    leave the log untouched, not append the batch a second time."""
    batch = _batch(tmp_path, 10)
    decisions = _write_decisions(tmp_path / "d.jsonl", _all(batch))
    log = tmp_path / "log.jsonl"

    collect_batches.collect(batch, decisions, log, MODEL)
    before = _snapshot(log)

    with pytest.raises(collect_batches.CollectionError):
        collect_batches.collect(batch, decisions, log, MODEL)

    assert _snapshot(log) == before


# --- provenance -----------------------------------------------------------

def test_prompt_sha256_mismatch_raises(tmp_path):
    """Decisions made against a different prompt are a different experiment."""
    batch = _batch(tmp_path, 5)
    decisions = _write_decisions(tmp_path / "d.jsonl", _all(batch, prompt_sha256="b" * 64))

    with pytest.raises(collect_batches.CollectionError, match="prompt_sha256"):
        collect_batches.collect(batch, decisions, tmp_path / "log.jsonl", MODEL)


def test_model_id_mismatch_raises(tmp_path):
    batch = _batch(tmp_path, 5)
    decisions = _write_decisions(tmp_path / "d.jsonl", _all(batch, model_id="other-model"))

    with pytest.raises(collect_batches.CollectionError, match="model_id"):
        collect_batches.collect(batch, decisions, tmp_path / "log.jsonl", MODEL)


def test_stage_mismatch_raises(tmp_path):
    batch = _batch(tmp_path, 5, stage="calibration")
    decisions = _write_decisions(tmp_path / "d.jsonl", _all(batch, stage="screening"))

    with pytest.raises(collect_batches.CollectionError, match="stage"):
        collect_batches.collect(batch, decisions, tmp_path / "log.jsonl", MODEL)


def test_a_human_screener_decision_in_an_ai_batch_raises(tmp_path):
    batch = _batch(tmp_path, 5)
    rows = _all(batch)
    rows[0].update(screener="human", model_id=None, prompt_sha256=None,
                   confidence=None, reason=None)
    decisions = _write_decisions(tmp_path / "d.jsonl", rows)

    with pytest.raises(collect_batches.CollectionError, match="screener"):
        collect_batches.collect(batch, decisions, tmp_path / "log.jsonl", MODEL)


def test_pmid_mismatch_raises(tmp_path):
    """A decision carrying another record's pmid means the batch was misread."""
    batch = _batch(tmp_path, 5)
    rows = _all(batch)
    rows[2]["pmid"] = "7777777"
    decisions = _write_decisions(tmp_path / "d.jsonl", rows)

    with pytest.raises(collect_batches.CollectionError, match="pmid"):
        collect_batches.collect(batch, decisions, tmp_path / "log.jsonl", MODEL)


def test_a_pmid_invented_for_a_record_that_has_none_raises(tmp_path):
    batch = _batch(tmp_path, 5, pmid=False)
    rows = _all(batch)
    rows[1]["pmid"] = "123456"
    decisions = _write_decisions(tmp_path / "d.jsonl", rows)

    with pytest.raises(collect_batches.CollectionError, match="pmid"):
        collect_batches.collect(batch, decisions, tmp_path / "log.jsonl", MODEL)


def test_a_null_pmid_on_both_sides_is_accepted(tmp_path):
    """Europe PMC preprints have no PMID; they must still be screenable."""
    batch = _batch(tmp_path, 5, pmid=False)
    decisions = _write_decisions(tmp_path / "d.jsonl", _all(batch))
    log = tmp_path / "log.jsonl"

    counts = collect_batches.collect(batch, decisions, log, MODEL)

    assert counts["collected"] == 5
    assert all(d.pmid is None for d in read_decisions(log))


# --- parsing --------------------------------------------------------------

def test_a_malformed_line_raises_rather_than_being_skipped(tmp_path):
    batch = _batch(tmp_path, 5)
    path = tmp_path / "d.jsonl"
    _write_decisions(path, _all(batch))
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{not json\n")

    with pytest.raises(collect_batches.CollectionError):
        collect_batches.collect(batch, path, tmp_path / "log.jsonl", MODEL)


def test_a_schema_violating_decision_raises(tmp_path):
    """An exclusion with no criterion cannot be reported in PRISMA."""
    batch = _batch(tmp_path, 5)
    rows = _all(batch)
    rows[0]["criterion"] = None
    decisions = _write_decisions(tmp_path / "d.jsonl", rows)

    with pytest.raises(collect_batches.CollectionError):
        collect_batches.collect(batch, decisions, tmp_path / "log.jsonl", MODEL)


def test_a_missing_decisions_file_raises(tmp_path):
    batch = _batch(tmp_path, 5)
    with pytest.raises(collect_batches.CollectionError):
        collect_batches.collect(
            batch, tmp_path / "absent.jsonl", tmp_path / "log.jsonl", MODEL
        )


# --- idempotence ----------------------------------------------------------

def test_recollecting_an_already_collected_batch_raises(tmp_path):
    batch = _batch(tmp_path, 10)
    decisions = _write_decisions(tmp_path / "d.jsonl", _all(batch))
    log = tmp_path / "log.jsonl"

    collect_batches.collect(batch, decisions, log, MODEL)

    with pytest.raises(collect_batches.CollectionError, match="already"):
        collect_batches.collect(batch, decisions, log, MODEL)

    assert len(read_decisions(log)) == 10


def test_the_same_records_at_a_different_stage_are_not_blocked(tmp_path):
    """Calibration and screening are separate passes over the same records."""
    cal = _batch(tmp_path, 5, stage="calibration", name="batch_0001.json")
    log = tmp_path / "log.jsonl"
    cal_rows = _write_decisions(
        tmp_path / "cal.jsonl", _all(cal, stage="calibration")
    )
    collect_batches.collect(cal, cal_rows, log, MODEL)

    scr = _batch(tmp_path, 5, stage="screening", name="batch_0002.json")
    scr_rows = _write_decisions(tmp_path / "scr.jsonl", _all(scr))
    collect_batches.collect(scr, scr_rows, log, MODEL)

    assert len(read_decisions(log)) == 10


# --- happy path -----------------------------------------------------------

def test_a_clean_batch_is_appended_and_counted(tmp_path):
    batch = _batch(tmp_path, 10)
    records = json.loads(batch.read_text(encoding="utf-8"))["records"]
    rows = [
        _decision(records[0], decision="include", criterion=None),
        _decision(records[1], decision="include", criterion=None),
        _decision(records[2], decision="unclear", criterion=None),
        *[_decision(r) for r in records[3:]],
    ]
    decisions = _write_decisions(tmp_path / "d.jsonl", rows)
    log = tmp_path / "log.jsonl"

    counts = collect_batches.collect(batch, decisions, log, MODEL)

    assert counts == {"collected": 10, "include": 2, "exclude": 7, "unclear": 1}
    logged = read_decisions(log)
    assert len(logged) == 10
    assert {d.record_id for d in logged} == {r["record_id"] for r in records}
    assert all(d.screener == "ai" for d in logged)
    assert all(d.model_id == MODEL for d in logged)
    assert all(d.prompt_sha256 == SHA for d in logged)


# --- collect_all ----------------------------------------------------------

def _pair(tmp_path, number, n=5, **kw):
    name = f"batch_{number:04d}.json"
    kw.setdefault("start", number * 1000)
    batch = _batch(tmp_path, n, name=name, **kw)
    decisions = _write_decisions(
        tmp_path / f"batch_{number:04d}_decisions.jsonl", _all(batch)
    )
    return batch, decisions


def test_collect_all_collects_every_batch_with_a_decisions_file(tmp_path):
    for number in (1, 2, 3):
        _pair(tmp_path, number, n=4)
    log = tmp_path / "log.jsonl"

    summary = collect_batches.collect_all(tmp_path, log, MODEL)

    assert summary["batches"] == 3
    assert summary["collected"] == 12
    assert summary["pending"] == []
    assert len(read_decisions(log)) == 12


def test_collect_all_reports_batches_without_decisions_as_pending(tmp_path):
    _pair(tmp_path, 1, n=4)
    _batch(tmp_path, 4, name="batch_0002.json", start=2000)
    log = tmp_path / "log.jsonl"

    summary = collect_batches.collect_all(tmp_path, log, MODEL)

    assert summary["batches"] == 1
    assert summary["collected"] == 4
    assert summary["pending"] == ["batch_0002"]


def test_collect_all_stops_on_the_first_integrity_failure(tmp_path):
    _pair(tmp_path, 1, n=4)
    bad = _batch(tmp_path, 4, name="batch_0002.json", start=2000)
    _write_decisions(
        tmp_path / "batch_0002_decisions.jsonl", _all(bad)[:-1]
    )
    _pair(tmp_path, 3, n=4)
    log = tmp_path / "log.jsonl"

    with pytest.raises(collect_batches.CollectionError):
        collect_batches.collect_all(tmp_path, log, MODEL)

    # Batch 1 was already committed; batch 3 must not have been reached.
    logged = {d.record_id for d in read_decisions(log)}
    assert len(logged) == 4


# --- CLI ------------------------------------------------------------------

def test_cli_collects_a_batch(tmp_path, monkeypatch, capsys):
    batch = _batch(tmp_path, 5)
    decisions = _write_decisions(tmp_path / "d.jsonl", _all(batch))
    log = tmp_path / "log.jsonl"

    monkeypatch.setattr("sys.argv", [
        "collect_batches", "--batch", str(batch), "--decisions", str(decisions),
        "--log", str(log), "--model-id", MODEL,
    ])
    collect_batches.main()

    assert "collected: 5" in capsys.readouterr().out
    assert len(read_decisions(log)) == 5


def test_cli_propagates_a_collection_error(tmp_path, monkeypatch):
    batch = _batch(tmp_path, 5)
    decisions = _write_decisions(tmp_path / "d.jsonl", _all(batch)[:-1])

    monkeypatch.setattr("sys.argv", [
        "collect_batches", "--batch", str(batch), "--decisions", str(decisions),
        "--log", str(tmp_path / "log.jsonl"), "--model-id", MODEL,
    ])
    with pytest.raises(collect_batches.CollectionError):
        collect_batches.main()


# --- resumption: a long run gets interrupted, and must be restartable --------


def test_collect_all_resumes_after_an_interrupted_run(tmp_path):
    """The real case: a rate limit killed the run partway through.

    Before this, collect_all called collect() on every batch with a decisions
    file, and collect()'s double-counting guard raised on the first already
    collected batch -- so a partial run could not be resumed at all, which
    invites deleting the log and starting over.
    """
    for number in (1, 2):
        _pair(tmp_path, number, n=4)
    log = tmp_path / "log.jsonl"

    first = collect_batches.collect_all(tmp_path, log, MODEL)
    assert first["batches"] == 2 and first["collected"] == 8

    second = collect_batches.collect_all(tmp_path, log, MODEL)

    assert second["batches"] == 0, "an already-collected batch was collected twice"
    assert second["collected"] == 0
    assert sorted(second["already_collected"]) == ["batch_0001", "batch_0002"]
    assert len(read_decisions(log)) == 8, "the log grew on a no-op re-run"


def test_collect_all_collects_only_the_batches_that_are_new(tmp_path):
    """Exactly the state after an interruption: some done, some not."""
    b1, d1 = _pair(tmp_path, 1, n=4)
    _pair(tmp_path, 2, n=4)
    log = tmp_path / "log.jsonl"
    collect_batches.collect(b1, d1, log, MODEL)

    result = collect_batches.collect_all(tmp_path, log, MODEL)

    assert result["batches"] == 1
    assert result["collected"] == 4
    assert result["already_collected"] == ["batch_0001"]
    assert len(read_decisions(log)) == 8


def test_a_partially_collected_batch_still_raises(tmp_path):
    """Half a batch in the log means an append tore. That is NOT resumable.

    This is the half of the guard that must survive the resumption fix: topping
    up a partial batch could mix records from two different decisions files.
    """
    batch, _ = _pair(tmp_path, 1, n=4)
    log = tmp_path / "log.jsonl"
    records = json.loads(batch.read_text(encoding="utf-8"))["records"]

    append_decision(log, ScreeningDecision(
        record_id=records[0]["record_id"], pmid=records[0]["pmid"],
        decision="include", criterion=None, confidence=0.9, reason="r",
        screener="ai", model_id=MODEL, prompt_sha256=SHA, stage="screening",
        decided_at="2026-09-14T00:00:00Z", supersedes=None,
    ))

    with pytest.raises(collect_batches.CollectionError, match="PARTIALLY collected"):
        collect_batches.collect_all(tmp_path, log, MODEL)


# --- mechanically generated decisions ---------------------------------------


def test_templated_reasons_are_refused(tmp_path):
    """The failure this guard exists for, reproduced.

    A subagent asked to screen 200 records wrote a keyword-matching script and
    had it emit every decision, correctly stamped with model_id and
    prompt_sha256. Every other check here passes such a batch. The tell is that
    a script emits a handful of fixed reason strings where a screener writes a
    record-specific sentence each time.
    """
    batch, decisions_path = _pair(tmp_path, 1, n=40)
    rows = _all(batch)
    for i, row in enumerate(rows):
        row["reason"] = ("Study appears to be animal or in vitro."
                         if i % 2 else "No epigenetic marker measured.")
    _write_decisions(decisions_path, rows)
    log = tmp_path / "log.jsonl"

    with pytest.raises(collect_batches.CollectionError, match="distinct reason templates"):
        collect_batches.collect(batch, decisions_path, log, MODEL)

    assert not log.exists(), "a rejected batch must write nothing"


# Fragments that vary in what they SAY, not merely in an interpolated number.
# The earlier fixture here used f"Record-specific finding number {i}." and was
# treated as genuine; under the template rule it is the interpolation attack,
# which is what an audit used to defeat this guard. On the real 9,786-decision
# log the template ratio is 1.000, so nothing genuine is near the floor.
_SUBJECTS = ("cord blood", "saliva", "buccal swab", "whole blood", "placenta",
             "peripheral leukocytes", "tumour tissue", "dried blood spot")
_ASSAYS = ("EPIC array", "pyrosequencing", "RRBS", "targeted bisulfite PCR",
           "450K array", "nanopore sequencing", "MeDIP-seq", "WGBS")
_CONTEXTS = ("prenatal exposure cohort", "occupational surveillance",
             "school-based screening", "clinical trial arm", "registry linkage",
             "case-control design", "birth cohort follow-up", "pilot programme")


def _varied_reasons(n):
    return [
        f"{_ASSAYS[i % len(_ASSAYS)]} methylation in "
        f"{_SUBJECTS[(i // 3) % len(_SUBJECTS)]}, "
        f"{_CONTEXTS[(i // 7) % len(_CONTEXTS)]}."
        for i in range(n)
    ]


def test_genuine_per_record_reasons_pass(tmp_path):
    batch, decisions_path = _pair(tmp_path, 1, n=40)
    rows = _all(batch)
    for row, reason in zip(rows, _varied_reasons(len(rows))):
        row["reason"] = reason
    _write_decisions(decisions_path, rows)
    log = tmp_path / "log.jsonl"

    assert collect_batches.collect(batch, decisions_path, log, MODEL)["collected"] == 40


def test_a_fixed_reason_with_the_record_id_interpolated_is_refused(tmp_path):
    """The audit's one-line defeat of the raw distinct-string ratio.

    Every reason is unique as a string, so the old check scored 1.00 and passed
    a batch in which the judgement never varied at all.
    """
    batch, decisions_path = _pair(tmp_path, 1, n=40)
    rows = _all(batch)
    for row in rows:
        row["reason"] = f"No epigenetic marker measured ({row['record_id']})."
    _write_decisions(decisions_path, rows)
    log = tmp_path / "log.jsonl"

    with pytest.raises(collect_batches.CollectionError, match="interpolated identifiers"):
        collect_batches.collect(batch, decisions_path, log, MODEL)

    assert not log.exists(), "a rejected batch must write nothing"


def test_a_small_batch_is_not_judged_on_reason_variety(tmp_path):
    """Under 20 decisions, repetition is not evidence of a template."""
    batch, decisions_path = _pair(tmp_path, 1, n=5)
    rows = _all(batch)
    for row in rows:
        row["reason"] = "Same reason."
    _write_decisions(decisions_path, rows)

    assert collect_batches.collect(
        batch, decisions_path, tmp_path / "log.jsonl", MODEL)["collected"] == 5
