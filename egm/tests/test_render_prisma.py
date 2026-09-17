"""The PRISMA figure must not be a way around the Stage 0 gate.

A PRISMA diagram is the figure a reader trusts on sight. If a screening count
could reach it without passing kappa, the gate in report_screening would be
decorative — the number would simply appear in the figure instead.
"""
import json

import pytest

from pipeline import render_prisma

CSV = """flow,stage,identified,excluded,included,reason
pubmed,identification_pubmed,9089,1,9088,"dupes"
combined,identification_combined,9978,192,9786,"union"
"""


def _inputs(tmp_path):
    ident = tmp_path / "counts.csv"
    ident.write_text(CSV, encoding="utf-8")
    return ident, tmp_path / "decisions.jsonl", tmp_path / "absent_agreement.json"


def test_gate_closed_withholds_every_screening_count(tmp_path):
    ident, decisions, agreement = _inputs(tmp_path)
    out = tmp_path / "flow.md"

    shown = render_prisma.render(ident, decisions, agreement, out)

    assert shown is False
    text = out.read_text(encoding="utf-8")
    assert "WITHHELD" in text
    # The identification and dedup numbers are legitimate and must appear.
    assert "9,786" in text and "9,089" in text
    # No screening outcome may appear anywhere in the document.
    for forbidden in ("5,745", "3,767", "58.7", "retained for full text"):
        assert forbidden not in text, f"screening count {forbidden!r} leaked into the figure"


def test_the_document_says_why_it_is_withholding(tmp_path):
    ident, decisions, agreement = _inputs(tmp_path)
    out = tmp_path / "flow.md"
    render_prisma.render(ident, decisions, agreement, out)
    text = out.read_text(encoding="utf-8")

    assert "kappa" in text.lower()
    assert "no agreement report" in text


def test_merge_note_is_derived_not_asserted(tmp_path):
    """An earlier hand-written draft said '192 cross-source merges'. 192 is the
    number of records removed; only 184 groups were cross-source."""
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps({"manifest": {}, "records": [
        {"record_id": "a", "merged_from": ["pubmed:1", "europepmc:PPR:1"]},
        {"record_id": "b", "merged_from": ["europepmc:PMC:1", "europepmc:PMC:2"]},
        {"record_id": "c", "merged_from": ["pubmed:2"]},
    ]}), encoding="utf-8")

    note = render_prisma._merge_note(corpus)

    assert "2 records were removed across 2 merge groups" in note
    assert "1 joined records from different databases" in note
    assert "1 were within a single database" in note


def test_merge_note_degrades_without_the_corpus(tmp_path):
    note = render_prisma._merge_note(None)
    assert "merged_from" in note
    assert "records were removed" not in note
