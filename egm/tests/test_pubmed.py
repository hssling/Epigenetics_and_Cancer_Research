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
