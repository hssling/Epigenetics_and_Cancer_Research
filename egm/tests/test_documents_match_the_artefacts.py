"""Numbers written into prose must still match the artefacts they describe.

`render_prisma` derives the PRISMA figure, so it cannot drift. STATUS.md and
the RUNBOOK are narrative documents with numbers typed into them, and a typed
number is a claim that stops being checked the moment it is written. An audit
found exactly this class of defect: a document asserting a record count read
from a superseded CSV, against a decision log covering a different number.

These tests read the committed artefacts and compare. They are deliberately
about the few numbers a reader would act on -- the corpus size and the
screening outcome -- not every figure in the prose.
"""
import json
import pathlib
import re

import pytest

from pipeline.screen_schema import read_decisions

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORPUS = ROOT / "search/raw/combined_corpus_v3.json"
DECISIONS = ROOT / "screening/screening_decisions_sonnet.jsonl"
STATUS = ROOT / "manuscript/STATUS.md"
RUNBOOK = ROOT / "screening/RUNBOOK.md"


def _require(path: pathlib.Path) -> pathlib.Path:
    """A missing artefact is a failure, not a reason to skip.

    Skipping here would make the suite pass most loudly in the one situation
    these tests exist to catch: the artefact being gone or renamed while the
    prose still cites numbers from it.
    """
    if not path.exists():
        pytest.fail(f"{path.relative_to(ROOT)} is missing; the documents cite it")
    return path


@pytest.fixture(scope="module")
def counts():
    decisions = [
        d for d in read_decisions(_require(DECISIONS)) if d.stage == "screening"
    ]
    tally = {"include": 0, "exclude": 0, "unclear": 0}
    for decision in decisions:
        tally[decision.decision] += 1
    return tally


@pytest.fixture(scope="module")
def corpus_size():
    payload = json.loads(_require(CORPUS).read_text(encoding="utf-8"))
    return len(payload["records"])


def test_status_screening_table_matches_the_decision_log(counts):
    """The table in STATUS.md section 2 is typed; the log is the truth."""
    text = _require(STATUS).read_text(encoding="utf-8")
    for label, n in counts.items():
        row = re.search(rf"^\| {label} \| ([\d,]+) \|", text, re.MULTILINE)
        assert row, f"STATUS.md has no screening row for {label!r}"
        written = int(row.group(1).replace(",", ""))
        assert written == n, (
            f"STATUS.md says {label}={written:,}; the decision log says "
            f"{n:,}. One of them has drifted."
        )


def test_every_corpus_record_has_exactly_one_screening_decision(counts, corpus_size):
    """The claim 'every record has a decision', actually checked."""
    decided = {
        d.record_id for d in read_decisions(DECISIONS) if d.stage == "screening"
    }
    assert len(decided) == corpus_size
    assert sum(counts.values()) == corpus_size


def test_documents_cite_the_corpus_size_they_actually_have(corpus_size):
    written = f"{corpus_size:,}"
    for path in (STATUS, RUNBOOK):
        text = _require(path).read_text(encoding="utf-8")
        assert written in text, (
            f"{path.relative_to(ROOT)} never mentions the corpus size "
            f"{written}; it may be citing a superseded corpus"
        )
        # The superseded corpora are close enough in size to pass unnoticed.
        for stale in ("9,978", "9,968", "9,967", "9,088 records"):
            assert stale not in text or "superseded" in text.lower(), (
                f"{path.relative_to(ROOT)} cites {stale}, a superseded count, "
                "without marking it as superseded"
            )


def test_the_instrument_hash_in_the_runbook_is_the_one_the_decisions_carry():
    """A stale hash in the runbook would send a re-run to the wrong prompt."""
    decisions = read_decisions(_require(DECISIONS))
    hashes = {d.prompt_sha256 for d in decisions if d.stage == "screening"}
    assert len(hashes) == 1, f"screening log spans {len(hashes)} instruments"
    full = hashes.pop()

    text = _require(RUNBOOK).read_text(encoding="utf-8")
    assert full[:8] in text, (
        f"the runbook does not cite the instrument hash {full[:8]}… that every "
        "screening decision was made under"
    )
