"""Full-text retrieval. Every HTTP call is mocked; nothing here touches a network.

Stage 3 is gated on the human calibration (manuscript/STATUS.md), so these
tests exercise the tooling against fixtures only. No real PMID from the corpus
or the screening include set appears below.
"""
import hashlib
import json
import sys

import pytest
import requests
from pydantic import ValidationError

from pipeline import fulltext
from pipeline.fulltext import FullTextResult

JATS = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<article xmlns:xlink="http://www.w3.org/1999/xlink">'
    b"<front><article-meta><title-group><article-title>Fixture</article-title>"
    b"</title-group></article-meta></front><body><p>Text.</p></body></article>"
)

OA_RECORD = (
    '<OA><responseDate>2026-10-29 10:00:00</responseDate>'
    '<request id="{pmcid}">https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmcid}</request>'
    '<records returned-count="1" total-count="1">'
    '<record id="{pmcid}" citation="Fixture J. 2020" license="CC BY" retracted="no">'
    '<link format="tgz" updated="2020-01-01" href="ftp://example.invalid/x.tar.gz"/>'
    '</record></records></OA>'
)

OA_NOT_OPEN = (
    '<OA><responseDate>2026-10-29 10:00:00</responseDate>'
    '<request id="{pmcid}">https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmcid}</request>'
    '<error code="idIsNotOpenAccess">identifier \'{pmcid}\' is not Open Access</error>'
    '</OA>'
)


class _FakeResponse:
    def __init__(self, payload=None, text=None, content=None, status=200):
        self._payload = payload
        self.text = text if text is not None else (
            content.decode("utf-8") if content is not None else ""
        )
        self.content = content if content is not None else self.text.encode("utf-8")
        self.status_code = status

    def json(self):
        if self._payload is None:
            raise ValueError("not JSON")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


class _FakeNet:
    """Dispatches requests.get by URL to fixture idconv / OA / Europe PMC data.

    idconv: {pmid: record-dict}; a pmid absent from the dict is omitted from
    the response entirely. oa: {pmcid: "open" | "closed"}. xml: {pmcid: bytes}.
    """

    def __init__(self, idconv=None, oa=None, xml=None):
        self.idconv = idconv or {}
        self.oa = oa or {}
        self.xml = xml or {}
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, url, params=None, timeout=None):
        params = params or {}
        self.calls.append((url, params))
        assert timeout is not None, "every request must carry a timeout"
        if url == fulltext.IDCONV_URL:
            ids = params["ids"].split(",")
            records = [self.idconv[i] for i in ids if i in self.idconv]
            return _FakeResponse(payload={"status": "ok", "records": records})
        if url == fulltext.OA_URL:
            pmcid = params["id"]
            template = OA_RECORD if self.oa.get(pmcid) == "open" else OA_NOT_OPEN
            return _FakeResponse(text=template.format(pmcid=pmcid))
        if url.startswith("https://www.ebi.ac.uk/europepmc/webservices/rest/"):
            pmcid = url.rstrip("/").split("/")[-2]
            if pmcid not in self.xml:
                return _FakeResponse(text="", status=404)
            return _FakeResponse(content=self.xml[pmcid])
        raise AssertionError(f"unexpected URL {url}")

    def urls(self, prefix):
        return [(u, p) for u, p in self.calls if u.startswith(prefix)]


@pytest.fixture(autouse=True)
def _no_sleep_and_no_network(mocker):
    mocker.patch.object(fulltext.time, "sleep")
    # A test that forgets to install a fake fails here rather than going live.
    mocker.patch.object(
        fulltext.requests, "get",
        side_effect=AssertionError("unmocked network call in test_fulltext"),
    )


def _install(mocker, net):
    return mocker.patch.object(fulltext.requests, "get", side_effect=net)


def _rec(pmid, pmcid=None, doi=None, **extra):
    record = {"pmid": pmid, **extra}
    if pmcid:
        record["pmcid"] = pmcid
    if doi:
        record["doi"] = doi
    return record


# --- id conversion -----------------------------------------------------------

