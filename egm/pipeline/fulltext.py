"""Full-text retrieval for Stage 3 (spec section 7.1): PMID -> PMCID -> JATS XML.

This stage is gated. Title/abstract screening is complete but unreportable
until the human calibration passes (manuscript/STATUS.md), and Stage 3 reads
the screening include set. This module is the retrieval tooling only; do not
point it at the corpus or the include set before the Stage 0 gate passes.

Three steps per PMID
--------------------
1. NCBI PMC ID Converter, in batches of at most 200 (the service's limit),
   resolves PMID -> PMCID and DOI.
2. The PMC OA web service states whether that PMCID is in the open-access
   subset.
3. Europe PMC `fullTextXML` returns the JATS XML, which is saved and hashed.

Why Europe PMC is the primary (and only) source of the XML
----------------------------------------------------------
The PMC OA web service does not return article XML. It returns links to a
`.tar.gz` package (and sometimes a PDF) on NCBI's FTP server, so using it as
the source would mean a second protocol, an archive to unpack, and a choice of
which member inside it is "the" article. Europe PMC mirrors the PMC
open-access subset and serves the JATS document itself, over HTTPS, in one
request, addressed by the same PMCID. What is hashed is exactly what was
served.

Why the PMC OA service is still called
--------------------------------------
For the open-access decision, not the content. Europe PMC answers a missing
full text with a bare 404, which cannot be told apart from a wrong ID, an
article not yet mirrored, or a transient fault. The OA service answers with a
coded refusal (`idIsNotOpenAccess`), so `not_open_access` is recorded only when
NCBI said so, and every other failure is `fetch_failed`. The OA subset is also
the set licensed for reuse, which matters because Stage 3 coding is AI text
mining; the licence is recorded with the result. There is no fallback between
the two services: if NCBI says open access and Europe PMC cannot serve the
XML, the record is `fetch_failed`, not silently sourced from somewhere else.

Absent values are explicit None (spec section 8.3 rule 1). A PMID the ID
converter omitted is `fetch_failed`, not `no_pmcid`: a conversion that did not
happen says nothing about whether a PMCID exists. No network failure is
allowed to end a run; it costs the record it happened to, which is logged as
`fetch_failed` with the error and can be retried with `--retry-failed`.

The log is append-only JSONL, one result per line, fsynced. A PMID already in
the log is skipped, which is what makes an interrupted run resumable. When a
PMID appears more than once (a retried failure), the last line is current and
the earlier ones are its history.

Run (fixtures only until the Stage 0 gate passes):
    python -m pipeline.fulltext \\
        --pmids pmids.txt --out-dir fulltext/xml --log fulltext/retrieval.jsonl
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Literal, NamedTuple, Optional

import requests
from pydantic import BaseModel, ConfigDict, Field, model_validator

from pipeline.config import NCBI_RATE_LIMIT_SECONDS, NCBI_TOOL_NAME
from pipeline.europepmc import RATE_LIMIT_SECONDS as EUROPEPMC_RATE_LIMIT_SECONDS
from pipeline.provenance import TOOL_VERSION

IDCONV_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
OA_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
EUROPEPMC_FULLTEXT_URL = (
    "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
)
IDCONV_BATCH_SIZE = 200  # the ID converter's documented per-request maximum
MAX_ATTEMPTS = 3

# The one OA-service error code that means "this article is not open access".
# Any other code (idDoesNotExist, ...) is a failure to determine status.
OA_NOT_OPEN_ACCESS_CODE = "idIsNotOpenAccess"

FullTextStatus = Literal["retrieved", "no_pmcid", "not_open_access", "fetch_failed"]
STATUSES: tuple[FullTextStatus, ...] = (
    "retrieved", "no_pmcid", "not_open_access", "fetch_failed",
)


class FullTextError(Exception):
    """Raised when a service cannot be reached or returns an unusable body."""


class FullTextResult(BaseModel):
    """The outcome of retrieving one PMID's full text.

    Every field is required, including the Optional ones (schema.py's
    no-default contract): a caller must say a value is absent. The validator
    ties each status to the fields it does and does not establish, so a
    `retrieved` result without a hash, or a `no_pmcid` result carrying a
    PMCID, cannot be constructed.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    pmid: str = Field(pattern=r"^\d+$")
    status: FullTextStatus
    pmcid: Optional[str] = Field(pattern=r"^PMC\d+$")
    doi: Optional[str]
    license: Optional[str]
    source_url: Optional[str]
    # Relative to the run's --out-dir, so the log survives the directory moving.
    xml_path: Optional[str]
    xml_sha256: Optional[str] = Field(pattern=r"^[0-9a-f]{64}$")
    retrieved_at: Optional[str]
    # When the status was established. Set for every status; `retrieved_at` is
    # set only when XML was actually retrieved.
    checked_at: str
    detail: Optional[str]
    tool_version: str

    @model_validator(mode="after")
    def _status_rules(self) -> "FullTextResult":
        retrieval = {
            "source_url": self.source_url,
            "xml_path": self.xml_path,
            "xml_sha256": self.xml_sha256,
            "retrieved_at": self.retrieved_at,
        }
        if self.status == "retrieved":
            missing = [k for k, v in {**retrieval, "pmcid": self.pmcid}.items() if v is None]
            if missing:
                raise ValueError(f"a retrieved result requires {missing}")
        else:
            present = [k for k, v in retrieval.items() if v is not None]
            if present:
                raise ValueError(
                    f"{present} must be None when status is {self.status!r}: "
                    "nothing was retrieved"
                )

        if self.status == "no_pmcid" and (self.pmcid is not None or self.license is not None):
            raise ValueError("pmcid and license must be None when status is 'no_pmcid'")
        if self.status == "not_open_access" and self.pmcid is None:
            raise ValueError("a not_open_access result requires the pmcid that was checked")
        if self.status == "fetch_failed" and not (self.detail or "").strip():
            raise ValueError(
                "detail is required when status is 'fetch_failed': a failure "
                "without its cause cannot be diagnosed or retried sensibly"
            )
        return self


