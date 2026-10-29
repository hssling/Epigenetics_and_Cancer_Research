import ast
import inspect

from pipeline import highlight, screen_app


def test_highlighter_cannot_reach_ai_decisions_or_a_model():
    """Blindness: the highlighter is fixed regexes over the record text only."""
    tree = ast.parse(inspect.getsource(highlight))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert imported <= {"html", "re", "typing"}, imported
    source = inspect.getsource(highlight)
    for forbidden in ("screening_decisions", "jsonl", "anthropic", "open("):
        assert forbidden not in source


def test_finds_terms_per_category_without_duplicates():
    found = highlight.find(
        "A prospective cohort measured DNA methylation in whole blood. "
        "Methylation predicted survival. miR-21 was also assayed."
    )
    assert found["design"] == ["prospective", "cohort"]
    assert found["marker"] == ["methylation"]
    assert found["material"] == ["whole blood"]
    assert found["approach"] == ["predicted", "survival"]
    assert found["ncrna"] == ["miR-21"]


def test_rule_specific_cautions_win_over_general_marker_terms():
    found = highlight.find("Citrullinated histone H3 and DNA fragmentation index were measured.")
    assert "Citrullinated histone H3" in found["caution"]
    assert "DNA fragmentation index" in found["caution"]
    assert found["marker"] == []


def test_matches_whole_words_only():
    found = highlight.find("Geographic variation in ratings of controlled substances")
    assert found["design"] == []
    assert found["nonhuman"] == []


def test_mark_escapes_html_in_the_record():
    out = highlight.mark("<script>x</script> methylation & cohort")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out
    assert '<mark class="marker"' in out and "&amp;" in out


def test_structured_abstract_sections_are_put_on_their_own_lines():
    out = highlight.mark("BACKGROUND: Something. METHODS: We did it. RESULTS: It worked.")
    assert "\n<b>METHODS:</b>" in out
    assert "\n<b>RESULTS:</b>" in out


def test_year_outside_the_window_is_flagged():
    assert highlight.year_flag("2014") == "2014 is outside 2015-2026 (excl. 6)"
    assert highlight.year_flag("2015") is None
    assert highlight.year_flag(None) == "year not stated"


def test_page_shows_signals_and_never_a_verdict():
    record = {
        "record_id": "egm-1", "pmid": "1", "year": "2020", "journal": "J",
        "title": "EWAS of smoking",
        "abstract": "A case-control study of blood DNA methylation and smoking.",
    }
    page = screen_app.build_page(record, 1, 300, 0.0)
    assert '<mark class="marker"' in page
    assert "not judgements" in page
    lowered = page.lower()
    for verdict in ("suggest", "likely include", "likely exclude", "recommend"):
        assert verdict not in lowered


def test_page_without_abstract_shows_no_signal_strip():
    record = {"record_id": "egm-1", "pmid": "1", "year": "2020", "title": "T", "abstract": None}
    page = screen_app.build_page(record, 1, 300, 0.0)
    assert 'class="sig"' not in page
    assert "no abstract" in page.lower()
