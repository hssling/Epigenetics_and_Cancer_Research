"""ClinicalTrials.gov API v2 client — the registered trial-registry search.

Why this source exists
----------------------
Protocol Section 4.1 commits to two trial registries, ClinicalTrials.gov and
WHO ICTRP, for a purpose distinct from the bibliographic databases: to identify
unpublished and ongoing studies, and to populate a "registered but unreported"
overlay showing where evidence is in flight. Until now both were recorded as
"not yet searched" (protocol/amendments.md; PRISMA-S item 3).

These records do NOT join the screening corpus. A registration is not a
publication, and merging the two streams would let a trial that was registered
and never published be counted as evidence. PRISMA 2020 gives registers their
own identification column, and so does this pipeline.

WHO ICTRP
---------
Not searched here, and the reason is narrower than "no access". ICTRP does
publish a Search Portal Web Service, and its portal does allow search results to
be downloaded as CSV or XML. Neither is callable unattended: the web service
operates on an agreed-partner basis arranged with WHO, and the portal download
is an interactive step requiring acceptance of WHO's Terms and Conditions, which
this pipeline does not accept on the investigator's behalf.

ICTRP therefore remains available as a MANUAL step and is recorded as
outstanding, not impossible. The coverage loss meanwhile is smaller than it
sounds -- ICTRP aggregates ClinicalTrials.gov along with the other primary
registries -- but it is real for trials registered ONLY in a non-US registry,
and it is carried in the limitations rather than offset by a claim of
equivalence.

How the registered strategy was translated, and what was measured
-----------------------------------------------------------------
The PubMed strategy is CORE AND HUMAN AND (EXPOSURE OR CLINICAL_USE) AND DESIGN
AND YEARS, every term restricted to [tiab]. Translating it clause by clause,
with live counts taken 2026-09-17:

* HUMAN is dropped. ClinicalTrials.gov registers human studies only, so the
  clause is vacuous rather than relaxed.

* DESIGN is dropped for the same reason. Its purpose in PubMed is to exclude
  reviews, editorials and case reports; a registry contains none of those. Both
  study types are kept (interventional 380, observational 314 of 694).

* The [tiab] restriction is kept, as `AREA[BriefTitle]` OR `AREA[BriefSummary]`.
  This is the clause that does the work: unrestricted, `query.term` matches the
  whole record including eligibility criteria and outcome descriptions, and the
  core block returns 1,771 rather than 694. This is the same trap as Europe
  PMC's full-text default.

* (EXPOSURE OR CLINICAL_USE) is dropped, and this one is a judgement rather
  than a formality. Measured three ways: restricted to title/summary like the
  core block it yields 535; applied unrestricted, 679; omitted, 694. It is
  dropped because in a registry those concepts live in the structured
  intervention and outcome-measure fields, not in the summary prose -- a diet
  trial's brief summary often never uses the word "diet". Dropping a fifth of
  the registry stream on a clause the record format cannot express would be an
  artefact of the source, not an eligibility decision. Eligibility is decided
  at screening, where these records are judged on the same instrument as
  everything else.

The net effect is a wider net over a much smaller pool: 694 registrations
against 9,786 bibliographic records. For an overlay whose question is "what is
in flight that we cannot see yet", under-retrieval is the expensive error.

No API key. ClinicalTrials.gov API v2 requires none, and this module sends no
credential of any kind. Absent fields become explicit None; nothing is
defaulted.
"""
import time
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from pipeline.schema import RegistryRecord

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
MAX_ATTEMPTS = 3
RATE_LIMIT_SECONDS = 0.34
PAGE_SIZE = 200

# The registered window. Expressed against StartDate because a registration's
# publication year has no meaning -- the analogue of "when did this research
# happen" is when the study started.
START_DATE_FILTER = "AREA[StartDate]RANGE[2015-01-01,MAX]"


class ClinicalTrialsError(Exception):
    """Raised when the registry cannot be reached or returns an unusable body."""


def _get(params: dict[str, Any]) -> dict[str, Any]:
    last: Optional[Exception] = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.get(BASE_URL, params=params, timeout=120)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001 - re-raised below
            last = exc
            time.sleep(RATE_LIMIT_SECONDS * (attempt + 1) * 3)
    raise ClinicalTrialsError(
        f"ClinicalTrials.gov search failed after {MAX_ATTEMPTS} attempts: {last}"
    ) from last