def test_resolve_ids_batches_at_200_and_sends_tool(mocker):
    pmids = [str(n) for n in range(1, 451)]
    net = _FakeNet(idconv={p: _rec(p) for p in pmids})
    _install(mocker, net)

    resolved = fulltext.resolve_ids(pmids)

    calls = net.urls(fulltext.IDCONV_URL)
    assert [len(p["ids"].split(",")) for _, p in calls] == [200, 200, 50]
    for _, params in calls:
        assert params["tool"] == fulltext.NCBI_TOOL_NAME
        assert params["format"] == "json"
        assert params["idtype"] == "pmid"
    assert set(resolved) == set(pmids)


def test_resolve_ids_refuses_a_batch_larger_than_200():
    with pytest.raises(ValueError, match="200"):
        fulltext.resolve_ids(["1"], batch_size=201)


def test_resolve_ids_sleeps_for_the_ncbi_rate_limit(mocker):
    net = _FakeNet(idconv={"1": _rec("1")})
    _install(mocker, net)
    fulltext.resolve_ids(["1"])
    fulltext.time.sleep.assert_called_with(fulltext.NCBI_RATE_LIMIT_SECONDS)


def test_resolve_ids_reads_pmcid_and_doi(mocker):
    net = _FakeNet(idconv={"10": _rec("10", pmcid="PMC100", doi="10.1/a")})
    _install(mocker, net)
    resolved = fulltext.resolve_ids(["10"])["10"]
    assert resolved.pmcid == "PMC100"
    assert resolved.doi == "10.1/a"


def test_resolve_ids_record_without_pmcid_is_none_not_blank(mocker):
    net = _FakeNet(idconv={
        "11": _rec("11", status="error", errmsg="Identifier not found in PMC"),
        "12": _rec("12", doi="10.1/b"),
    })
    _install(mocker, net)
    resolved = fulltext.resolve_ids(["11", "12"])
    assert resolved["11"].pmcid is None
    assert resolved["11"].doi is None
    assert resolved["11"].detail == "Identifier not found in PMC"
    assert resolved["12"].pmcid is None
    assert resolved["12"].doi == "10.1/b"


def test_resolve_ids_omits_a_pmid_the_response_omitted(mocker):
    """An omitted PMID is unknown, not 'has no PMCID'. It must not be guessed."""
    net = _FakeNet(idconv={"13": _rec("13", pmcid="PMC13")})
    _install(mocker, net)
    resolved = fulltext.resolve_ids(["13", "14"])
    assert "14" not in resolved


def test_resolve_ids_raises_after_retries(mocker):
    get = mocker.patch.object(
        fulltext.requests, "get", side_effect=requests.ConnectionError("down")
    )
    with pytest.raises(fulltext.FullTextError, match="attempts"):
        fulltext.resolve_ids(["1"])
    assert get.call_count == fulltext.MAX_ATTEMPTS


# --- open-access check -------------------------------------------------------

def test_check_open_access_reads_license(mocker):
    _install(mocker, _FakeNet(oa={"PMC1": "open"}))
    status = fulltext.check_open_access("PMC1")
    assert status.is_open_access is True
    assert status.license == "CC BY"


def test_check_open_access_recognises_the_not_open_access_error(mocker):
    _install(mocker, _FakeNet(oa={"PMC2": "closed"}))
    status = fulltext.check_open_access("PMC2")
    assert status.is_open_access is False
    assert status.license is None
    assert "not Open Access" in status.detail


def test_check_open_access_raises_on_an_unrecognised_error_code(mocker):
    """Only idIsNotOpenAccess means 'not open access'. Anything else is a
    failure to determine status, and must not be filed as a closed article."""
    body = '<OA><error code="idDoesNotExist">no such id</error></OA>'
    mocker.patch.object(fulltext.requests, "get", return_value=_FakeResponse(text=body))
    with pytest.raises(fulltext.FullTextError, match="idDoesNotExist"):
        fulltext.check_open_access("PMC3")


