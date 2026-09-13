"""Europe PMC client tests. All HTTP is mocked; the suite never touches the network."""
import pytest

from pipeline import europepmc
from pipeline.schema import SearchRecord

QH = "h" * 12

# A hard ceiling on mocked requests. Without it, a pagination bug that never
# terminates would hang the suite instead of failing it.
REQUEST_CAP = 10


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def _result(**overrides):
    """A minimal well-formed Europe PMC result, overridable per test."""
    base = {"id": "PPR1", "source": "PPR", "title": "A methylation study"}
    base.update(overrides)
    return base


def _page(results, hit_count, next_cursor):
    return {
        "hitCount": hit_count,
        "nextCursorMark": next_cursor,
        "resultList": {"result": results},
    }


def _final_page(results, hit_count):
    """A page that ends the result set by omitting nextCursorMark.

    Observed live on 2026-09-14: at pageSize=1000 the whole 890-record set came
    back on one page and the response body carried no nextCursorMark key at all.
    That is what these single-page fixtures reproduce. The other exhaustion
    signal -- a paged set whose final page echoes the cursorMark it was sent --
    is covered by test_pagination_stops_when_cursor_repeats.
    """
    return {"hitCount": hit_count, "resultList": {"result": results}}


def _patch_pages(mocker, pages, cap=REQUEST_CAP):
    """Serve `pages` in order; repeat the last one thereafter (as Europe PMC does).

    Returns the list of cursorMark values the client actually sent.
    """
    sent: list[str] = []

    def fake_get(url, params=None, timeout=None):
        if len(sent) >= cap:
            raise AssertionError(
                f"client issued more than {cap} requests; pagination did not terminate"
            )
        sent.append(params["cursorMark"])
        index = min(len(sent) - 1, len(pages) - 1)
        return _FakeResponse(pages[index])

    mocker.patch.object(europepmc.requests, "get", side_effect=fake_get)
    mocker.patch.object(europepmc.time, "sleep")
    return sent


# --------------------------------------------------------------------------
# Query construction
# --------------------------------------------------------------------------

def test_query_restricts_terms_to_title_and_abstract():
    """Europe PMC free-text searches FULL TEXT. Unwrapped, this strategy returns
    239,868 rather than 5,982. Each term must be (TITLE:x OR ABSTRACT:x)."""
    query = europepmc.build_europepmc_query(exclude_medline=True)

    assert "(TITLE:EWAS OR ABSTRACT:EWAS)" in query
    assert '(TITLE:"DNA methylation" OR ABSTRACT:"DNA methylation")' in query
    assert '(TITLE:"epigenetic clock" OR ABSTRACT:"epigenetic clock")' in query
    assert "NOT SRC:MED" in query
    assert "(PUB_YEAR:[2015 TO 2026])" in query

    # Every occurrence of a sampled term must be field-qualified. Strip the
    # qualified forms and the bare term must not survive anywhere.
    stripped = query.replace("TITLE:EWAS", "").replace("ABSTRACT:EWAS", "")
    assert "EWAS" not in stripped


def test_query_without_exclude_medline_has_no_src_filter():
    query = europepmc.build_europepmc_query(exclude_medline=False)
    assert "NOT SRC:MED" not in query
    assert "SRC:MED" not in query


def test_build_query_flag_is_required():
    """Mirrors build_pubmed_query: the flag is explicit, never defaulted."""
    with pytest.raises(TypeError):
        europepmc.build_europepmc_query()


# --------------------------------------------------------------------------
# count
# --------------------------------------------------------------------------

def test_count_parses_hitcount(mocker):
    mocker.patch.object(
        europepmc.requests, "get", return_value=_FakeResponse({"hitCount": 890})
    )
    assert europepmc.count("q") == 890


def test_count_missing_hitcount_raises(mocker):
    mocker.patch.object(europepmc.requests, "get", return_value=_FakeResponse({}))
    mocker.patch.object(europepmc.time, "sleep")
    with pytest.raises(europepmc.EuropePMCError) as exc:
        europepmc.count("q")
    assert "hitCount" in str(exc.value)


# --------------------------------------------------------------------------
# Pagination
# --------------------------------------------------------------------------