# ---------------------------------------------------------------------------
# Query construction
# ---------------------------------------------------------------------------

# Term lists reproduced from the registered PubMed strategy so the two cannot
# drift. Phrases are quoted; Essie treats an unquoted space as AND.
METHYLATION = (
    '"DNA methylation" OR methylome OR EWAS OR "epigenome-wide" OR CpG '
    'OR "5-methylcytosine" OR hydroxymethylation'
)
HISTONE = (
    'histone OR histones OR chromatin OR H3K4 OR H3K27 OR HDAC '
    'OR "histone deacetylase"'
)
CLOCK = (
    '"epigenetic clock" OR "epigenetic age" OR "DNAm age" OR GrimAge '
    'OR PhenoAge OR "Horvath clock" OR "biological age"'
)
CORE = f"({METHYLATION}) OR ({HISTONE}) OR ({CLOCK})"


def _title_or_summary(block: str) -> str:
    """Restrict a term block to the brief title or brief summary.

    This is the [tiab] analogue and it is load-bearing. Without it `query.term`
    searches the entire registration -- eligibility criteria, outcome measures,
    detailed description -- and the core block returns 1,771 instead of 694.
    See the module docstring; do not "simplify" this away.
    """
    return f"(AREA[BriefTitle]({block}) OR AREA[BriefSummary]({block}))"


def build_registry_query() -> str:
    """The registered strategy as ClinicalTrials.gov can express it."""
    return _title_or_summary(CORE)


def _search_params(query: str, page_token: Optional[str]) -> dict[str, Any]:
    params: dict[str, Any] = {
        "query.term": query,
        "filter.advanced": START_DATE_FILTER,
        "pageSize": PAGE_SIZE,
        "countTotal": "true",
    }
    if page_token is not None:
        params["pageToken"] = page_token
    return params


def count(query: str) -> int:
    """Number of registrations matching `query`, without retrieving them."""
    params = _search_params(query, None)
    params["pageSize"] = 1
    body = _get(params)
    if "totalCount" not in body:
        raise ClinicalTrialsError(
            f"response missing 'totalCount' for query: {query!r}"
        )
    return int(body["totalCount"])


# ---------------------------------------------------------------------------
# Mapping
# ---------------------------------------------------------------------------

def _date(struct: Any) -> tuple[Optional[str], Optional[bool]]:
    """Return (date, is_actual). `is_actual` is None when the registry is silent.

    ClinicalTrials.gov marks each date ACTUAL or ESTIMATED. The overlay's whole
    question -- has this trial finished without reporting? -- depends on the
    difference, so an unlabelled date yields None rather than a guess.
    """
    if not isinstance(struct, dict):
        return None, None
    date = (struct.get("date") or "").strip() or None
    kind = (struct.get("type") or "").strip().upper()
    if kind == "ACTUAL":
        return date, True
    if kind == "ESTIMATED":
        return date, False
    return date, None


def _interventions(protocol: dict[str, Any]) -> list[str]:
    arms = protocol.get("armsInterventionsModule") or {}
    names = []
    for item in arms.get("interventions") or []:
        name = (item.get("name") or "").strip()
        if name:
            kind = (item.get("type") or "").strip()
            names.append(f"{kind}: {name}" if kind else name)
    return names


def _result_pmids(study: dict[str, Any]) -> list[str]:
    """PMIDs the registry itself links as REPORTING this trial's results.

    `referencesModule` mixes background citations with result publications.
    Only DERIVED and RESULT types are claims about this trial's findings; a
    BACKGROUND citation is a paper the investigators read, and counting it as
    a report would make an unreported trial look reported.
    """
    references = (study.get("protocolSection", {})
                  .get("referencesModule", {})
                  .get("references") or [])
    pmids = []
    for reference in references:
        if (reference.get("type") or "").strip().upper() in {"RESULT", "DERIVED"}:
            pmid = (reference.get("pmid") or "").strip()
            if pmid:
                pmids.append(pmid)
    return pmids