class IdConversion(NamedTuple):
    """One ID-converter record. `detail` carries the service's errmsg, if any."""

    pmcid: Optional[str]
    doi: Optional[str]
    detail: Optional[str]


class OpenAccessStatus(NamedTuple):
    is_open_access: bool
    license: Optional[str]
    detail: Optional[str]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _blank_to_none(value: Any) -> Optional[str]:
    """Strip a service-supplied value; an empty string is absence, not a value."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _request(
    url: str, params: Optional[dict[str, Any]], timeout: int, rate_limit: float
) -> requests.Response:
    last: Optional[Exception] = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as exc:  # noqa: BLE001 - re-raised as FullTextError below
            last = exc
            time.sleep(rate_limit * (attempt + 1) * 3)
    raise FullTextError(f"{url} failed after {MAX_ATTEMPTS} attempts: {last}") from last


def _get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET an NCBI JSON endpoint, with the tool name and retries."""
    params = {**params, "format": "json", "tool": NCBI_TOOL_NAME}
    response = _request(url, params, timeout=60, rate_limit=NCBI_RATE_LIMIT_SECONDS)
    try:
        return response.json()
    except ValueError as exc:
        raise FullTextError(f"{url} returned a body that is not JSON: {exc}") from exc


def _get_text(url: str, params: dict[str, Any]) -> str:
    """As _get, but for NCBI endpoints returning XML rather than JSON."""
    params = {**params, "tool": NCBI_TOOL_NAME}
    return _request(url, params, timeout=60, rate_limit=NCBI_RATE_LIMIT_SECONDS).text


def _get_bytes(url: str) -> bytes:
    """Raw body, undecoded, so the hash covers exactly what was served."""
    return _request(
        url, None, timeout=120, rate_limit=EUROPEPMC_RATE_LIMIT_SECONDS
    ).content


def _parse_xml(body: str | bytes, what: str) -> ET.Element:
    """Parse a service response, refusing any body that declares entities.

    defusedxml is not a project dependency. The stdlib parser does not fetch
    external entities, and neither the OA service nor JATS from Europe PMC
    declares internal ones, so a body that does is refused outright rather
    than expanded (the billion-laughs shape).
    """
    probe = body if isinstance(body, bytes) else body.encode("utf-8")
    if b"<!ENTITY" in probe:
        raise FullTextError(f"{what} declares XML entities; refusing to parse it")
    try:
        return ET.fromstring(body)
    except ET.ParseError as exc:
        raise FullTextError(f"{what} returned unparseable XML: {exc}") from exc