def test_pagination_stops_when_cursor_repeats(mocker):
    """Europe PMC returns the SAME cursorMark on the final page. A naive
    `while next_cursor:` loop therefore never terminates."""
    pages = [
        _page([_result(id="A1"), _result(id="A2")], 5, "CURSOR_B"),
        _page([_result(id="B1"), _result(id="B2")], 5, "CURSOR_C"),
        _page([_result(id="C1")], 5, "CURSOR_C"),  # unchanged -> final page
    ]
    sent = _patch_pages(mocker, pages)

    records = europepmc.search_records("q", query_hash_value=QH, page_size=2)

    assert len(sent) == 3, f"expected exactly 3 requests, got {len(sent)}: {sent}"
    assert sent == ["*", "CURSOR_B", "CURSOR_C"]
    assert [r.source_id for r in records] == [
        "PPR:A1", "PPR:A2", "PPR:B1", "PPR:B2", "PPR:C1",
    ]


def test_record_count_exceeding_hitcount_raises(mocker):
    """More records than hitCount means the cursor is looping or the index
    shifted mid-run; either way the corpus is not the one that was counted."""
    pages = [
        _page([_result(id="A1"), _result(id="A2")], 3, "CURSOR_B"),
        _page([_result(id="B1"), _result(id="B2")], 3, "CURSOR_C"),
    ]
    _patch_pages(mocker, pages)
    with pytest.raises(europepmc.EuropePMCError) as exc:
        europepmc.search_records("q", query_hash_value=QH, page_size=2)
    assert "hitCount" in str(exc.value)


def test_empty_page_with_records_outstanding_raises(mocker):
    pages = [
        _page([_result(id="A1")], 10, "CURSOR_B"),
        _page([], 10, "CURSOR_C"),
    ]
    _patch_pages(mocker, pages)
    with pytest.raises(europepmc.EuropePMCError) as exc:
        europepmc.search_records("q", query_hash_value=QH, page_size=1)
    assert "0 results" in str(exc.value)


# --------------------------------------------------------------------------
# Field mapping
# --------------------------------------------------------------------------

def test_missing_title_raises(mocker):
    """title is required and must never be defaulted to an empty string:
    rapidfuzz.fuzz.ratio('', '') == 100, so blank titles collide in dedup."""
    pages = [_final_page([{"id": "PPR9", "source": "PPR"}], 1)]
    _patch_pages(mocker, pages)
    with pytest.raises(europepmc.EuropePMCError) as exc:
        europepmc.search_records("q", query_hash_value=QH, page_size=1)
    assert "PPR9" in str(exc.value)
    assert "title" in str(exc.value)


def test_blank_title_raises(mocker):
    pages = [_final_page([_result(id="PPR8", title="   ")], 1)]
    _patch_pages(mocker, pages)
    with pytest.raises(europepmc.EuropePMCError):
        europepmc.search_records("q", query_hash_value=QH, page_size=1)


def test_absent_fields_become_none(mocker):
    pages = [_final_page([_result()], 1)]
    _patch_pages(mocker, pages)
    records = europepmc.search_records("q", query_hash_value=QH, page_size=1)
    assert len(records) == 1
    record = records[0]
    assert isinstance(record, SearchRecord)
    assert record.source_db == "europepmc"
    assert record.title == "A methylation study"
    assert record.doi is None
    assert record.pmid is None
    assert record.abstract is None
    assert record.year is None
    assert record.journal is None
    assert record.authors == []
    assert record.query_hash == QH


def test_populated_fields_are_mapped(mocker):
    pages = [_final_page([_result(
        id="12345", source="MED", doi="10.1000/x", pmid="12345",
        abstractText="An abstract.", pubYear="2020",
        journalInfo={"journal": {"title": "J Epi"}},
        authorString="Smith J, Jones A.",
    )], 1)]
    _patch_pages(mocker, pages)
    record = europepmc.search_records("q", query_hash_value=QH, page_size=1)[0]
    assert record.source_id == "MED:12345"
    assert record.doi == "10.1000/x"
    assert record.pmid == "12345"
    assert record.abstract == "An abstract."
    assert record.year == 2020
    assert record.journal == "J Epi"
    assert record.authors == ["Smith J", "Jones A"]


def test_source_id_is_qualified_by_source(mocker):
    """Europe PMC ids are unique only within a source; PPR:123 and PMC:123
    are different records and must not collapse."""
    pages = [_final_page(
        [_result(id="123", source="PPR"), _result(id="123", source="PMC")],
        2,
    )]
    _patch_pages(mocker, pages)
    records = europepmc.search_records("q", query_hash_value=QH, page_size=2)
    ids = [r.source_id for r in records]
    assert ids == ["PPR:123", "PMC:123"]
    assert len(set(ids)) == 2