def test_check_open_access_raises_on_unparseable_body(mocker):
    mocker.patch.object(
        fulltext.requests, "get", return_value=_FakeResponse(text="<html>oops")
    )
    with pytest.raises(fulltext.FullTextError):
        fulltext.check_open_access("PMC4")


# --- XML fetch ---------------------------------------------------------------

def test_fetch_xml_uses_europepmc_and_returns_bytes(mocker):
    net = _FakeNet(xml={"PMC5": JATS})
    _install(mocker, net)
    body, url = fulltext.fetch_xml("PMC5")
    assert body == JATS
    assert url == "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC5/fullTextXML"


def test_fetch_xml_refuses_a_body_that_is_not_jats(mocker):
    mocker.patch.object(
        fulltext.requests, "get",
        return_value=_FakeResponse(content=b"<html><body>maintenance</body></html>"),
    )
    with pytest.raises(fulltext.FullTextError, match="article"):
        fulltext.fetch_xml("PMC6")


# --- the per-PMID result model ----------------------------------------------

def test_result_model_has_no_defaults():
    """schema.py's contract: absence is stated by the caller, never defaulted."""
    for name, field in FullTextResult.model_fields.items():
        assert field.is_required(), f"{name} has a default"


def test_status_values_are_the_four_stated():
    assert set(fulltext.STATUSES) == {
        "retrieved", "no_pmcid", "not_open_access", "fetch_failed",
    }


def _kwargs(**over):
    base = dict(
        pmid="1", status="retrieved", pmcid="PMC1", doi=None, license="CC BY",
        source_url="https://x", xml_path="PMC1.xml", xml_sha256="a" * 64,
        retrieved_at="2026-10-29T10:00:00Z", checked_at="2026-10-29T10:00:00Z",
        detail=None, tool_version="0.1.0",
    )
    return {**base, **over}


def test_result_retrieved_requires_hash_and_path():
    with pytest.raises(ValidationError):
        FullTextResult(**_kwargs(xml_sha256=None))
    with pytest.raises(ValidationError):
        FullTextResult(**_kwargs(xml_path=None))


def test_result_rejects_a_malformed_hash():
    with pytest.raises(ValidationError):
        FullTextResult(**_kwargs(xml_sha256="not-a-hash"))


def test_result_non_retrieved_cannot_carry_retrieval_fields():
    with pytest.raises(ValidationError):
        FullTextResult(**_kwargs(status="not_open_access", detail="closed"))


def test_result_no_pmcid_cannot_carry_a_pmcid():
    with pytest.raises(ValidationError):
        FullTextResult(**_kwargs(
            status="no_pmcid", license=None, source_url=None, xml_path=None,
            xml_sha256=None, retrieved_at=None,
        ))


def test_result_fetch_failed_requires_a_detail():
    with pytest.raises(ValidationError):
        FullTextResult(**_kwargs(
            status="fetch_failed", license=None, source_url=None, xml_path=None,
            xml_sha256=None, retrieved_at=None, detail=None,
        ))


# --- the batch driver --------------------------------------------------------

def _mixed_net():
    return _FakeNet(
        idconv={
            "101": _rec("101", pmcid="PMC101", doi="10.1/101"),
            "102": _rec("102", status="error", errmsg="Identifier not found in PMC"),
            "103": _rec("103", pmcid="PMC103"),
            "104": _rec("104", pmcid="PMC104"),
            # "105" deliberately omitted from the idconv response
        },
        oa={"PMC101": "open", "PMC103": "closed", "PMC104": "open"},
        xml={"PMC101": JATS},  # PMC104 is OA but Europe PMC 404s
    )


def _by_pmid(results):
    return {r.pmid: r for r in results}


def test_retrieve_assigns_each_status(tmp_path, mocker):
    _install(mocker, _mixed_net())
    log = tmp_path / "log.jsonl"

    counts = fulltext.retrieve(
        ["101", "102", "103", "104", "105"], tmp_path / "xml", log
    )
    results = _by_pmid(fulltext.read_log(log))

    assert results["101"].status == "retrieved"
    assert results["102"].status == "no_pmcid"
    assert results["103"].status == "not_open_access"
    assert results["104"].status == "fetch_failed"
    assert results["105"].status == "fetch_failed"
    assert "omitted" in results["105"].detail
    assert counts == {
        "requested": 5, "skipped": 0, "retrieved": 1, "no_pmcid": 1,
        "not_open_access": 1, "fetch_failed": 2,
    }


