import json

import pytest
from pydantic import ValidationError

from pipeline.provenance import RunManifest, query_hash, write_artefact


def test_query_hash_is_stable_and_short():
    assert query_hash("epigenetics AND cancer") == query_hash("epigenetics AND cancer")
    assert len(query_hash("x")) == 12


def test_query_hash_differs_for_different_queries():
    assert query_hash("a AND b") != query_hash("a OR b")


def test_manifest_records_the_hash_of_its_query():
    m = RunManifest.create(query_string="q1", source_db="pubmed", record_count=5, notes=None)
    assert m.query_hash == query_hash("q1")
    assert m.run_at.endswith("Z")


def test_run_at_is_genuinely_utc_not_local_time_mislabelled():
    """Would fail if run_at used local time with a hardcoded 'Z' suffix.

    Parses run_at back as UTC and compares it to a UTC instant captured
    around the call. On any machine whose local time differs from UTC,
    a mislabelled local timestamp lands far outside this window.
    """
    from datetime import datetime, timezone

    before = datetime.now(timezone.utc)
    manifest = RunManifest.create(
        query_string="q", source_db="pubmed", record_count=0, notes=None
    )
    after = datetime.now(timezone.utc)

    parsed = datetime.strptime(manifest.run_at, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )

    # One second of slack each side absorbs the format's whole-second truncation.
    assert before.replace(microsecond=0) <= parsed <= after, (
        f"run_at {manifest.run_at} is not within the UTC window "
        f"[{before.isoformat()}, {after.isoformat()}] — likely local time "
        f"mislabelled as UTC"
    )


def test_manifest_rejects_negative_count():
    with pytest.raises(ValidationError):
        RunManifest.create(query_string="q", source_db="pubmed", record_count=-1, notes=None)


def test_manifest_requires_explicit_notes():
    with pytest.raises(TypeError):
        RunManifest.create(query_string="q", source_db="pubmed", record_count=1)


def test_write_artefact_refuses_count_mismatch(tmp_path):
    m = RunManifest.create(query_string="q", source_db="pubmed", record_count=2, notes=None)
    with pytest.raises(ValueError, match="record_count"):
        write_artefact(tmp_path / "out.json", [{"a": 1}], m)


def test_write_artefact_round_trips(tmp_path):
    m = RunManifest.create(query_string="q", source_db="pubmed", record_count=1, notes=None)
    out = tmp_path / "out.json"
    write_artefact(out, [{"a": 1}], m)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["manifest"]["query_hash"] == query_hash("q")
    assert payload["records"] == [{"a": 1}]


def test_write_artefact_refuses_to_overwrite(tmp_path):
    """Raw exports are append-only (global constraint)."""
    m = RunManifest.create(query_string="q", source_db="pubmed", record_count=1, notes=None)
    out = tmp_path / "out.json"
    write_artefact(out, [{"a": 1}], m)
    with pytest.raises(FileExistsError):
        write_artefact(out, [{"a": 2}], m)
