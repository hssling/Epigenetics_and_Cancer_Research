"""Data models enforcing the no-default contract (spec section 8.3).

Pydantic v2 treats `Optional[X]` WITHOUT a default as a required field that
accepts None. That is deliberate and load-bearing: a caller must state that
a value is absent rather than forgetting it. Do not add `= None` defaults.
"""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Written out literally rather than derived from config.SOURCE_DBS: passing a
# tuple to Literal[...] happens to flatten at runtime but is not valid typing,
# and Pydantic's schema builder should not depend on that behaviour. The test
# `test_source_db_literal_matches_config` keeps the two in sync.
SourceDB = Literal[
    "pubmed", "embase", "wos", "central", "ctgov", "ictrp", "europepmc"
]


class QuantitativeValue(BaseModel):
    """A number extracted from a paper.

    Cannot be constructed without a source location, so spec section 8.4's
    provenance rule is enforced by the type rather than by a later check.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: float
    source_location: str = Field(min_length=1)

    @model_validator(mode="after")
    def _source_location_not_blank(self) -> "QuantitativeValue":
        if not self.source_location.strip():
            raise ValueError("source_location cannot be blank or whitespace")
        return self


class SearchRecord(BaseModel):
    """One bibliographic record as retrieved, before deduplication."""

    model_config = ConfigDict(extra="forbid")

    source_db: SourceDB
    source_id: str
    doi: Optional[str]
    pmid: Optional[str]
    title: str
    abstract: Optional[str]
    year: Optional[int]
    journal: Optional[str]
    authors: list[str]
    retrieved_at: str
    query_hash: str


class RegistryRecord(BaseModel):
    """One trial registration, as retrieved from a study registry.

    Deliberately NOT a `SearchRecord`. A registration is not a publication: it
    has no journal, no author list, and no abstract, and treating it as a
    bibliographic record would let a registered-but-never-published trial be
    counted as evidence. Protocol Section 4.1 gives registry records a distinct
    purpose -- identifying unpublished and ongoing studies, and populating a
    "registered but unreported" overlay showing where evidence is in flight --
    and they travel in their own PRISMA stream.

    The `_is_actual` flags carry the distinction the overlay turns on. A
    registration posted with an ESTIMATED completion date of 2019 says nothing
    about whether the trial finished; only an ACTUAL date does. Collapsing the
    two would manufacture "overdue" trials out of abandoned projections, so
    the flag is required rather than inferred, and stays None when the registry
    does not say which kind of date it holds.
    """

    model_config = ConfigDict(extra="forbid")

    source_db: SourceDB
    source_id: str
    title: str
    summary: Optional[str]
    status: Optional[str]
    study_type: Optional[str]
    phases: list[str]
    conditions: list[str]
    interventions: list[str]
    enrollment: Optional[int]
    enrollment_is_actual: Optional[bool]
    start_date: Optional[str]
    primary_completion_date: Optional[str]
    completion_date: Optional[str]
    completion_is_actual: Optional[bool]
    sponsor: Optional[str]
    # Results posted in the registry itself, which is a legal obligation in
    # several jurisdictions and distinct from publication in a journal.
    has_results: bool
    # PMIDs the registry itself links as reporting this trial's results.
    result_pmids: list[str]
    retrieved_at: str
    query_hash: str


class DedupedRecord(SearchRecord):
    """A record surviving deduplication, carrying its merge history."""

    model_config = ConfigDict(extra="forbid")

    record_id: str
    merged_from: list[str]
    dedup_rule: Literal["unique", "doi", "pmid", "fuzzy_title"]
