from pipeline import query
from pipeline.config import DATE_END, DATE_START


def test_core_excludes_ncrna_by_default():
    core = query.epigenetic_core()
    assert "methylome" in core
    assert "lncRNA" not in core


def test_build_query_is_balanced():
    q = query.build_pubmed_query(include_ncrna=False, date_limited=True)
    assert q.count("(") == q.count(")"), "unbalanced parentheses"


def test_date_limited_query_carries_the_window():
    q = query.build_pubmed_query(include_ncrna=False, date_limited=True)
    assert f"{DATE_START}:{DATE_END}[dp]" in q


def test_undated_query_omits_the_window():
    q = query.build_pubmed_query(include_ncrna=False, date_limited=False)
    assert "[dp]" not in q


def test_ncrna_flag_adds_ncrna_terms():
    without = query.build_pubmed_query(include_ncrna=False, date_limited=True)
    with_ = query.build_pubmed_query(include_ncrna=True, date_limited=True)
    assert "lncRNA" not in without
    assert "lncRNA" in with_
    assert len(with_) > len(without)


def test_secondary_publication_types_are_excluded():
    q = query.build_pubmed_query(include_ncrna=False, date_limited=True)
    assert "NOT (" in q
    for pt in ["review[pt]", "meta-analysis[pt]", "editorial[pt]"]:
        assert pt in q


def test_human_filter_present():
    assert "humans[MeSH]" in query.build_pubmed_query(include_ncrna=False, date_limited=True)
