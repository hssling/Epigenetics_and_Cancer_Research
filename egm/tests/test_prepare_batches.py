"""Slicing the corpus into subagent-sized batches.

The batch files are the input side of the screening loop. If a record is
dropped here it is never screened and never counted, and nothing downstream
would notice -- so completeness of the partition is tested directly.
"""
import json
import pathlib

import pytest

from pipeline import prepare_batches
from pipeline.prompt_loader import load_prompt


def _corpus(tmp_path, n, abstract="An abstract."):
    records = [
        {
            "record_id": f"egm-{i:06d}",
            "pmid": str(1000 + i),
            "title": f"Title {i}",
            "abstract": abstract,
            "year": 2020,
            "journal": "J Epigenet",
            "doi": f"10.1/{i}",
            "source_db": "pubmed",
        }
        for i in range(n)
    ]
    path = tmp_path / "corpus.json"
    path.write_text(
        json.dumps({"manifest": {"record_count": n}, "records": records}),
        encoding="utf-8",
    )
    return path


def _load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def test_every_record_appears_exactly_once_across_the_batches(tmp_path):
    """The batches must partition the corpus: no record lost, none duplicated."""
    corpus = _corpus(tmp_path, 125)
    paths = prepare_batches.prepare(
        corpus, tmp_path / "batches", batch_size=50, stage="screening"
    )

    assert [p.name for p in paths] == [
        "batch_0001.json", "batch_0002.json", "batch_0003.json"
    ]
    sizes = [len(_load(p)["records"]) for p in paths]
    assert sizes == [50, 50, 25]

    seen = [r["record_id"] for p in paths for r in _load(p)["records"]]
    expected = [f"egm-{i:06d}" for i in range(125)]
    assert seen == expected
    assert len(set(seen)) == 125


def test_an_exact_multiple_produces_no_trailing_empty_batch(tmp_path):
    corpus = _corpus(tmp_path, 100)
    paths = prepare_batches.prepare(
        corpus, tmp_path / "batches", batch_size=50, stage="screening"
    )
    assert len(paths) == 2
    assert [len(_load(p)["records"]) for p in paths] == [50, 50]


def test_batch_header_carries_stage_and_the_frozen_prompt_hash(tmp_path):
    corpus = _corpus(tmp_path, 3)
    _, prompt_sha = load_prompt("v1")
    paths = prepare_batches.prepare(
        corpus, tmp_path / "batches", batch_size=50, stage="calibration"
    )
    payload = _load(paths[0])
    assert payload["batch_id"] == "batch_0001"
    assert payload["stage"] == "calibration"
    assert payload["prompt_sha256"] == prompt_sha


def test_batch_records_carry_only_the_six_screening_fields(tmp_path):
    corpus = _corpus(tmp_path, 2)
    paths = prepare_batches.prepare(
        corpus, tmp_path / "batches", batch_size=50, stage="screening"
    )
    record = _load(paths[0])["records"][0]
    assert set(record) == {
        "record_id", "pmid", "title", "abstract", "year", "journal"
    }


def test_a_null_abstract_survives_as_null_not_as_a_placeholder(tmp_path):
    """The screener must be able to see that an abstract is genuinely absent
    and answer unclear; a placeholder string would read as content."""
    corpus = _corpus(tmp_path, 2, abstract=None)
    paths = prepare_batches.prepare(
        corpus, tmp_path / "batches", batch_size=50, stage="screening"
    )
    raw = pathlib.Path(paths[0]).read_text(encoding="utf-8")
    assert '"abstract": null' in raw
    assert _load(paths[0])["records"][0]["abstract"] is None


def test_a_null_pmid_survives_as_null(tmp_path):
    corpus = _corpus(tmp_path, 1)
    payload = _load(corpus)
    payload["records"][0]["pmid"] = None
    corpus.write_text(json.dumps(payload), encoding="utf-8")

    paths = prepare_batches.prepare(
        corpus, tmp_path / "batches", batch_size=50, stage="screening"
    )
    assert _load(paths[0])["records"][0]["pmid"] is None


def test_a_record_missing_the_abstract_key_raises(tmp_path):
    """Absent key and null value are different facts; only one is legitimate."""
    corpus = _corpus(tmp_path, 1)
    payload = _load(corpus)
    del payload["records"][0]["abstract"]
    corpus.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(prepare_batches.PrepareError, match="abstract"):
        prepare_batches.prepare(
            corpus, tmp_path / "batches", batch_size=50, stage="screening"
        )


def test_record_ids_selects_only_those_records_in_corpus_order(tmp_path):
    corpus = _corpus(tmp_path, 100)
    wanted = ["egm-000042", "egm-000007", "egm-000003"]
    paths = prepare_batches.prepare(
        corpus, tmp_path / "batches", batch_size=50, stage="calibration",
        record_ids=wanted,
    )
    got = [r["record_id"] for r in _load(paths[0])["records"]]
    assert got == ["egm-000003", "egm-000007", "egm-000042"]


def test_a_requested_record_id_absent_from_the_corpus_raises(tmp_path):
    """A silently missing calibration record would shrink the kappa denominator."""
    corpus = _corpus(tmp_path, 10)
    with pytest.raises(prepare_batches.PrepareError, match="egm-999999"):
        prepare_batches.prepare(
            corpus, tmp_path / "batches", batch_size=50, stage="calibration",
            record_ids=["egm-000001", "egm-999999"],
        )