def test_year_unparseable_becomes_none(mocker):
    pages = [_final_page([_result(pubYear="n.d.")], 1)]
    _patch_pages(mocker, pages)
    assert europepmc.search_records("q", query_hash_value=QH, page_size=1)[0].year is None


def test_authors_parsed_from_author_string(mocker):
    pages = [_final_page([_result(authorString="Smith J, Jones A, Brown K.")], 1)]
    _patch_pages(mocker, pages)
    record = europepmc.search_records("q", query_hash_value=QH, page_size=1)[0]
    assert record.authors == ["Smith J", "Jones A", "Brown K"]


def test_empty_doi_becomes_none_not_empty_string(mocker):
    pages = [_final_page([_result(doi="", pmid="", abstractText="")], 1)]
    _patch_pages(mocker, pages)
    record = europepmc.search_records("q", query_hash_value=QH, page_size=1)[0]
    assert record.doi is None
    assert record.pmid is None
    assert record.abstract is None


# --------------------------------------------------------------------------
# Transport failures
# --------------------------------------------------------------------------

def test_http_failure_raises_europepmc_error(mocker):
    """A failed page must never yield a silently partial corpus."""
    get = mocker.patch.object(
        europepmc.requests, "get",
        side_effect=europepmc.requests.RequestException("boom"),
    )
    mocker.patch.object(europepmc.time, "sleep")
    with pytest.raises(europepmc.EuropePMCError) as exc:
        europepmc.search_records("q", query_hash_value=QH, page_size=10)
    assert get.call_count == europepmc.MAX_ATTEMPTS
    assert isinstance(exc.value.__cause__, europepmc.requests.RequestException)


def test_missing_resultlist_raises(mocker):
    pages = [{"hitCount": 3, "nextCursorMark": "CURSOR_A"}]
    _patch_pages(mocker, pages)
    with pytest.raises(europepmc.EuropePMCError) as exc:
        europepmc.search_records("q", query_hash_value=QH, page_size=1)
    assert "resultList" in str(exc.value)


def test_absent_next_cursor_ends_a_complete_result_set(mocker):
    """Live at pageSize=1000 the whole set arrives on one page and the body
    carries no nextCursorMark. That is exhaustion, and one request suffices."""
    pages = [{"hitCount": 2, "resultList": {"result": [
        _result(id="A1"), _result(id="A2")]}}]
    sent = _patch_pages(mocker, pages)
    records = europepmc.search_records("q", query_hash_value=QH, page_size=1000)
    assert len(sent) == 1
    assert [r.source_id for r in records] == ["PPR:A1", "PPR:A2"]


def test_absent_next_cursor_with_records_outstanding_raises(mocker):
    """An omitted nextCursorMark must not be an escape hatch: if records are
    still outstanding there is no way to continue, so the corpus would be
    silently truncated."""
    pages = [{"hitCount": 890, "resultList": {"result": [_result(id="A1")]}}]
    _patch_pages(mocker, pages)
    with pytest.raises(europepmc.EuropePMCError) as exc:
        europepmc.search_records("q", query_hash_value=QH, page_size=1000)
    assert "1 of 890" in str(exc.value)
    assert "truncated" in str(exc.value)


def test_repeated_cursor_with_records_outstanding_raises(mocker):
    """The other exhaustion signal gets the same cross-check."""
    pages = [
        _page([_result(id="A1")], 890, "CURSOR_B"),
        _page([_result(id="B1")], 890, "CURSOR_B"),
    ]
    _patch_pages(mocker, pages)
    with pytest.raises(europepmc.EuropePMCError) as exc:
        europepmc.search_records("q", query_hash_value=QH, page_size=1)
    assert "2 of 890" in str(exc.value)
    assert "truncated" in str(exc.value)


def test_search_requests_core_result_type(mocker):
    """resultType=core is what carries abstractText; lite would silently
    produce a corpus of abstract-less records."""
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured.update(params)
        return _FakeResponse(_final_page([_result()], 1))

    mocker.patch.object(europepmc.requests, "get", side_effect=fake_get)
    mocker.patch.object(europepmc.time, "sleep")
    europepmc.search_records("q", query_hash_value=QH, page_size=25)
    assert captured["resultType"] == "core"
    assert captured["format"] == "json"
    assert captured["pageSize"] == 25
