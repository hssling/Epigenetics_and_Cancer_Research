import pytest

from pipeline import pubmed
from pipeline.schema import SearchRecord


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def test_count_parses_esearch(mocker):
    mocker.patch.object(
        pubmed.requests, "get",
        return_value=_FakeResponse({"esearchresult": {"count": "9089"}}),
    )
    assert pubmed.count("anything") == 9089


def test_search_returns_idlist(mocker):
    mocker.patch.object(
        pubmed.requests, "get",
        return_value=_FakeResponse({"esearchresult": {"idlist": ["1", "2", "3"]}}),
    )
    assert pubmed.search("q", retmax=10) == ["1", "2", "3"]


def test_fetch_summaries_builds_records_with_explicit_none(mocker):
    """Absent fields must become explicit None, never a substituted value."""
    payload = {"result": {
        "uids": ["111"],
        "111": {
            "uid": "111",
            "title": "A methylation study",
            "fulljournalname": "J Epi",
            "pubdate": "2020 Mar",
            "authors": [{"name": "Smith J"}],
            "articleids": [{"idtype": "doi", "value": "10.1000/x"}],
        },
    }}
    mocker.patch.object(pubmed.requests, "get", return_value=_FakeResponse(payload))
    mocker.patch.object(pubmed.time, "sleep")

    records = pubmed.fetch_summaries(["111"], query_hash_value="abc123abc123")
    assert len(records) == 1
    r = records[0]
    assert isinstance(r, SearchRecord)
    assert r.pmid == "111"
    assert r.doi == "10.1000/x"
    assert r.year == 2020
    assert r.abstract is None           # esummary carries no abstract
    assert r.query_hash == "abc123abc123"


def test_missing_doi_becomes_none_not_empty_string(mocker):
    payload = {"result": {
        "uids": ["222"],
        "222": {"uid": "222", "title": "T", "fulljournalname": "J",
                "pubdate": "2019", "authors": [], "articleids": []},
    }}
    mocker.patch.object(pubmed.requests, "get", return_value=_FakeResponse(payload))
    mocker.patch.object(pubmed.time, "sleep")
    assert pubmed.fetch_summaries(["222"], query_hash_value="h" * 12)[0].doi is None


def test_unparseable_year_becomes_none(mocker):
    payload = {"result": {
        "uids": ["333"],
        "333": {"uid": "333", "title": "T", "fulljournalname": "J",
                "pubdate": "n.d.", "authors": [], "articleids": []},
    }}
    mocker.patch.object(pubmed.requests, "get", return_value=_FakeResponse(payload))
    mocker.patch.object(pubmed.time, "sleep")
    assert pubmed.fetch_summaries(["333"], query_hash_value="h" * 12)[0].year is None


def test_retries_then_raises(mocker):
    get = mocker.patch.object(
        pubmed.requests, "get", side_effect=pubmed.requests.RequestException("boom")
    )
    mocker.patch.object(pubmed.time, "sleep")
    with pytest.raises(pubmed.PubMedError):
        pubmed.count("q")
    assert get.call_count == 3


def test_pubmed_error_preserves_original_exception(mocker):
    mocker.patch.object(
        pubmed.requests, "get", side_effect=pubmed.requests.RequestException("boom")
    )
    mocker.patch.object(pubmed.time, "sleep")
    with pytest.raises(pubmed.PubMedError) as exc:
        pubmed.count("q")
    assert exc.value.__cause__ is not None
    assert isinstance(exc.value.__cause__, pubmed.requests.RequestException)


def test_ncbi_error_in_result_raises_pubmed_error(mocker):
    mocker.patch.object(
        pubmed.requests, "get",
        return_value=_FakeResponse({"esearchresult": {"ERROR": "Invalid db name"}}),
    )
    with pytest.raises(pubmed.PubMedError) as exc:
        pubmed.count("q")
    assert "Invalid db name" in str(exc.value)
    assert "PubMedError" not in str(exc.value.__cause__)


def test_missing_count_raises_pubmed_error(mocker):
    mocker.patch.object(
        pubmed.requests, "get",
        return_value=_FakeResponse({"esearchresult": {}}),
    )
    with pytest.raises(pubmed.PubMedError) as exc:
        pubmed.count("q")
    assert "count" in str(exc.value)


def test_missing_idlist_raises_pubmed_error(mocker):
    mocker.patch.object(
        pubmed.requests, "get",
        return_value=_FakeResponse({"esearchresult": {}}),
    )
    with pytest.raises(pubmed.PubMedError) as exc:
        pubmed.search("q", retmax=10)
    assert "idlist" in str(exc.value)


def test_missing_result_key_raises_instead_of_vanishing(mocker):
    """A malformed/error esummary body with no 'result' key must not silently
    yield zero records for the whole batch (demonstrated: 3 requested, 0 returned,
    no error, before this fix).

    Asserts on wording distinctive to the 'result' key check itself (batch size
    and 'result'), not just "an error was raised" -- the per-pmid omission
    check (a separate fix) would also fire in this scenario since every pmid
    in the batch is technically "missing" once result defaults to {}, so a
    looser assertion would pass even with this specific check removed.
    """
    mocker.patch.object(
        pubmed.requests, "get",
        return_value=_FakeResponse({"header": {"type": "esummary"}}),
    )
    mocker.patch.object(pubmed.time, "sleep")
    with pytest.raises(pubmed.PubMedError) as exc:
        pubmed.fetch_summaries(["1", "2", "3"], query_hash_value="h" * 12)
    message = str(exc.value)
    assert "'result'" in message
    assert "batch of 3" in message
    assert "first='1'" in message and "last='3'" in message


def test_omitted_pmid_raises_instead_of_silently_dropping(mocker):
    """A uid NCBI omits from the result body must not silently disappear
    (demonstrated: 2 requested, 1 returned, no error, before this fix)."""
    payload = {"result": {
        "uids": ["111"],
        "111": {"uid": "111", "title": "A methylation study", "fulljournalname": "J",
                "pubdate": "2020", "authors": [], "articleids": []},
    }}
    mocker.patch.object(pubmed.requests, "get", return_value=_FakeResponse(payload))
    mocker.patch.object(pubmed.time, "sleep")
    with pytest.raises(pubmed.PubMedError) as exc:
        pubmed.fetch_summaries(["111", "222"], query_hash_value="h" * 12)
    assert "222" in str(exc.value)


def test_empty_title_raises_instead_of_defaulting(mocker):
    """title is a required, non-Optional field; it must never default to ''.

    An empty default lets two distinct untitled records collide under fuzzy
    matching, since rapidfuzz.fuzz.ratio('', '') == 100.0.
    """
    payload = {"result": {
        "uids": ["444"],
        "444": {"uid": "444", "title": "   ", "fulljournalname": "J",
                "pubdate": "2020", "authors": [], "articleids": []},
    }}
    mocker.patch.object(pubmed.requests, "get", return_value=_FakeResponse(payload))
    mocker.patch.object(pubmed.time, "sleep")
    with pytest.raises(pubmed.PubMedError) as exc:
        pubmed.fetch_summaries(["444"], query_hash_value="h" * 12)
    assert "444" in str(exc.value)