def test_retrieve_saves_xml_and_records_its_sha256(tmp_path, mocker):
    _install(mocker, _mixed_net())
    out = tmp_path / "xml"
    fulltext.retrieve(["101"], out, tmp_path / "log.jsonl")

    result = fulltext.read_log(tmp_path / "log.jsonl")[0]
    saved = out / "PMC101.xml"
    assert saved.read_bytes() == JATS
    assert result.xml_sha256 == hashlib.sha256(JATS).hexdigest()
    assert result.xml_path == "PMC101.xml"
    assert result.pmcid == "PMC101"
    assert result.doi == "10.1/101"
    assert result.license == "CC BY"
    assert result.source_url.endswith("/PMC101/fullTextXML")
    assert result.retrieved_at.endswith("Z")


def test_network_failure_after_retries_is_fetch_failed_not_a_crash(tmp_path, mocker):
    """One dead endpoint must cost one record, not the batch."""
    net = _FakeNet(
        idconv={"201": _rec("201", pmcid="PMC201"), "202": _rec("202", pmcid="PMC202")},
        oa={"PMC201": "open", "PMC202": "open"},
        xml={"PMC202": JATS},
    )

    def flaky(url, params=None, timeout=None):
        if url.endswith("/PMC201/fullTextXML"):
            raise requests.ConnectionError("reset by peer")
        return net(url, params=params, timeout=timeout)

    get = mocker.patch.object(fulltext.requests, "get", side_effect=flaky)
    fulltext.retrieve(["201", "202"], tmp_path / "xml", tmp_path / "log.jsonl")

    results = _by_pmid(fulltext.read_log(tmp_path / "log.jsonl"))
    assert results["201"].status == "fetch_failed"
    assert "reset by peer" in results["201"].detail
    assert results["201"].pmcid == "PMC201"
    assert results["202"].status == "retrieved"
    xml_calls = [c for c in get.call_args_list if c.args[0].endswith("/PMC201/fullTextXML")]
    assert len(xml_calls) == fulltext.MAX_ATTEMPTS


def test_idconv_batch_failure_marks_the_batch_fetch_failed_not_no_pmcid(tmp_path, mocker):
    """A conversion that never happened says nothing about whether a PMCID exists."""
    mocker.patch.object(
        fulltext.requests, "get", side_effect=requests.Timeout("timed out")
    )
    fulltext.retrieve(["301", "302"], tmp_path / "xml", tmp_path / "log.jsonl")
    results = fulltext.read_log(tmp_path / "log.jsonl")
    assert {r.status for r in results} == {"fetch_failed"}
    assert all(r.pmcid is None and r.doi is None for r in results)


def test_not_open_access_does_not_fetch(tmp_path, mocker):
    net = _mixed_net()
    _install(mocker, net)
    fulltext.retrieve(["103"], tmp_path / "xml", tmp_path / "log.jsonl")
    assert net.urls("https://www.ebi.ac.uk/") == []
    assert not (tmp_path / "xml" / "PMC103.xml").exists()


def test_no_field_is_ever_defaulted_to_a_placeholder(tmp_path, mocker):
    """Every field a status does not establish is None: never '', 'unknown', 0."""
    _install(mocker, _mixed_net())
    log = tmp_path / "log.jsonl"
    fulltext.retrieve(["101", "102", "103", "104", "105"], tmp_path / "xml", log)

    placeholders = {"", "unknown", "n/a", "na", "none", "null", "0", "-"}
    for line in log.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        for key, value in entry.items():
            if isinstance(value, str):
                assert value.strip().lower() not in placeholders, (key, value)
            assert value != 0, (key, value)

    results = _by_pmid(fulltext.read_log(log))
    for pmid in ("102", "103", "104", "105"):
        r = results[pmid]
        assert r.xml_path is None and r.xml_sha256 is None
        assert r.retrieved_at is None and r.source_url is None
    assert results["102"].pmcid is None and results["102"].doi is None
    assert results["105"].pmcid is None and results["105"].doi is None
    assert results["103"].license is None
    assert results["103"].doi is None  # idconv gave none; not copied from elsewhere