def test_refuses_to_overwrite_an_existing_batch_file(tmp_path):
    corpus = _corpus(tmp_path, 10)
    out = tmp_path / "batches"
    prepare_batches.prepare(corpus, out, batch_size=50, stage="screening")

    with pytest.raises(FileExistsError):
        prepare_batches.prepare(corpus, out, batch_size=50, stage="screening")


def test_nothing_is_written_when_a_later_batch_already_exists(tmp_path):
    """The overwrite check runs before any write, so a clash leaves no
    half-written batch set behind."""
    corpus = _corpus(tmp_path, 100)
    out = tmp_path / "batches"
    out.mkdir()
    (out / "batch_0002.json").write_text("sentinel", encoding="utf-8")

    with pytest.raises(FileExistsError):
        prepare_batches.prepare(corpus, out, batch_size=50, stage="screening")

    assert not (out / "batch_0001.json").exists()
    assert (out / "batch_0002.json").read_text(encoding="utf-8") == "sentinel"


def test_preparation_is_deterministic_byte_for_byte(tmp_path):
    """No RNG, no shuffling: the same corpus yields the same batch files."""
    corpus = _corpus(tmp_path, 75)
    first = prepare_batches.prepare(
        corpus, tmp_path / "a", batch_size=25, stage="screening"
    )
    second = prepare_batches.prepare(
        corpus, tmp_path / "b", batch_size=25, stage="screening"
    )
    assert len(first) == len(second) == 3
    for one, two in zip(first, second):
        assert one.read_bytes() == two.read_bytes()


def test_a_non_positive_batch_size_raises(tmp_path):
    corpus = _corpus(tmp_path, 10)
    with pytest.raises(prepare_batches.PrepareError, match="batch_size"):
        prepare_batches.prepare(
            corpus, tmp_path / "batches", batch_size=0, stage="screening"
        )


def test_an_empty_selection_raises_rather_than_writing_nothing(tmp_path):
    """Zero batches written and a clean exit is indistinguishable from success."""
    corpus = _corpus(tmp_path, 10)
    with pytest.raises(prepare_batches.PrepareError, match="no records"):
        prepare_batches.prepare(
            corpus, tmp_path / "batches", batch_size=50, stage="screening",
            record_ids=[],
        )


def test_cli_writes_batches(tmp_path, monkeypatch):
    corpus = _corpus(tmp_path, 60)
    out = tmp_path / "batches"
    monkeypatch.setattr("sys.argv", [
        "prepare_batches", "--corpus", str(corpus), "--out-dir", str(out),
        "--batch-size", "50", "--stage", "screening", "--prompt-version", "v1",
    ])
    prepare_batches.main()
    assert (out / "batch_0001.json").exists()
    assert (out / "batch_0002.json").exists()


def test_cli_record_ids_file_is_honoured(tmp_path, monkeypatch):
    corpus = _corpus(tmp_path, 60)
    ids = tmp_path / "ids.json"
    ids.write_text(json.dumps(["egm-000005", "egm-000006"]), encoding="utf-8")
    out = tmp_path / "batches"
    monkeypatch.setattr("sys.argv", [
        "prepare_batches", "--corpus", str(corpus), "--out-dir", str(out),
        "--stage", "calibration", "--prompt-version", "v1", "--record-ids", str(ids),
    ])
    prepare_batches.main()
    records = _load(out / "batch_0001.json")["records"]
    assert [r["record_id"] for r in records] == ["egm-000005", "egm-000006"]


def test_cli_requires_an_explicit_prompt_version(monkeypatch, tmp_path, capsys):
    """A defaulted prompt version would mislabel a run with a stale instrument.

    The prompt SHA-256 is stamped into every decision in the batch and is the
    only thing that makes instrument drift detectable in the log. If the CLI
    defaulted to v1, a screening run launched after the v2 refinement would
    carry v1's hash on 9,786 decisions and nothing would flag it.
    """
    corpus = _corpus(tmp_path, 3)
    monkeypatch.setattr("sys.argv", [
        "prepare_batches", "--corpus", str(corpus),
        "--out-dir", str(tmp_path / "b"), "--stage", "screening",
    ])
    with pytest.raises(SystemExit):
        prepare_batches.main()
    assert "--prompt-version" in capsys.readouterr().err


def test_batch_carries_the_hash_of_the_requested_version(tmp_path):
    """v1 and v2 must produce different stamps, or the guard is decorative."""
    corpus = _corpus(tmp_path, 3)
    v1, = prepare_batches.prepare(corpus, tmp_path / "b1", 50, "screening", None, "v1")
    v2, = prepare_batches.prepare(corpus, tmp_path / "b2", 50, "screening", None, "v2")

    h1 = json.loads(v1.read_text(encoding="utf-8"))["prompt_sha256"]
    h2 = json.loads(v2.read_text(encoding="utf-8"))["prompt_sha256"]

    assert h1 != h2
    assert h2 == "0b2565e2d7be6fe29dcb81e6d34b831546476f85c5256cdabfc313e353d335da"