def resolve_ids(
    pmids: list[str], batch_size: int = IDCONV_BATCH_SIZE
) -> dict[str, IdConversion]:
    """Map each PMID to its PMCID and DOI via the PMC ID Converter.

    A PMID the response did not mention is left OUT of the result rather than
    mapped to an empty conversion; the caller decides what an omission means.
    Raises FullTextError if a batch cannot be retrieved.
    """
    if batch_size > IDCONV_BATCH_SIZE:
        raise ValueError(
            f"batch_size={batch_size} exceeds the ID converter's limit of "
            f"{IDCONV_BATCH_SIZE} ids per request"
        )

    resolved: dict[str, IdConversion] = {}
    for start in range(0, len(pmids), batch_size):
        batch = pmids[start : start + batch_size]
        body = _get(IDCONV_URL, {"ids": ",".join(batch), "idtype": "pmid"})
        if body.get("status") == "error":
            raise FullTextError(
                f"ID converter rejected a batch of {len(batch)} pmid(s) "
                f"(first={batch[0]!r}): {body.get('message') or body.get('errmsg')!r}"
            )
        if "records" not in body:
            raise FullTextError(
                f"ID converter response had no 'records' key for a batch of "
                f"{len(batch)} pmid(s) (first={batch[0]!r})"
            )

        wanted = set(batch)
        for record in body["records"]:
            key = _blank_to_none(record.get("requested-id")) or _blank_to_none(
                record.get("pmid")
            )
            if key not in wanted:
                continue
            resolved[key] = IdConversion(
                pmcid=_blank_to_none(record.get("pmcid")),
                doi=_blank_to_none(record.get("doi")),
                detail=_blank_to_none(record.get("errmsg")),
            )
        time.sleep(NCBI_RATE_LIMIT_SECONDS)
    return resolved


def check_open_access(pmcid: str) -> OpenAccessStatus:
    """Ask the PMC OA web service whether `pmcid` is in the open-access subset.

    Only the coded `idIsNotOpenAccess` refusal is read as "not open access".
    Any other error, or a body that cannot be read, raises FullTextError.
    """
    body = _get_text(OA_URL, {"id": pmcid})
    time.sleep(NCBI_RATE_LIMIT_SECONDS)
    root = _parse_xml(body, f"OA service response for {pmcid}")

    error = root.find("error")
    if error is not None:
        code = error.get("code")
        message = _blank_to_none(error.text)
        if code == OA_NOT_OPEN_ACCESS_CODE:
            return OpenAccessStatus(is_open_access=False, license=None, detail=message)
        raise FullTextError(f"OA service returned error {code!r} for {pmcid}: {message!r}")

    record = root.find("records/record")
    if record is None:
        raise FullTextError(f"OA service response for {pmcid} had neither a record nor an error")
    if record.get("id") != pmcid:
        raise FullTextError(
            f"OA service answered for {record.get('id')!r} when asked about {pmcid!r}"
        )
    return OpenAccessStatus(
        is_open_access=True, license=_blank_to_none(record.get("license")), detail=None
    )


def fetch_xml(pmcid: str) -> tuple[bytes, str]:
    """Fetch the JATS XML for `pmcid` from Europe PMC. Returns (body, url).

    The body must parse and have an <article> root. A maintenance page or an
    error document served with HTTP 200 is refused rather than saved as a
    full text.
    """
    url = EUROPEPMC_FULLTEXT_URL.format(pmcid=pmcid)
    body = _get_bytes(url)
    time.sleep(EUROPEPMC_RATE_LIMIT_SECONDS)
    root = _parse_xml(body, url)
    if root.tag != "article" and not root.tag.endswith("}article"):
        raise FullTextError(f"{url} returned <{root.tag}>, not a JATS <article>")
    return body, url


def _save_xml(out_dir: pathlib.Path, pmcid: str, body: bytes) -> tuple[str, str]:
    """Write the XML and return (path relative to out_dir, sha256).

    An existing file with identical bytes is accepted (an interrupted run that
    saved the file but not its log line). An existing file that differs is
    refused: retrieved artefacts are not silently replaced.
    """
    digest = hashlib.sha256(body).hexdigest()
    name = f"{pmcid}.xml"
    path = out_dir / name
    if path.exists():
        existing = hashlib.sha256(path.read_bytes()).hexdigest()
        if existing != digest:
            raise FullTextError(
                f"{path} exists and its contents differ from what was just "
                f"retrieved (sha256 {existing[:12]} vs {digest[:12]}); refusing "
                "to overwrite a retrieved artefact"
            )
        return name, digest

    out_dir.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(name + ".part")
    with partial.open("wb") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, path)
    return name, digest


def _not_retrieved(
    pmid: str,
    status: FullTextStatus,
    pmcid: Optional[str],
    doi: Optional[str],
    license: Optional[str],
    detail: Optional[str],
) -> FullTextResult:
    return FullTextResult(
        pmid=pmid, status=status, pmcid=pmcid, doi=doi, license=license,
        source_url=None, xml_path=None, xml_sha256=None, retrieved_at=None,
        checked_at=_now(), detail=detail, tool_version=TOOL_VERSION,
    )


