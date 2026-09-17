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
    number of records REMOVED; only 184 of the 190 groups were cross-source.

    The fixture deliberately uses a group of THREE records. With only two-record
    groups, `sum(len - 1)` and `len(groups)` coincide, and the exact off-by-one
    this test exists to catch is invisible — an audit found the first version of
    this test passing against that bug. Here 4 records are removed across 3
    groups, so the two quantities cannot be confused.
    """
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps({"manifest": {}, "records": [
        # three records merged into one: contributes 2 removals, 1 group
        {"record_id": "a", "merged_from": ["pubmed:1", "europepmc:PPR:1", "europepmc:PPR:2"]},
        {"record_id": "b", "merged_from": ["pubmed:2", "europepmc:PMC:9"]},
        {"record_id": "c", "merged_from": ["europepmc:PMC:1", "europepmc:PMC:2"]},
        {"record_id": "d", "merged_from": ["pubmed:3"]},
    ]}), encoding="utf-8")

    note = render_prisma._merge_note(corpus)

    assert "4 records were removed across 3 merge groups" in note, note
    assert "2 joined records from different databases" in note, note
    assert "1 were within a single database" in note, note


def test_merge_note_degrades_without_the_corpus(tmp_path):
    note = render_prisma._merge_note(None)
    assert "merged_from" in note
    assert "records were removed" not in note


def test_gate_closed_block_does_not_claim_unverified_coverage(tmp_path):
    """An audit found the withheld block asserting "Every one has a recorded
    decision" for a record count taken from a stale CSV, against a decision log
    that covered a different number. The claim is now checked."""
    ident = tmp_path / "counts.csv"
    ident.write_text(CSV, encoding="utf-8")
    decisions = tmp_path / "decisions.jsonl"
    decisions.write_text("", encoding="utf-8")   # no decisions at all
    out = tmp_path / "flow.md"

    render_prisma.render(ident, decisions, tmp_path / "absent.json", out)
    text = out.read_text(encoding="utf-8")

    assert "Every one has a recorded decision" not in text
    assert "decision log covers 0 of them" in text
    assert "do not match" in text


# --- registers are their own identification stream ---------------------------


def _registry(tmp_path, n_interventional=3, n_observational=2):
    path = tmp_path / "registry.json"
    records = (
        [{"source_id": f"NCT{i:08d}", "study_type": "INTERVENTIONAL"}
         for i in range(n_interventional)]
        + [{"source_id": f"NCT9{i:07d}", "study_type": "OBSERVATIONAL"}
           for i in range(n_observational)]
    )
    path.write_text(json.dumps({"manifest": {}, "records": records}), encoding="utf-8")
    return path


def test_registry_counts_are_derived_from_the_artefact(tmp_path):
    ident, decisions, agreement = _inputs(tmp_path)
    out = tmp_path / "flow.md"

    render_prisma.render(ident, decisions, agreement, out, None,
                         _registry(tmp_path, 3, 2))
    text = out.read_text(encoding="utf-8")

    assert "| ClinicalTrials.gov | 5 |" in text
    assert "| interventional | 3 |" in text
    assert "| observational | 2 |" in text


def test_registrations_are_never_added_to_the_corpus_count(tmp_path):
    """The inversion this stream exists to expose.

    A trial registered and never published is the ABSENCE of evidence. If the
    694 registrations were folded into the 9,786 screened records, that absence
    would be counted as evidence.
    """
    ident, decisions, agreement = _inputs(tmp_path)
    out = tmp_path / "flow.md"

    render_prisma.render(ident, decisions, agreement, out, None,
                         _registry(tmp_path, 3, 2))
    text = out.read_text(encoding="utf-8")

    # 9,786 is the corpus; 9,791 would be the corpus with registrations merged.
    assert "9,786" in text
    assert "9,791" not in text
    assert "not** part of the screening corpus" in text


def test_an_unsearched_register_says_so_rather_than_showing_nothing(tmp_path):
    """Silence would read as 'no registrations found', which is a different claim."""
    ident, decisions, agreement = _inputs(tmp_path)
    out = tmp_path / "flow.md"

    render_prisma.render(ident, decisions, agreement, out)
    text = out.read_text(encoding="utf-8")

    assert "Identification from registers" in text
    assert "Not searched" in text


def test_ictrp_is_named_as_unsearched_even_when_ctgov_ran(tmp_path):
    """A half-executed registry commitment must not read as a complete one."""
    ident, decisions, agreement = _inputs(tmp_path)
    out = tmp_path / "flow.md"

    render_prisma.render(ident, decisions, agreement, out, None,
                         _registry(tmp_path))
    text = out.read_text(encoding="utf-8")

    assert "| WHO ICTRP | not searched |" in text


def test_the_overlay_finding_stays_out_of_the_prisma_figure(tmp_path):
    """Identification counts are ungated; findings are not.

    'Registered but unreported' is a claim about the evidence base and needs
    the bibliographic corpus to confirm. It waits for the Stage 0 gate.
    """
    ident, decisions, agreement = _inputs(tmp_path)
    out = tmp_path / "flow.md"

    render_prisma.render(ident, decisions, agreement, out, None,
                         _registry(tmp_path))
    text = out.read_text(encoding="utf-8").lower()

    for forbidden in ("unreported", "overlay candidate"):
        assert forbidden not in text, f"{forbidden!r} is a finding, not identification"
