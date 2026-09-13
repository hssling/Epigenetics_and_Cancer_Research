"""The protocol must pre-specify the decisions that cannot be made later."""
import pathlib

from pipeline.query import build_pubmed_query

PROTOCOL = pathlib.Path(__file__).resolve().parents[1] / "protocol" / "protocol.md"


def test_protocol_exists():
    assert PROTOCOL.exists()


def test_protocol_embeds_the_exact_executed_query():
    """The registered query must be byte-identical to the one the code builds."""
    text = PROTOCOL.read_text(encoding="utf-8")
    assert build_pubmed_query(include_ncrna=False, date_limited=True) in text


def test_protocol_prespecifies_the_poolability_rule():
    text = PROTOCOL.read_text(encoding="utf-8")
    for required in ["10 studies", "comparable comparator", "pre-registered null"]:
        assert required in text, f"poolability rule must state {required!r}"


def test_protocol_prespecifies_screening_validation():
    text = PROTOCOL.read_text(encoding="utf-8")
    for required in ["0.75", "1,000", "false negative"]:
        assert required in text


def test_protocol_declares_ai_use_and_non_authorship():
    text = PROTOCOL.read_text(encoding="utf-8").lower()
    assert "not an author" in text or "not authors" in text