def to_record(
    study: dict[str, Any], query_hash_value: str, retrieved_at: str
) -> RegistryRecord:
    """Map one registration. An absent NCT id or title raises rather than defaults."""
    protocol = study.get("protocolSection") or {}
    identification = protocol.get("identificationModule") or {}

    nct_id = (identification.get("nctId") or "").strip()
    if not nct_id:
        raise ClinicalTrialsError(
            f"registration has no nctId; it cannot be identified: {study!r}"
        )

    title = (identification.get("briefTitle") or "").strip()
    if not title:
        raise ClinicalTrialsError(
            f"registration {nct_id} has no briefTitle; title is required and "
            "must never be defaulted to an empty string"
        )

    status_module = protocol.get("statusModule") or {}
    design = protocol.get("designModule") or {}
    enrollment_info = design.get("enrollmentInfo") or {}
    enrollment_kind = (enrollment_info.get("type") or "").strip().upper()

    start_date, _ = _date(status_module.get("startDateStruct"))
    primary_completion, _ = _date(status_module.get("primaryCompletionDateStruct"))
    completion, completion_is_actual = _date(
        status_module.get("completionDateStruct")
    )

    sponsor = ((protocol.get("sponsorCollaboratorsModule") or {})
               .get("leadSponsor") or {}).get("name")

    return RegistryRecord(
        source_db="ctgov",
        source_id=nct_id,
        title=title,
        summary=((protocol.get("descriptionModule") or {})
                 .get("briefSummary") or "").strip() or None,
        status=(status_module.get("overallStatus") or "").strip() or None,
        study_type=(design.get("studyType") or "").strip() or None,
        phases=list(design.get("phases") or []),
        conditions=list((protocol.get("conditionsModule") or {})
                        .get("conditions") or []),
        interventions=_interventions(protocol),
        enrollment=enrollment_info.get("count"),
        enrollment_is_actual=(
            True if enrollment_kind == "ACTUAL"
            else False if enrollment_kind == "ESTIMATED"
            else None
        ),
        start_date=start_date,
        primary_completion_date=primary_completion,
        completion_date=completion,
        completion_is_actual=completion_is_actual,
        sponsor=(sponsor or "").strip() or None,
        has_results=bool(study.get("hasResults")),
        result_pmids=_result_pmids(study),
        retrieved_at=retrieved_at,
        query_hash=query_hash_value,
    )


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def search_records(query: str, query_hash_value: str) -> list[RegistryRecord]:
    """Retrieve every registration matching `query`, paginating by pageToken.

    Exhaustion is signalled by omitting `nextPageToken`. That signal is not
    taken at face value: it is cross-checked against `totalCount`, so "no more
    pages" can never quietly mean "stream truncated". A registry that returned
    half its matches without an error would understate exactly the thing this
    stream exists to measure -- how much evidence is in flight and unseen.
    """
    records: list[RegistryRecord] = []
    seen_ids: set[str] = set()
    page_token: Optional[str] = None
    total: Optional[int] = None

    while True:
        body = _get(_search_params(query, page_token))

        if total is None:
            if "totalCount" not in body:
                raise ClinicalTrialsError(
                    f"response missing 'totalCount' for query: {query!r}"
                )
            total = int(body["totalCount"])

        if "studies" not in body:
            raise ClinicalTrialsError(
                f"response missing 'studies' at pageToken {page_token!r}; the "
                "page would otherwise vanish from the stream with no error"
            )
        page = body["studies"]

        if not page and len(records) < total:
            raise ClinicalTrialsError(
                f"returned 0 registrations at pageToken {page_token!r} while "
                f"{total - len(records)} of {total} were still outstanding"
            )

        retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for study in page:
            record = to_record(study, query_hash_value, retrieved_at)
            # A repeated NCT id means the page token is looping. Left
            # unchecked it would inflate the count with duplicates of the
            # same trial and still look like a clean run.
            if record.source_id in seen_ids:
                raise ClinicalTrialsError(
                    f"registration {record.source_id} returned twice; the page "
                    "token is looping and the stream is not what was counted"
                )
            seen_ids.add(record.source_id)
            records.append(record)

        next_token = body.get("nextPageToken")
        if not next_token:
            if len(records) < total:
                raise ClinicalTrialsError(
                    f"registry signalled exhaustion at pageToken {page_token!r} "
                    f"with only {len(records)} of {total} registrations "
                    "retrieved; the stream would be silently truncated"
                )
            return records

        page_token = next_token
        time.sleep(RATE_LIMIT_SECONDS)