def test_retrieve_skips_pmids_already_in_the_log(tmp_path, mocker):
    net = _mixed_net()
    _install(mocker, net)
    log = tmp_path / "log.jsonl"
    fulltext.retrieve(["101", "102"], tmp_path / "xml", log)
    net.calls.clear()

    counts = fulltext.retrieve(["101", "102", "103"], tmp_path / "xml", log)

    idconv_ids = [p["ids"] for _, p in net.urls(fulltext.IDCONV_URL)]
    assert idconv_ids == ["103"]
    assert counts["skipped"] == 2
    assert [r.pmid for r in fulltext.read_log(log)] == ["101", "102", "103"]


def test_resume_does_not_retry_failures_unless_asked(tmp_path, mocker):
    net = _mixed_net()
    _install(mocker, net)
    log = tmp_path / "log.jsonl"
    fulltext.retrieve(["104"], tmp_path / "xml", log)

    net.calls.clear()
    assert fulltext.retrieve(["104"], tmp_path / "xml", log)["skipped"] == 1
    assert net.calls == []

    net.xml["PMC104"] = JATS
    counts = fulltext.retrieve(["104"], tmp_path / "xml", log, retry_failed=True)
    assert counts["retrieved"] == 1
    statuses = [r.status for r in fulltext.read_log(log)]
    assert statuses == ["fetch_failed", "retrieved"]  # append-only: history kept


def test_retrieve_will_not_overwrite_a_differing_xml_file(tmp_path, mocker):
    _install(mocker, _mixed_net())
    out = tmp_path / "xml"
    out.mkdir()
    (out / "PMC101.xml").write_bytes(b"<article>older</article>")

    fulltext.retrieve(["101"], out, tmp_path / "log.jsonl")

    result = fulltext.read_log(tmp_path / "log.jsonl")[0]
    assert result.status == "fetch_failed"
    assert "differ" in result.detail
    assert (out / "PMC101.xml").read_bytes() == b"<article>older</article>"


def test_read_log_of_missing_file_is_empty(tmp_path):
    assert fulltext.read_log(tmp_path / "absent.jsonl") == []


# --- CLI ---------------------------------------------------------------------

def test_load_pmids_strips_blanks_and_duplicates(tmp_path):
    path = tmp_path / "pmids.txt"
    path.write_text("101\n\n 102 \n101\n", encoding="utf-8")
    assert fulltext.load_pmids(path) == ["101", "102"]


def test_load_pmids_refuses_a_non_numeric_line(tmp_path):
    path = tmp_path / "pmids.txt"
    path.write_text("101\nPMC102\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        fulltext.load_pmids(path)


def test_main_runs_end_to_end_on_fixtures(tmp_path, mocker, capsys):
    _install(mocker, _mixed_net())
    pmids = tmp_path / "pmids.txt"
    pmids.write_text("101\n102\n", encoding="utf-8")
    log = tmp_path / "log.jsonl"
    mocker.patch.object(sys, "argv", [
        "fulltext", "--pmids", str(pmids), "--out-dir", str(tmp_path / "xml"),
        "--log", str(log),
    ])

    fulltext.main()

    out = capsys.readouterr().out
    assert "retrieved: 1" in out
    assert "no_pmcid: 1" in out
    assert len(fulltext.read_log(log)) == 2


def test_fetch_xml_refuses_a_body_declaring_entities(mocker):
    body = (b'<?xml version="1.0"?><!DOCTYPE article [<!ENTITY a "aaaa">]>'
            b"<article>&a;</article>")
    mocker.patch.object(fulltext.requests, "get", return_value=_FakeResponse(content=body))
    with pytest.raises(fulltext.FullTextError, match="entities"):
        fulltext.fetch_xml("PMC7")
