"""ClinicalTrials.gov client tests. All HTTP is mocked; the suite never touches the network."""
import pytest

from pipeline import clinicaltrials
from pipeline.schema import RegistryRecord

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


def _study(nct="NCT00000001", **overrides):
    """A minimal well-formed registration, overridable per test."""
    protocol = {
        "identificationModule": {"nctId": nct, "briefTitle": "A methylation trial"},
        "statusModule": {"overallStatus": "COMPLETED"},
        "designModule": {"studyType": "INTERVENTIONAL"},
    }
    for key, value in overrides.pop("protocol", {}).items():
        protocol[key] = value
    study = {"protocolSection": protocol, "hasResults": False}
    study.update(overrides)
    return study


def _page(studies, total, next_token=None):
    body = {"totalCount": total, "studies": studies}
    if next_token is not None:
        body["nextPageToken"] = next_token
    return body


def _serve(mocker, pages):
    """Serve `pages` in order, capping total requests so a loop fails fast."""
    calls = {"n": 0}

    def _get(url, params=None, timeout=None):
        calls["n"] += 1
        if calls["n"] > REQUEST_CAP:
            raise AssertionError(
                f"more than {REQUEST_CAP} requests; pagination is not terminating"
            )
        return _FakeResponse(pages[min(calls["n"] - 1, len(pages) - 1)])

    mocker.patch.object(clinicaltrials.requests, "get", side_effect=_get)
    mocker.patch.object(clinicaltrials.time, "sleep")
    return calls


# --- the query ---------------------------------------------------------------


def test_the_core_block_is_restricted_to_title_and_summary():
    """The [tiab] analogue. Unrestricted, `query.term` matches the whole record.

    Measured live 2026-09-17: the core block restricted returns 694
    registrations, unrestricted 1,771. Losing this restriction inflates the
    registry stream two and a half fold with trials that merely mention a
    methylation assay somewhere in their eligibility criteria.
    """
    query = clinicaltrials.build_registry_query()

    assert "AREA[BriefTitle]" in query
    assert "AREA[BriefSummary]" in query
    assert "DNA methylation" in query and "epigenetic clock" in query


def test_multiword_terms_are_quoted():
    """Essie reads an unquoted space as AND, so an unquoted phrase silently
    narrows the search to records containing both words anywhere."""
    query = clinicaltrials.build_registry_query()

    for phrase in ("DNA methylation", "epigenetic clock", "histone deacetylase"):
        assert f'"{phrase}"' in query, f"{phrase!r} is not quoted"


def test_the_search_is_limited_to_the_registered_window():
    """2015 onward, expressed against StartDate."""
    assert "2015-01-01" in clinicaltrials.START_DATE_FILTER
    assert "StartDate" in clinicaltrials.START_DATE_FILTER


# --- mapping -----------------------------------------------------------------


def test_a_registration_maps_to_a_registry_record():
    record = clinicaltrials.to_record(_study(), QH, "2026-09-17T00:00:00Z")

    assert isinstance(record, RegistryRecord)
    assert record.source_db == "ctgov"
    assert record.source_id == "NCT00000001"
    assert record.title == "A methylation trial"
    assert record.query_hash == QH


def test_a_registration_without_an_nct_id_raises():
    study = _study()
    study["protocolSection"]["identificationModule"].pop("nctId")

    with pytest.raises(clinicaltrials.ClinicalTrialsError, match="no nctId"):
        clinicaltrials.to_record(study, QH, "2026-09-17T00:00:00Z")


def test_a_registration_without_a_title_raises_rather_than_defaulting():
    study = _study()
    study["protocolSection"]["identificationModule"]["briefTitle"] = "   "

    with pytest.raises(clinicaltrials.ClinicalTrialsError, match="no briefTitle"):
        clinicaltrials.to_record(study, QH, "2026-09-17T00:00:00Z")


def test_absent_fields_become_none_not_placeholders():
    """The no-default contract: absence is stated, never filled in."""
    record = clinicaltrials.to_record(_study(), QH, "2026-09-17T00:00:00Z")

    assert record.summary is None
    assert record.enrollment is None
    assert record.enrollment_is_actual is None
    assert record.completion_date is None
    assert record.completion_is_actual is None
    assert record.sponsor is None
    assert record.phases == [] and record.conditions == []


# --- the distinction the overlay turns on ------------------------------------


def test_an_estimated_completion_date_is_not_recorded_as_actual():
    """A 2019 ESTIMATED completion says nothing about whether the trial finished.

    Collapsing ESTIMATED into ACTUAL would manufacture "completed but
    unreported" trials out of abandoned projections -- inventing exactly the
    finding this overlay exists to report.
    """
    study = _study()
    study["protocolSection"]["statusModule"]["completionDateStruct"] = {
        "date": "2019-06-01", "type": "ESTIMATED"
    }

    record = clinicaltrials.to_record(study, QH, "2026-09-17T00:00:00Z")

    assert record.completion_date == "2019-06-01"
    assert record.completion_is_actual is False