def _retrieve_one(
    pmid: str,
    conversion: Optional[IdConversion],
    batch_error: Optional[str],
    out_dir: pathlib.Path,
) -> FullTextResult:
    if batch_error is not None:
        return _not_retrieved(
            pmid, "fetch_failed", None, None, None, f"ID conversion failed: {batch_error}"
        )
    if conversion is None:
        return _not_retrieved(
            pmid, "fetch_failed", None, None, None,
            "ID converter omitted this pmid from its response",
        )
    if conversion.pmcid is None:
        return _not_retrieved(pmid, "no_pmcid", None, conversion.doi, None, conversion.detail)

    pmcid, doi = conversion.pmcid, conversion.doi
    try:
        access = check_open_access(pmcid)
    except FullTextError as exc:
        return _not_retrieved(
            pmid, "fetch_failed", pmcid, doi, None, f"OA check failed: {exc}"
        )
    if not access.is_open_access:
        return _not_retrieved(pmid, "not_open_access", pmcid, doi, None, access.detail)

    try:
        body, url = fetch_xml(pmcid)
        xml_path, digest = _save_xml(out_dir, pmcid, body)
    except FullTextError as exc:
        return _not_retrieved(
            pmid, "fetch_failed", pmcid, doi, access.license, f"XML fetch failed: {exc}"
        )

    now = _now()
    return FullTextResult(
        pmid=pmid, status="retrieved", pmcid=pmcid, doi=doi, license=access.license,
        source_url=url, xml_path=xml_path, xml_sha256=digest, retrieved_at=now,
        checked_at=now, detail=None, tool_version=TOOL_VERSION,
    )


def append_result(path: pathlib.Path, result: FullTextResult) -> None:
    """Append one result and flush it to disk before returning (as screen_schema)."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result.model_dump(), sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def read_log(path: pathlib.Path) -> list[FullTextResult]:
    """Read a retrieval log. A missing file is an empty log, not an error."""
    path = pathlib.Path(path)
    if not path.exists():
        return []
    return [
        FullTextResult(**json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def retrieve(
    pmids: list[str],
    out_dir: pathlib.Path,
    log_path: pathlib.Path,
    batch_size: int = IDCONV_BATCH_SIZE,
    retry_failed: bool = False,
) -> dict[str, int]:
    """Retrieve full texts for `pmids`, logging one result per PMID.

    PMIDs already in the log are skipped. With `retry_failed`, a PMID whose
    latest logged status is `fetch_failed` is attempted again and the new
    result appended; nothing earlier in the log is rewritten.
    """
    out_dir = pathlib.Path(out_dir)
    log_path = pathlib.Path(log_path)
    unique = list(dict.fromkeys(pmids))

    latest = {r.pmid: r for r in read_log(log_path)}
    todo = [
        p for p in unique
        if p not in latest or (retry_failed and latest[p].status == "fetch_failed")
    ]

    counts = {"requested": len(unique), "skipped": len(unique) - len(todo)}
    counts.update({status: 0 for status in STATUSES})

    for start in range(0, len(todo), batch_size):
        batch = todo[start : start + batch_size]
        try:
            resolved = resolve_ids(batch, batch_size=batch_size)
            batch_error: Optional[str] = None
        except FullTextError as exc:
            resolved, batch_error = {}, str(exc)

        for pmid in batch:
            result = _retrieve_one(pmid, resolved.get(pmid), batch_error, out_dir)
            append_result(log_path, result)
            counts[result.status] += 1

    return counts


def load_pmids(path: pathlib.Path) -> list[str]:
    """One PMID per line. Blank lines and repeats are dropped; anything else
    that is not a bare PMID is refused rather than skipped."""
    pmids: list[str] = []
    lines = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, start=1):
        value = line.strip()
        if not value:
            continue
        if not re.fullmatch(r"\d+", value):
            raise ValueError(f"{path} line {number}: {value!r} is not a PMID")
        pmids.append(value)
    return list(dict.fromkeys(pmids))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve open-access JATS full texts for a list of PMIDs"
    )
    parser.add_argument("--pmids", type=pathlib.Path, required=True)
    parser.add_argument("--out-dir", type=pathlib.Path, required=True)
    parser.add_argument("--log", type=pathlib.Path, required=True)
    parser.add_argument("--batch-size", type=int, default=IDCONV_BATCH_SIZE)
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Re-attempt PMIDs whose latest logged status is fetch_failed.",
    )
    args = parser.parse_args()

    counts = retrieve(
        load_pmids(args.pmids), args.out_dir, args.log,
        batch_size=args.batch_size, retry_failed=args.retry_failed,
    )
    for key, value in counts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