def test_an_actual_completion_date_is_recorded_as_actual():
    study = _study()
    study["protocolSection"]["statusModule"]["completionDateStruct"] = {
        "date": "2019-06-01", "type": "ACTUAL"
    }

    record = clinicaltrials.to_record(study, QH, "2026-09-17T00:00:00Z")

    assert record.completion_is_actual is True


def test_an_unlabelled_date_yields_none_rather_than_a_guess():
    study = _study()
    study["protocolSection"]["statusModule"]["completionDateStruct"] = {
        "date": "2019-06-01"
    }

    record = clinicaltrials.to_record(study, QH, "2026-09-17T00:00:00Z")

    assert record.completion_date == "2019-06-01"
    assert record.completion_is_actual is None


def test_an_estimated_enrolment_is_not_recorded_as_actual():
    study = _study()
    study["protocolSection"]["designModule"]["enrollmentInfo"] = {
        "count": 250, "type": "ESTIMATED"
    }

    record = clinicaltrials.to_record(study, QH, "2026-09-17T00:00:00Z")

    assert record.enrollment == 250
    assert record.enrollment_is_actual is False


def test_only_result_publications_count_as_reporting():
    """A BACKGROUND citation is a paper the investigators read.

    Counting it would make an unreported trial look reported, which is the one
    error this overlay must not make.
    """
    study = _study()
    study["protocolSection"]["referencesModule"] = {"references": [
        {"pmid": "111", "type": "BACKGROUND"},
        {"pmid": "222", "type": "RESULT"},
        {"pmid": "333", "type": "DERIVED"},
        {"type": "RESULT"},                      # no pmid
    ]}

    record = clinicaltrials.to_record(study, QH, "2026-09-17T00:00:00Z")

    assert record.result_pmids == ["222", "333"]


def test_registry_posted_results_are_tracked_separately_from_publication():
    """Posting results to the registry is a legal duty distinct from publishing."""
    study = _study(hasResults=True)

    record = clinicaltrials.to_record(study, QH, "2026-09-17T00:00:00Z")

    assert record.has_results is True
    assert record.result_pmids == []


# --- retrieval ---------------------------------------------------------------


def test_a_single_page_result_set_is_returned(mocker):
    _serve(mocker, [_page([_study("NCT1"), _study("NCT2")], total=2)])

    records = clinicaltrials.search_records("q", QH)

    assert [r.source_id for r in records] == ["NCT1", "NCT2"]


def test_pagination_follows_the_page_token(mocker):
    _serve(mocker, [
        _page([_study("NCT1")], total=3, next_token="t2"),
        _page([_study("NCT2")], total=3, next_token="t3"),
        _page([_study("NCT3")], total=3),
    ])

    records = clinicaltrials.search_records("q", QH)

    assert [r.source_id for r in records] == ["NCT1", "NCT2", "NCT3"]


def test_exhaustion_short_of_the_total_is_refused(mocker):
    """"No more pages" must never be allowed to mean "stream truncated".

    A registry that returned half its matches without an error would understate
    precisely what this stream measures: how much evidence is in flight.
    """
    _serve(mocker, [_page([_study("NCT1")], total=694)])

    with pytest.raises(clinicaltrials.ClinicalTrialsError, match="silently truncated"):
        clinicaltrials.search_records("q", QH)


def test_a_looping_page_token_is_refused(mocker):
    """Repeats would inflate the count and still look like a clean run."""
    _serve(mocker, [
        _page([_study("NCT1")], total=2, next_token="t2"),
        _page([_study("NCT1")], total=2, next_token="t3"),
    ])

    with pytest.raises(clinicaltrials.ClinicalTrialsError, match="returned twice"):
        clinicaltrials.search_records("q", QH)


def test_an_empty_page_with_records_outstanding_is_refused(mocker):
    _serve(mocker, [
        _page([_study("NCT1")], total=3, next_token="t2"),
        _page([], total=3, next_token="t3"),
    ])

    with pytest.raises(clinicaltrials.ClinicalTrialsError, match="0 registrations"):
        clinicaltrials.search_records("q", QH)


def test_a_response_without_studies_is_refused(mocker):
    _serve(mocker, [{"totalCount": 1}])

    with pytest.raises(clinicaltrials.ClinicalTrialsError, match="missing 'studies'"):
        clinicaltrials.search_records("q", QH)


def test_a_response_without_a_total_is_refused(mocker):
    _serve(mocker, [{"studies": []}])

    with pytest.raises(clinicaltrials.ClinicalTrialsError, match="missing 'totalCount'"):
        clinicaltrials.search_records("q", QH)


def test_the_client_sends_no_credential(mocker):
    """ClinicalTrials.gov needs no key, and this module must never invent one."""
    captured = {}

    def _get(url, params=None, timeout=None):
        captured.update(params or {})
        return _FakeResponse(_page([_study("NCT1")], total=1))

    mocker.patch.object(clinicaltrials.requests, "get", side_effect=_get)
    mocker.patch.object(clinicaltrials.time, "sleep")

    clinicaltrials.search_records("q", QH)

    joined = " ".join(str(k) + str(v) for k, v in captured.items()).lower()
    for forbidden in ("key", "token=", "secret", "auth"):
        assert forbidden not in joined.replace("pagetoken", ""), captured
