# EGM Foundation & Corpus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible, provenance-tracked search-and-deduplication pipeline that produces the screened-ready corpus for an evidence gap map, guarded by a data-integrity test suite that makes the previous pipeline's failure modes impossible.

**Architecture:** A Python package (`egm/pipeline/`) writes immutable, timestamped artefacts into sibling data directories (`egm/search/`, `egm/screening/`, ...). Every record is a Pydantic model with no default values, so absent data must be stated explicitly rather than silently filled. Quantitative values are a dedicated type that cannot be constructed without a source location. A test suite enforces four integrity rules and includes a regression fixture built from the *actual fabricated dataset* in this repository, proving the detector catches the specific failure that occurred.

**Tech Stack:** Python 3.11+, Pydantic v2 (schema + fail-loud validation), pandas (tabular ops), requests (NCBI E-utilities), PyYAML (workflow assertions), pytest + pytest-mock, rapidfuzz (fuzzy dedup).

**Spec:** [docs/superpowers/specs/2026-09-13-epigenetics-evidence-gap-map-design.md](../specs/2026-09-13-epigenetics-evidence-gap-map-design.md)

## Global Constraints

Every task's requirements implicitly include this section. Values are copied verbatim from the spec.

- **Python 3.11+.** Pydantic **v2** specifically — v1 treats `Optional[X]` as implicitly defaulting to `None`, which defeats the core integrity mechanism. Pin `pydantic>=2.6,<3`.
- **No default values anywhere in the data path.** Missing data stays `None` and must be passed explicitly. A function substituting a constant for absent data is a defect. *(Spec §8.3 rule 1)*
- **Fail loud.** A missing required field raises; it is never silently filled. *(Spec §8.3 rule 2)*
- **No RNG in the data path.** `random` / `numpy.random` may be imported only in `egm/pipeline/sampling.py`. *(Spec §8.3 rule 3)*
- **Single source of truth.** Every number destined for the manuscript is injected from the coded dataset at build time. No hand-typed statistics. *(Spec §8.3 rule 4)*
- **Date window:** 2015-01-01 to 2026-12-31. *(Spec §4.1)*
- **Eligible markers:** DNA methylation, histone modification, chromatin state, epigenetic clock / DNAm age. **ncRNA excluded as a sole marker.** *(Spec §4.4)*
- **Raw exports are append-only.** Never mutate a file under `egm/search/raw/`. Corrections are new timestamped artefacts.
- **Every artefact carries a run manifest** with UTC timestamp, query hash, tool version, and record count. *(Spec §5.3)*
- **Commit after every task.** Conventional Commits format. Attribution line: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

---

## File Structure

Code and data artefacts are kept in sibling trees so that no module name collides with an output directory.

| Path | Responsibility |
|---|---|
| `egm/pyproject.toml` | Package metadata, pinned dependencies, pytest config |
| `egm/pipeline/config.py` | Constants: date window, concept blocks, source databases. No logic |
| `egm/pipeline/schema.py` | Pydantic models. `QuantitativeValue`, `SearchRecord`, `DedupedRecord`. The no-default contract lives here |
| `egm/pipeline/provenance.py` | `RunManifest` — timestamp, query hash, counts, tool version |
| `egm/pipeline/integrity.py` | Reusable integrity checks (`modal_share`, placeholder saturation) callable from both tests and the pipeline |
| `egm/pipeline/query.py` | Composes query strings from concept blocks. Pure functions, no I/O |
| `egm/pipeline/pubmed.py` | NCBI E-utilities client: count, search, fetch. Retry + rate limiting |
| `egm/pipeline/dedup.py` | DOI → PMID → fuzzy title+year+author deduplication |
| `egm/pipeline/prisma.py` | PRISMA counter with reconciliation assertions |
| `egm/pipeline/sampling.py` | **The only module permitted to import `random`.** Validation-sample selection |
| `egm/tests/` | Test suite mirroring the module layout |
| `egm/protocol/` | Protocol document and amendments log (artefacts) |
| `egm/search/raw/` | Append-only raw exports (artefacts) |
| `egm/search/` | Query strings, dedup log, PRISMA counts (artefacts) |
| `DEPRECATED.md` | Root-level notice covering superseded pipelines |

---

## Task 1: Remediate the superseded pipelines

Spec §9.4. This is first because the GitHub Action currently regenerates and commits fabricated outputs on a weekly cron, and that must stop before any new work is published from this repository.

**Files:**
- Create: `DEPRECATED.md`
- Modify: `.github/workflows/python-living-review.yml`
- Modify: `README.md:1-3`
- Modify: `re_research_2025/AUTHORS:10-13`
- Create: `egm/tests/test_remediation.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: a repository state where no scheduled job writes research artefacts; `egm/tests/test_remediation.py` guards it

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_remediation.py`:

```python
"""Guards the remediation of the superseded pipelines (spec section 9.4)."""
import pathlib
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "python-living-review.yml"


def test_deprecated_notice_exists_and_is_specific():
    notice = REPO / "DEPRECATED.md"
    assert notice.exists(), "DEPRECATED.md must exist at repository root"
    text = notice.read_text(encoding="utf-8")
    # The notice must name the concrete defects, not merely say "outdated".
    for required in ["random.random", "0.3", "200", "prisma_counts.csv", "not research findings"]:
        assert required in text, f"DEPRECATED.md must mention {required!r}"


def test_living_review_workflow_has_no_schedule_trigger():
    assert WORKFLOW.exists(), "workflow file should be retained, not deleted"
    spec = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    # PyYAML parses the bare key `on:` as boolean True.
    triggers = spec.get("on", spec.get(True, {})) or {}
    assert "schedule" not in triggers, (
        "scheduled trigger must be removed: it regenerates fabricated outputs weekly"
    )


def test_authors_file_lists_no_ai_author():
    authors = (REPO / "re_research_2025" / "AUTHORS").read_text(encoding="utf-8")
    for banned in ["Automation Agent", "DeepMind"]:
        assert banned not in authors, f"AI systems are not authors (found {banned!r})"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_remediation.py -v`
Expected: FAIL — `DEPRECATED.md must exist at repository root`

- [ ] **Step 3: Create the deprecation notice**

Create `DEPRECATED.md` at the repository root:

```markdown
# DEPRECATED — superseded research pipelines

The pipelines and outputs described below are **retained for transparency only**.
The values they report are pipeline artefacts and **are not research findings**.
They were never submitted, published, shared, or cited.

Active work lives in `egm/`. See
`docs/superpowers/specs/2026-09-13-epigenetics-evidence-gap-map-design.md`.

## 1. Root pipeline — `scripts/`, `output/`, `data/`

`output/Epigenetics_PublicHealth_Manuscript.md` must not be cited or reused.

| Reported value | Actual origin |
|---|---|
| "Mean positive detection 48.9%" | Mean of `random.random()` (`scripts/fetch_pubmed_data.py:268`) |
| "SEPT9 mean positivity 66.0%" (n=1) | A single `random.random()` draw |
| `sensitivity`, `specificity` columns | `random.uniform(0.5, 0.95)` (`scripts/fetch_pubmed_data.py:270-271`) |
| Exposure effect sizes and ranking | 424 of 616 (69%) are the constant `0.3` (`scripts/prepare_master_dataset.py:83`) |
| "Median sample size 200" | 468 of 616 (76%) are the constant `200` (`scripts/prepare_master_dataset.py:88`) |
| 95% confidence intervals | Computed as `effect x 0.8` to `effect x 1.2` — arithmetic, no variance input |

`data/prisma_counts.csv` records 616 identified, **0 excluded**, 616 included.
No screening was performed; the PRISMA diagram depicts a process that did not occur.

The placeholder constants were introduced so that downstream R scripts would not
fail on missing data. That converted "unmeasured" into "measured as 0.3".

## 2. `re_research_2025/`

The underlying data are real and arithmetically consistent, but the module is
described as a systematic review when it is an **unscreened bibliometric
snapshot**: the PubMed query returned exactly 29 records against a `retmax` of
100, and all 29 were analysed. No screening, dual review, or exclusion occurred.

Its first-match keyword classifier misclassifies: an exposome/environmental
paper and a prostate gene-expression paper are both coded `Nutritional` because
the nutrition keyword block is evaluated first. The headline "48.3% nutritional"
is partly an artefact of that keyword ordering.

## 3. Scheduled automation

The weekly `schedule:` trigger on `.github/workflows/python-living-review.yml`
has been removed. It regenerated and committed these artefacts every Monday.
The workflow is retained, manual-dispatch only, for historical reference.
```

- [ ] **Step 4: Disable the scheduled trigger**

In `.github/workflows/python-living-review.yml`, remove the `schedule:` block so only manual dispatch remains:

```yaml
name: Living Review Pipeline (Python 2025) [DEPRECATED]

# DEPRECATED: see /DEPRECATED.md.
# The weekly schedule was removed — it regenerated fabricated outputs.
# Retained for historical reference; manual dispatch only.
on:
  workflow_dispatch:
```

- [ ] **Step 5: Update the README banner and the AUTHORS file**

Insert immediately after line 1 of `README.md`:

```markdown
> ## ⚠️ This pipeline is deprecated
> The manuscript and datasets in `output/` and `data/` contain placeholder
> constants and randomly generated values. They are **not research findings**.
> See [DEPRECATED.md](DEPRECATED.md). Active work is in `egm/`.
```

Remove the badge line (`README.md:2`) pointing at the now-unscheduled workflow.

In `re_research_2025/AUTHORS`, delete the `**Epigenetics Research Automation Agent** (Google DeepMind)` bullet from the Research Team block. AI systems are not authors (spec §9.3).

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_remediation.py -v`
Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
git add DEPRECATED.md README.md .github/workflows/python-living-review.yml re_research_2025/AUTHORS egm/tests/test_remediation.py
git commit -m "chore: deprecate superseded pipelines and disable fabricating cron

The weekly scheduled workflow regenerated and committed outputs whose
reported values came from random.random() and hardcoded constants.
Schedule removed; workflow retained manual-dispatch only.

DEPRECATED.md documents each defect with its source line. Guarded by
egm/tests/test_remediation.py so the schedule cannot silently return.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: Package scaffold and the no-default schema

The integrity contract lives in the type system. In Pydantic v2, `Optional[str]` **without** a default is a *required* field that accepts `None` — the caller must state absence explicitly. Do not add `= None` to any field; that silently restores the failure mode this schema exists to prevent.

**Files:**
- Create: `egm/pyproject.toml`
- Create: `egm/pipeline/__init__.py`
- Create: `egm/pipeline/config.py`
- Create: `egm/pipeline/schema.py`
- Create: `egm/tests/__init__.py`
- Test: `egm/tests/test_schema.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `QuantitativeValue(value: float, source_location: str)` — frozen
  - `SearchRecord(source_db, source_id, doi, pmid, title, abstract, year, journal, authors, retrieved_at, query_hash)`
  - `config.DATE_START: str`, `config.DATE_END: str`, `config.SOURCE_DBS: tuple[str, ...]`

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_schema.py`:

```python
"""The no-default contract (spec section 8.3 rules 1 and 2)."""
import pytest
from pydantic import ValidationError

from pipeline.schema import QuantitativeValue, SearchRecord


def _valid_record_kwargs():
    return dict(
        source_db="pubmed", source_id="12345678", doi="10.1000/x", pmid="12345678",
        title="A study", abstract="Text.", year=2020, journal="J Epi",
        authors=["Smith J"], retrieved_at="2026-09-13T10:00:00Z", query_hash="ab12cd34",
    )


def test_quantitative_value_requires_source_location():
    with pytest.raises(ValidationError):
        QuantitativeValue(value=0.42)


def test_quantitative_value_rejects_blank_source_location():
    with pytest.raises(ValidationError):
        QuantitativeValue(value=0.42, source_location="   ")


def test_quantitative_value_is_frozen():
    qv = QuantitativeValue(value=0.42, source_location="Table 2, row 3")
    with pytest.raises(ValidationError):
        qv.value = 0.99


def test_omitting_an_optional_field_raises_rather_than_defaulting():
    """The crux: absence must be stated, never assumed."""
    kwargs = _valid_record_kwargs()
    del kwargs["doi"]
    with pytest.raises(ValidationError) as exc:
        SearchRecord(**kwargs)
    assert "doi" in str(exc.value)


def test_explicit_none_is_accepted():
    kwargs = _valid_record_kwargs()
    kwargs["doi"] = None
    assert SearchRecord(**kwargs).doi is None


def test_unknown_field_is_rejected():
    kwargs = _valid_record_kwargs()
    kwargs["epigenetic_effect_size"] = 0.3
    with pytest.raises(ValidationError):
        SearchRecord(**kwargs)


def test_unknown_source_db_is_rejected():
    kwargs = _valid_record_kwargs()
    kwargs["source_db"] = "google_scholar"
    with pytest.raises(ValidationError):
        SearchRecord(**kwargs)


def test_source_db_literal_matches_config():
    """SourceDB is spelled out literally; this keeps it in sync with config."""
    from typing import get_args

    from pipeline.config import SOURCE_DBS
    from pipeline.schema import SourceDB

    assert get_args(SourceDB) == tuple(SOURCE_DBS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline'`

- [ ] **Step 3: Create the package scaffold**

Create `egm/pyproject.toml`:

```toml
[project]
name = "egm-pipeline"
version = "0.1.0"
description = "Evidence gap map pipeline: epigenetic approaches in health practice"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.6,<3",
    "pandas>=2.2",
    "requests>=2.31",
    "PyYAML>=6.0",
    "rapidfuzz>=3.6",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-mock>=3.12"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]

[tool.setuptools.packages.find]
include = ["pipeline*"]
```

Create empty `egm/pipeline/__init__.py` and `egm/tests/__init__.py`.

Create `egm/pipeline/config.py`:

```python
"""Project constants. No logic lives here (spec sections 4.1, 4.4, 4.5)."""

DATE_START = "2015/01/01"
DATE_END = "2026/12/31"

SOURCE_DBS = ("pubmed", "embase", "wos", "central", "ctgov", "ictrp")

# Eligible epigenetic markers. ncRNA is deliberately excluded as a sole
# marker (spec section 4.4): it nearly doubles the corpus (11,965 -> 21,528)
# for low expected yield, and is definitionally contested.
ELIGIBLE_MARKERS = ("methylation", "histone", "chromatin", "clock")

NCBI_TOOL_NAME = "egm-pipeline"
NCBI_RATE_LIMIT_SECONDS = 0.34  # ~3 requests/sec without an API key
```

- [ ] **Step 4: Write the schema**

Create `egm/pipeline/schema.py`:

```python
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
SourceDB = Literal["pubmed", "embase", "wos", "central", "ctgov", "ictrp"]


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


class DedupedRecord(SearchRecord):
    """A record surviving deduplication, carrying its merge history."""

    model_config = ConfigDict(extra="forbid")

    record_id: str
    merged_from: list[str]
    dedup_rule: Literal["unique", "doi", "pmid", "fuzzy_title"]
```

- [ ] **Step 5: Install and run tests to verify they pass**

Run:
```bash
cd egm && python -m pip install -e ".[dev]" && python -m pytest tests/ -v
```
Expected: 11 passed (3 from Task 1 + 8 here)

- [ ] **Step 6: Commit**

```bash
git add egm/pyproject.toml egm/pipeline/ egm/tests/
git commit -m "feat: add package scaffold and no-default schema

Pydantic v2 Optional fields without defaults are required, so absent
data must be passed explicitly as None rather than silently omitted.
QuantitativeValue cannot be constructed without a source_location.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: Integrity harness with a real fabricated-data fixture

The placeholder detector is tested against **the actual fabricated dataset in this repository**, where `0.3` occupies 69% of one column and `200` occupies 76% of another. A detector that cannot catch the failure that already happened is not worth having.

**Files:**
- Create: `egm/pipeline/integrity.py`
- Create: `egm/pipeline/sampling.py`
- Test: `egm/tests/test_integrity.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `modal_share(values: Iterable) -> float`
  - `find_placeholder_saturation(df: pd.DataFrame, threshold: float = 0.20) -> dict[str, tuple[object, float]]`
  - `assert_no_placeholder_saturation(df, threshold=0.20) -> None` — raises `IntegrityError`
  - `IntegrityError(Exception)`
  - `sampling.stratified_sample(...)` — the only RNG consumer

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_integrity.py`:

```python
"""Integrity rules (spec sections 8.3, 8.4)."""
import ast
import pathlib

import pandas as pd
import pytest

from pipeline.integrity import (
    IntegrityError,
    assert_no_placeholder_saturation,
    find_placeholder_saturation,
    modal_share,
)

REPO = pathlib.Path(__file__).resolve().parents[2]
PIPELINE = REPO / "egm" / "pipeline"
RNG_ALLOWED = {"sampling.py"}


def test_modal_share_of_uniform_column_is_one():
    assert modal_share([0.3] * 10) == pytest.approx(1.0)


def test_modal_share_ignores_none():
    assert modal_share([1.0, 2.0, None, None]) == pytest.approx(0.5)


def test_modal_share_of_empty_is_zero():
    assert modal_share([]) == 0.0
    assert modal_share([None, None]) == 0.0


def test_clean_column_passes():
    df = pd.DataFrame({"effect": [0.1, 0.2, 0.3, 0.4, 0.5]})
    assert find_placeholder_saturation(df) == {}


def test_saturated_column_is_flagged_with_value_and_share():
    df = pd.DataFrame({"effect": [0.3] * 7 + [0.1, 0.2, 0.4]})
    found = find_placeholder_saturation(df, threshold=0.20)
    assert "effect" in found
    value, share = found["effect"]
    assert value == 0.3
    assert share == pytest.approx(0.7)


def test_assert_raises_on_saturation():
    df = pd.DataFrame({"effect": [0.3] * 7 + [0.1, 0.2, 0.4]})
    with pytest.raises(IntegrityError, match="effect"):
        assert_no_placeholder_saturation(df)


def test_detector_catches_the_actual_fabricated_dataset():
    """Regression fixture: the real failure this repository already had.

    data/epigenetic_master_dataset.csv has epigenetic_effect_size == 0.3 in
    69% of rows and population_size == 200 in 76%. If the detector cannot
    catch this, it is useless.
    """
    fabricated = REPO / "data" / "epigenetic_master_dataset.csv"
    if not fabricated.exists():
        pytest.skip("superseded dataset not present")

    df = pd.read_csv(fabricated)[["epigenetic_effect_size", "population_size"]]
    found = find_placeholder_saturation(df, threshold=0.20)

    assert "epigenetic_effect_size" in found
    assert found["epigenetic_effect_size"][0] == pytest.approx(0.3)
    assert found["epigenetic_effect_size"][1] > 0.65

    assert "population_size" in found
    assert found["population_size"][0] == 200
    assert found["population_size"][1] > 0.70


def test_no_rng_imported_in_data_path():
    """Spec section 8.3 rule 3. Only sampling.py may import random."""
    offenders: list[str] = []
    for path in PIPELINE.rglob("*.py"):
        if path.name in RNG_ALLOWED:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root == "random" or alias.name.startswith("numpy.random"):
                        offenders.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] == "random" or "numpy.random" in node.module:
                    offenders.append(f"{path.name}: from {node.module} import ...")
    assert offenders == [], f"RNG must not appear in the data path: {offenders}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_integrity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.integrity'`

- [ ] **Step 3: Write the implementation**

Create `egm/pipeline/integrity.py`:

```python
"""Integrity checks against the failure modes of the superseded pipeline.

See DEPRECATED.md. The detector here is validated in tests against that
dataset directly.
"""
from collections import Counter
from typing import Iterable

import pandas as pd


class IntegrityError(Exception):
    """Raised when data violates an integrity rule. Never caught internally."""


def modal_share(values: Iterable) -> float:
    """Fraction of non-null values occupied by the single most common value."""
    present = [v for v in values if v is not None and not pd.isna(v)]
    if not present:
        return 0.0
    _, count = Counter(present).most_common(1)[0]
    return count / len(present)


def find_placeholder_saturation(
    df: pd.DataFrame, threshold: float = 0.20
) -> dict[str, tuple[object, float]]:
    """Return numeric columns whose modal value exceeds `threshold` share.

    A legitimately measured quantity rarely repeats one exact value in more
    than a fifth of rows; a substituted constant always does.
    """
    flagged: dict[str, tuple[object, float]] = {}
    for column in df.select_dtypes(include="number").columns:
        series = df[column].dropna()
        if series.empty:
            continue
        share = modal_share(series.tolist())
        if share > threshold:
            flagged[column] = (series.mode().iloc[0], share)
    return flagged


def assert_no_placeholder_saturation(df: pd.DataFrame, threshold: float = 0.20) -> None:
    """Raise IntegrityError if any numeric column looks constant-filled."""
    flagged = find_placeholder_saturation(df, threshold)
    if flagged:
        detail = "; ".join(
            f"{col}={value!r} in {share:.0%} of rows" for col, (value, share) in flagged.items()
        )
        raise IntegrityError(f"Placeholder saturation detected: {detail}")
```

Create `egm/pipeline/sampling.py`:

```python
"""Validation-sample selection.

The ONLY module permitted to import `random` (spec section 8.3 rule 3).
Sampling is a methodological procedure, not a data-production step: it
selects which records a human re-screens. It never produces a value that
appears in results.
"""
import random
from typing import Sequence, TypeVar

T = TypeVar("T")


def stratified_sample(
    items: Sequence[T], strata: Sequence[str], per_stratum: dict[str, int], seed: int
) -> list[T]:
    """Draw a reproducible stratified sample.

    `seed` is mandatory: the validation sample must be reproducible from the
    published protocol.
    """
    if len(items) != len(strata):
        raise ValueError(f"items ({len(items)}) and strata ({len(strata)}) must align")

    rng = random.Random(seed)
    buckets: dict[str, list[T]] = {}
    for item, stratum in zip(items, strata):
        buckets.setdefault(stratum, []).append(item)

    selected: list[T] = []
    for stratum, wanted in sorted(per_stratum.items()):
        available = buckets.get(stratum, [])
        if wanted > len(available):
            raise ValueError(
                f"stratum {stratum!r}: requested {wanted}, only {len(available)} available"
            )
        selected.extend(rng.sample(available, wanted))
    return selected
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_integrity.py -v`
Expected: 8 passed — including `test_detector_catches_the_actual_fabricated_dataset`

- [ ] **Step 5: Commit**

```bash
git add egm/pipeline/integrity.py egm/pipeline/sampling.py egm/tests/test_integrity.py
git commit -m "feat: add integrity harness validated on the fabricated dataset

find_placeholder_saturation flags numeric columns whose modal value
exceeds 20% of rows. Regression-tested against the superseded dataset,
where 0.3 occupies 69% of one column and 200 occupies 76% of another.

AST scan asserts random/numpy.random appear nowhere in the data path
except sampling.py, which selects validation samples only.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: Provenance manifests

Spec §5.3: every artefact records the query, timestamp, tool version and count that produced it.

**Files:**
- Create: `egm/pipeline/provenance.py`
- Test: `egm/tests/test_provenance.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `RunManifest(tool_version, run_at, query_string, query_hash, source_db, record_count, notes)`
  - `RunManifest.create(query_string, source_db, record_count, notes) -> RunManifest`
  - `query_hash(query_string: str) -> str` — 12-char SHA-256 prefix
  - `write_artefact(path, records, manifest) -> None`

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_provenance.py`:

```python
import json

import pytest
from pydantic import ValidationError

from pipeline.provenance import RunManifest, query_hash, write_artefact


def test_query_hash_is_stable_and_short():
    assert query_hash("epigenetics AND cancer") == query_hash("epigenetics AND cancer")
    assert len(query_hash("x")) == 12


def test_query_hash_differs_for_different_queries():
    assert query_hash("a AND b") != query_hash("a OR b")


def test_manifest_records_the_hash_of_its_query():
    m = RunManifest.create(query_string="q1", source_db="pubmed", record_count=5, notes=None)
    assert m.query_hash == query_hash("q1")
    assert m.run_at.endswith("Z")


def test_manifest_rejects_negative_count():
    with pytest.raises(ValidationError):
        RunManifest.create(query_string="q", source_db="pubmed", record_count=-1, notes=None)


def test_manifest_requires_explicit_notes():
    with pytest.raises(TypeError):
        RunManifest.create(query_string="q", source_db="pubmed", record_count=1)


def test_write_artefact_refuses_count_mismatch(tmp_path):
    m = RunManifest.create(query_string="q", source_db="pubmed", record_count=2, notes=None)
    with pytest.raises(ValueError, match="record_count"):
        write_artefact(tmp_path / "out.json", [{"a": 1}], m)


def test_write_artefact_round_trips(tmp_path):
    m = RunManifest.create(query_string="q", source_db="pubmed", record_count=1, notes=None)
    out = tmp_path / "out.json"
    write_artefact(out, [{"a": 1}], m)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["manifest"]["query_hash"] == query_hash("q")
    assert payload["records"] == [{"a": 1}]


def test_write_artefact_refuses_to_overwrite(tmp_path):
    """Raw exports are append-only (global constraint)."""
    m = RunManifest.create(query_string="q", source_db="pubmed", record_count=1, notes=None)
    out = tmp_path / "out.json"
    write_artefact(out, [{"a": 1}], m)
    with pytest.raises(FileExistsError):
        write_artefact(out, [{"a": 2}], m)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_provenance.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.provenance'`

- [ ] **Step 3: Write the implementation**

Create `egm/pipeline/provenance.py`:

```python
"""Run manifests binding every artefact to the query that produced it."""
import hashlib
import json
import pathlib
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

TOOL_VERSION = "0.1.0"


def query_hash(query_string: str) -> str:
    """Stable 12-character identifier for a query string."""
    return hashlib.sha256(query_string.encode("utf-8")).hexdigest()[:12]


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_version: str
    run_at: str
    query_string: str
    query_hash: str
    source_db: str
    record_count: int = Field(ge=0)
    notes: Optional[str]

    @classmethod
    def create(
        cls, query_string: str, source_db: str, record_count: int, notes: Optional[str]
    ) -> "RunManifest":
        """`notes` is positional-required so absence is stated, not defaulted."""
        return cls(
            tool_version=TOOL_VERSION,
            run_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            query_string=query_string,
            query_hash=query_hash(query_string),
            source_db=source_db,
            record_count=record_count,
            notes=notes,
        )


def write_artefact(
    path: pathlib.Path, records: list[dict[str, Any]], manifest: RunManifest
) -> None:
    """Write records plus manifest. Refuses overwrite; verifies the count."""
    if len(records) != manifest.record_count:
        raise ValueError(
            f"manifest.record_count={manifest.record_count} but got {len(records)} records"
        )
    path = pathlib.Path(path)
    if path.exists():
        raise FileExistsError(f"{path} exists; raw artefacts are append-only")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"manifest": manifest.model_dump(), "records": records}, indent=2),
        encoding="utf-8",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_provenance.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add egm/pipeline/provenance.py egm/tests/test_provenance.py
git commit -m "feat: add run manifests binding artefacts to their queries

Every artefact carries tool version, UTC timestamp, query hash and
record count. write_artefact refuses overwrite (raw exports are
append-only) and verifies the count matches the manifest.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: Query builder

Pure functions composing the concept blocks validated in spec §5.2. Reproduces the measured counts exactly.

**Files:**
- Create: `egm/pipeline/query.py`
- Test: `egm/tests/test_query.py`

**Interfaces:**
- Consumes: `config.DATE_START`, `config.DATE_END`
- Produces:
  - `METHYLATION, HISTONE, CLOCK, NCRNA, EXPOSURE, CLINICAL_USE, HUMAN, DESIGN, NOT_SECONDARY: str`
  - `epigenetic_core() -> str`
  - `build_pubmed_query(include_ncrna: bool, date_limited: bool) -> str`

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_query.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_query.py -v`
Expected: FAIL — `ImportError: cannot import name 'query'`

- [ ] **Step 3: Write the implementation**

Create `egm/pipeline/query.py`:

```python
"""PubMed query construction (spec section 5.2).

Counts validated against live PubMed on 2026-09-13:
  core + human + (exposure OR clinical) + design + not-secondary = 11,965
  ... restricted to 2015-2026                                    =  9,089
  ... including ncRNA                                            = 21,528
"""
from pipeline.config import DATE_END, DATE_START

METHYLATION = (
    '("DNA methylation"[MeSH] OR "DNA Methylation"[tiab] OR methylome[tiab] '
    'OR EWAS[tiab] OR "epigenome-wide"[tiab] OR "CpG"[tiab] '
    'OR "5-methylcytosine"[tiab] OR "hydroxymethylation"[tiab])'
)
HISTONE = (
    '("Histone Code"[MeSH] OR "Histones"[MeSH] OR histone*[tiab] '
    'OR "chromatin"[tiab] OR "H3K4"[tiab] OR "H3K27"[tiab] OR "HDAC"[tiab] '
    'OR "histone deacetylase"[tiab])'
)
CLOCK = (
    '("epigenetic clock"[tiab] OR "epigenetic age"[tiab] OR "DNAm age"[tiab] '
    'OR "GrimAge"[tiab] OR "PhenoAge"[tiab] OR "Horvath clock"[tiab] '
    'OR "biological age"[tiab])'
)
NCRNA = (
    '("MicroRNAs"[MeSH] OR microRNA*[tiab] OR miRNA*[tiab] '
    'OR "long non-coding RNA"[tiab] OR lncRNA*[tiab])'
)
EXPOSURE = (
    '("Diet"[MeSH] OR diet*[tiab] OR nutrition*[tiab] OR supplement*[tiab] '
    'OR "Exercise"[MeSH] OR exercise[tiab] OR "physical activity"[tiab] '
    'OR "Smoking"[MeSH] OR smoking[tiab] OR tobacco[tiab] OR alcohol[tiab] '
    'OR "Environmental Exposure"[MeSH] OR "air pollution"[tiab] '
    'OR "particulate matter"[tiab] OR pesticide*[tiab] OR "heavy metal*"[tiab] '
    'OR "Stress, Psychological"[MeSH] OR "psychosocial"[tiab] OR sleep[tiab] '
    'OR "weight loss"[tiab] OR intervention*[tiab])'
)
CLINICAL_USE = (
    '(screening[tiab] OR "early detection"[tiab] OR diagnos*[tiab] '
    'OR prognos*[tiab] OR "risk prediction"[tiab] OR "risk stratification"[tiab] '
    'OR triage[tiab] OR biomarker*[tiab] OR "treatment response"[tiab] '
    'OR monitoring[tiab])'
)
HUMAN = "(humans[MeSH])"
DESIGN = (
    '("Randomized Controlled Trial"[pt] OR "Controlled Clinical Trial"[pt] '
    'OR "Clinical Trial"[pt] OR "Cohort Studies"[MeSH] '
    'OR "Case-Control Studies"[MeSH] OR "Cross-Sectional Studies"[MeSH] '
    'OR randomi*[tiab] OR cohort[tiab] OR "case-control"[tiab] OR trial[tiab])'
)
NOT_SECONDARY = (
    'NOT (review[pt] OR "systematic review"[pt] OR meta-analysis[pt] '
    "OR editorial[pt] OR comment[pt] OR letter[pt])"
)


def epigenetic_core(include_ncrna: bool = False) -> str:
    """Eligible marker concepts. ncRNA excluded by default (spec section 4.4)."""
    blocks = [METHYLATION, HISTONE, CLOCK]
    if include_ncrna:
        blocks.append(NCRNA)
    return "(" + " OR ".join(blocks) + ")"


def build_pubmed_query(include_ncrna: bool, date_limited: bool) -> str:
    """Compose the full PubMed strategy. Both flags are explicit by design."""
    parts = [
        epigenetic_core(include_ncrna),
        "AND",
        HUMAN,
        "AND",
        f"({EXPOSURE} OR {CLINICAL_USE})",
        "AND",
        DESIGN,
        NOT_SECONDARY,
    ]
    if date_limited:
        parts.append(f"AND {DATE_START}:{DATE_END}[dp]")
    return " ".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_query.py -v`
Expected: 7 passed

- [ ] **Step 5: Verify the query reproduces the spec's measured count**

Run:
```bash
cd egm && python -c "
import urllib.parse, urllib.request, json
from pipeline.query import build_pubmed_query
q = build_pubmed_query(include_ncrna=False, date_limited=True)
p = urllib.parse.urlencode({'db':'pubmed','term':q,'retmode':'json','retmax':0,'tool':'egm-pipeline'})
with urllib.request.urlopen(f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{p}', timeout=60) as r:
    print('count:', json.loads(r.read().decode())['esearchresult']['count'])
"
```
Expected: approximately 9,089 (PubMed grows; within a few percent confirms fidelity). Record the observed count in `egm/search/count_verification.md` with the date.

- [ ] **Step 6: Commit**

```bash
git add egm/pipeline/query.py egm/tests/test_query.py egm/search/count_verification.md
git commit -m "feat: add PubMed query builder reproducing validated counts

Concept blocks compose to the strategy measured in spec section 5.2.
ncRNA excluded by default; both flags explicit at the call site.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: PubMed E-utilities client

**Files:**
- Create: `egm/pipeline/pubmed.py`
- Test: `egm/tests/test_pubmed.py`

**Interfaces:**
- Consumes: `config.NCBI_TOOL_NAME`, `config.NCBI_RATE_LIMIT_SECONDS`, `schema.SearchRecord`, `provenance.query_hash`
- Produces:
  - `count(query: str) -> int`
  - `search(query: str, retmax: int) -> list[str]`
  - `fetch_summaries(pmids: list[str], query_hash_value: str, batch_size: int = 200) -> list[SearchRecord]`
  - `PubMedError(Exception)`

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_pubmed.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_pubmed.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.pubmed'`

- [ ] **Step 3: Write the implementation**

Create `egm/pipeline/pubmed.py`:

```python
"""NCBI E-utilities client.

Absent fields become explicit None. This module never substitutes a value
for missing data (spec section 8.3 rule 1).
"""
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from pipeline.config import NCBI_RATE_LIMIT_SECONDS, NCBI_TOOL_NAME
from pipeline.schema import SearchRecord

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
MAX_ATTEMPTS = 3


class PubMedError(Exception):
    """Raised when E-utilities cannot be reached or returns an unusable body."""


def _get(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    params = {**params, "retmode": "json", "tool": NCBI_TOOL_NAME}
    last: Optional[Exception] = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001 - re-raised as PubMedError below
            last = exc
            time.sleep(NCBI_RATE_LIMIT_SECONDS * (attempt + 1) * 3)
    raise PubMedError(f"{endpoint} failed after {MAX_ATTEMPTS} attempts: {last}")


def count(query: str) -> int:
    """Number of records matching `query`, without retrieving them."""
    body = _get("esearch.fcgi", {"db": "pubmed", "term": query, "retmax": 0})
    return int(body["esearchresult"]["count"])


def search(query: str, retmax: int) -> list[str]:
    """PMIDs matching `query`, up to `retmax`."""
    body = _get("esearch.fcgi", {"db": "pubmed", "term": query, "retmax": retmax})
    return list(body["esearchresult"]["idlist"])


def _parse_year(pubdate: str) -> Optional[int]:
    """Extract a 4-digit year, or None. Never guesses."""
    match = re.search(r"\b(19|20)\d{2}\b", pubdate or "")
    return int(match.group(0)) if match else None


def _extract_doi(article: dict[str, Any]) -> Optional[str]:
    for identifier in article.get("articleids", []):
        if identifier.get("idtype") == "doi":
            value = (identifier.get("value") or "").strip()
            return value or None
    return None


def fetch_summaries(
    pmids: list[str], query_hash_value: str, batch_size: int = 200
) -> list[SearchRecord]:
    """Retrieve summaries as SearchRecords. Absent fields become None."""
    records: list[SearchRecord] = []
    for start in range(0, len(pmids), batch_size):
        batch = pmids[start : start + batch_size]
        body = _get("esummary.fcgi", {"db": "pubmed", "id": ",".join(batch)})
        result = body.get("result", {})
        retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        for pmid in batch:
            article = result.get(pmid)
            if article is None:
                continue
            journal = (article.get("fulljournalname") or "").strip()
            records.append(
                SearchRecord(
                    source_db="pubmed",
                    source_id=pmid,
                    doi=_extract_doi(article),
                    pmid=pmid,
                    title=(article.get("title") or "").strip(),
                    abstract=None,  # esummary does not carry abstracts
                    year=_parse_year(article.get("pubdate", "")),
                    journal=journal or None,
                    authors=[a.get("name", "") for a in article.get("authors", [])],
                    retrieved_at=retrieved_at,
                    query_hash=query_hash_value,
                )
            )
        time.sleep(NCBI_RATE_LIMIT_SECONDS)
    return records
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_pubmed.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add egm/pipeline/pubmed.py egm/tests/test_pubmed.py
git commit -m "feat: add E-utilities client that never substitutes missing data

Absent DOI, year, journal and abstract become explicit None. Unparseable
dates return None rather than a guessed year. Retries three times with
backoff, then raises PubMedError.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 7: Deduplication

Spec §5.3: DOI → PMID → fuzzy title+year+first-author, with counts recorded at each step.

**Files:**
- Create: `egm/pipeline/dedup.py`
- Test: `egm/tests/test_dedup.py`

**Interfaces:**
- Consumes: `schema.SearchRecord`, `schema.DedupedRecord`
- Produces:
  - `normalise_doi(doi: Optional[str]) -> Optional[str]`
  - `normalise_title(title: str) -> str`
  - `deduplicate(records: list[SearchRecord], fuzzy_threshold: int = 95) -> tuple[list[DedupedRecord], dict[str, int]]`

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_dedup.py`:

```python
from pipeline.dedup import deduplicate, normalise_doi, normalise_title
from pipeline.schema import SearchRecord


def _record(source_db, source_id, doi=None, pmid=None, title="A study", year=2020,
            authors=("Smith J",)):
    return SearchRecord(
        source_db=source_db, source_id=source_id, doi=doi, pmid=pmid, title=title,
        abstract=None, year=year, journal="J", authors=list(authors),
        retrieved_at="2026-09-13T10:00:00Z", query_hash="h" * 12,
    )


def test_normalise_doi_lowercases_and_strips_prefix():
    assert normalise_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert normalise_doi("  10.1000/ABC  ") == "10.1000/abc"


def test_normalise_doi_passes_through_none():
    assert normalise_doi(None) is None
    assert normalise_doi("   ") is None


def test_normalise_title_strips_punctuation_and_case():
    assert normalise_title("Epigenetics: A Review!") == "epigenetics a review"


def test_unique_records_all_survive():
    records = [_record("pubmed", "1", doi="10.1/a"), _record("embase", "2", doi="10.1/b")]
    kept, counts = deduplicate(records)
    assert len(kept) == 2
    assert counts["input"] == 2
    assert counts["removed_total"] == 0


def test_doi_duplicates_collapse():
    records = [
        _record("pubmed", "1", doi="10.1/a"),
        _record("embase", "2", doi="https://doi.org/10.1/A"),
    ]
    kept, counts = deduplicate(records)
    assert len(kept) == 1
    assert counts["removed_doi"] == 1
    assert kept[0].dedup_rule == "doi"
    assert sorted(kept[0].merged_from) == ["embase:2", "pubmed:1"]


def test_pmid_duplicates_collapse_when_doi_absent():
    records = [_record("pubmed", "1", pmid="999"), _record("central", "2", pmid="999")]
    kept, counts = deduplicate(records)
    assert len(kept) == 1
    assert counts["removed_pmid"] == 1


def test_fuzzy_title_duplicates_collapse():
    records = [
        _record("wos", "1", title="DNA methylation and diet in adults"),
        _record("embase", "2", title="DNA methylation and diet in adults."),
    ]
    kept, counts = deduplicate(records)
    assert len(kept) == 1
    assert counts["removed_fuzzy"] == 1


def test_same_title_different_year_kept_separate():
    records = [
        _record("wos", "1", title="Cohort study", year=2018),
        _record("embase", "2", title="Cohort study", year=2022),
    ]
    assert len(deduplicate(records)[0]) == 2


def test_counts_reconcile():
    records = [
        _record("pubmed", "1", doi="10.1/a"),
        _record("embase", "2", doi="10.1/a"),
        _record("wos", "3", doi="10.1/b"),
    ]
    kept, counts = deduplicate(records)
    assert counts["input"] - counts["removed_total"] == counts["output"] == len(kept)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_dedup.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.dedup'`

- [ ] **Step 3: Write the implementation**

Create `egm/pipeline/dedup.py`:

```python
"""Deduplication: DOI, then PMID, then fuzzy title (spec section 5.3).

Counts are returned per rule so the PRISMA diagram reports real numbers.
"""
import re
from typing import Optional

from rapidfuzz import fuzz

from pipeline.schema import DedupedRecord, SearchRecord

_DOI_PREFIX = re.compile(r"^(https?://)?(dx\.)?doi\.org/", re.IGNORECASE)
_PUNCT = re.compile(r"[^a-z0-9 ]")
_SPACES = re.compile(r"\s+")


def normalise_doi(doi: Optional[str]) -> Optional[str]:
    if doi is None:
        return None
    cleaned = _DOI_PREFIX.sub("", doi.strip()).lower().strip()
    return cleaned or None


def normalise_title(title: str) -> str:
    return _SPACES.sub(" ", _PUNCT.sub("", title.lower())).strip()


def _first_author_surname(record: SearchRecord) -> str:
    return record.authors[0].split()[0].lower() if record.authors else ""


def _key(record: SearchRecord) -> str:
    return f"{record.source_db}:{record.source_id}"


def deduplicate(
    records: list[SearchRecord], fuzzy_threshold: int = 95
) -> tuple[list[DedupedRecord], dict[str, int]]:
    """Collapse duplicates, returning survivors and per-rule counts."""
    counts = {
        "input": len(records), "removed_doi": 0, "removed_pmid": 0,
        "removed_fuzzy": 0, "removed_total": 0, "output": 0,
    }

    by_doi: dict[str, int] = {}
    by_pmid: dict[str, int] = {}
    survivors: list[dict] = []

    for record in records:
        doi = normalise_doi(record.doi)
        pmid = (record.pmid or "").strip() or None
        index: Optional[int] = None
        rule = "unique"

        if doi is not None and doi in by_doi:
            index, rule = by_doi[doi], "doi"
            counts["removed_doi"] += 1
        elif pmid is not None and pmid in by_pmid:
            index, rule = by_pmid[pmid], "pmid"
            counts["removed_pmid"] += 1
        else:
            norm_title = normalise_title(record.title)
            surname = _first_author_surname(record)
            for position, existing in enumerate(survivors):
                if existing["year"] != record.year or existing["surname"] != surname:
                    continue
                if fuzz.ratio(existing["norm_title"], norm_title) >= fuzzy_threshold:
                    index, rule = position, "fuzzy_title"
                    counts["removed_fuzzy"] += 1
                    break

        if index is not None:
            survivors[index]["merged_from"].append(_key(record))
            if survivors[index]["rule"] == "unique":
                survivors[index]["rule"] = rule
            continue

        survivors.append({
            "record": record,
            "merged_from": [_key(record)],
            "rule": "unique",
            "norm_title": normalise_title(record.title),
            "surname": _first_author_surname(record),
            "year": record.year,
        })
        position = len(survivors) - 1
        if doi is not None:
            by_doi[doi] = position
        if pmid is not None:
            by_pmid[pmid] = position

    deduped = [
        DedupedRecord(
            **entry["record"].model_dump(),
            record_id=f"egm-{n:06d}",
            merged_from=sorted(entry["merged_from"]),
            dedup_rule=entry["rule"],
        )
        for n, entry in enumerate(survivors, start=1)
    ]

    counts["removed_total"] = counts["removed_doi"] + counts["removed_pmid"] + counts["removed_fuzzy"]
    counts["output"] = len(deduped)
    return deduped, counts
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_dedup.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add egm/pipeline/dedup.py egm/tests/test_dedup.py
git commit -m "feat: add three-stage deduplication with per-rule counts

DOI, then PMID, then fuzzy title matched within the same year and first
author. Returns counts per rule so PRISMA reports measured numbers.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 8: PRISMA counter with reconciliation

The superseded pipeline's `data/prisma_counts.csv` recorded 616 identified, 0 excluded, 616 included. This module makes that state unrepresentable.

**Files:**
- Create: `egm/pipeline/prisma.py`
- Test: `egm/tests/test_prisma.py`

**Interfaces:**
- Consumes: `integrity.IntegrityError`
- Produces:
  - `PrismaStage(name, identified, excluded, reason)`
  - `PrismaFlow(stages: list[PrismaStage])` with `.included_after(name)`, `.validate()`, `.to_csv(path)`

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_prisma.py`:

```python
import pytest

from pipeline.integrity import IntegrityError
from pipeline.prisma import PrismaFlow, PrismaStage


def test_included_is_identified_minus_excluded():
    flow = PrismaFlow(stages=[
        PrismaStage(name="identification", identified=14000, excluded=2000,
                    reason="duplicates removed"),
    ])
    assert flow.included_after("identification") == 12000


def test_validate_accepts_a_real_flow():
    flow = PrismaFlow(stages=[
        PrismaStage(name="identification", identified=14000, excluded=2000, reason="duplicates"),
        PrismaStage(name="screening", identified=12000, excluded=10500, reason="ineligible"),
        PrismaStage(name="full_text", identified=1500, excluded=400, reason="no measured marker"),
    ])
    flow.validate()


def test_zero_exclusions_across_the_whole_flow_is_rejected():
    """The exact shape of the superseded pipeline's PRISMA file."""
    flow = PrismaFlow(stages=[
        PrismaStage(name="identification", identified=616, excluded=0, reason="none"),
        PrismaStage(name="screening", identified=616, excluded=0, reason="none"),
        PrismaStage(name="full_text", identified=616, excluded=0, reason="none"),
    ])
    with pytest.raises(IntegrityError, match="zero exclusions"):
        flow.validate()


def test_stage_carry_forward_mismatch_is_rejected():
    flow = PrismaFlow(stages=[
        PrismaStage(name="identification", identified=14000, excluded=2000, reason="duplicates"),
        PrismaStage(name="screening", identified=9999, excluded=500, reason="ineligible"),
    ])
    with pytest.raises(IntegrityError, match="carry-forward"):
        flow.validate()


def test_excluding_more_than_identified_is_rejected():
    with pytest.raises(ValueError):
        PrismaStage(name="screening", identified=10, excluded=11, reason="impossible")


def test_exclusion_requires_a_reason():
    with pytest.raises(ValueError, match="reason"):
        PrismaStage(name="screening", identified=10, excluded=5, reason="")


def test_to_csv_round_trips(tmp_path):
    flow = PrismaFlow(stages=[
        PrismaStage(name="identification", identified=100, excluded=10, reason="duplicates"),
        PrismaStage(name="screening", identified=90, excluded=40, reason="ineligible"),
    ])
    out = tmp_path / "prisma.csv"
    flow.to_csv(out)
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0] == "stage,identified,excluded,included,reason"
    assert lines[1].startswith("identification,100,10,90,")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_prisma.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.prisma'`

- [ ] **Step 3: Write the implementation**

Create `egm/pipeline/prisma.py`:

```python
"""PRISMA flow with reconciliation assertions.

The superseded pipeline recorded 616 identified, 0 excluded, 616 included
across every stage (see DEPRECATED.md). validate() makes that unrepresentable.
"""
import csv
import pathlib

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pipeline.integrity import IntegrityError


class PrismaStage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    identified: int = Field(ge=0)
    excluded: int = Field(ge=0)
    reason: str

    @model_validator(mode="after")
    def _check(self) -> "PrismaStage":
        if self.excluded > self.identified:
            raise ValueError(
                f"{self.name}: excluded ({self.excluded}) exceeds identified ({self.identified})"
            )
        if self.excluded > 0 and not self.reason.strip():
            raise ValueError(f"{self.name}: a non-zero exclusion requires a reason")
        return self

    @property
    def included(self) -> int:
        return self.identified - self.excluded


class PrismaFlow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stages: list[PrismaStage]

    def included_after(self, name: str) -> int:
        for stage in self.stages:
            if stage.name == name:
                return stage.included
        raise KeyError(f"no stage named {name!r}")

    def validate(self) -> None:
        """Raise IntegrityError if the flow is internally inconsistent."""
        if not self.stages:
            raise IntegrityError("PRISMA flow has no stages")

        for earlier, later in zip(self.stages, self.stages[1:]):
            if later.identified != earlier.included:
                raise IntegrityError(
                    f"carry-forward mismatch: {earlier.name} included {earlier.included} "
                    f"but {later.name} identified {later.identified}"
                )

        if sum(stage.excluded for stage in self.stages) == 0:
            raise IntegrityError(
                "zero exclusions across the entire flow: no screening occurred"
            )

    def to_csv(self, path: pathlib.Path) -> None:
        self.validate()
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["stage", "identified", "excluded", "included", "reason"])
            for stage in self.stages:
                writer.writerow(
                    [stage.name, stage.identified, stage.excluded, stage.included, stage.reason]
                )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_prisma.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add egm/pipeline/prisma.py egm/tests/test_prisma.py
git commit -m "feat: add PRISMA flow that rejects a zero-exclusion pipeline

validate() enforces stage carry-forward (each stage's identified equals
the previous stage's included) and rejects a flow with zero exclusions
throughout — the exact shape of the superseded prisma_counts.csv.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 9: Protocol document and registration

Spec §3 and §9.1. **No screening begins until this is registered and timestamped.** This task produces the document; registration is a manual submission the investigator performs.

**Files:**
- Create: `egm/protocol/protocol.md`
- Create: `egm/protocol/amendments.md`
- Create: `egm/protocol/REGISTRATION.md`
- Test: `egm/tests/test_protocol.py`

**Interfaces:**
- Consumes: `pipeline.query.build_pubmed_query` (the protocol embeds the exact executed query)
- Produces: a registerable protocol document; `REGISTRATION.md` records the ID once assigned

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_protocol.py`:

```python
"""The protocol must pre-specify the decisions that cannot be made later."""
import pathlib

from pipeline.query import build_pubmed_query

PROTOCOL = pathlib.Path(__file__).resolve().parents[1] / "protocol" / "protocol.md"


def test_protocol_exists():
    assert PROTOCOL.exists()


def test_protocol_embeds_the_exact_executed_query():
    """The registered query must be byte-identical to the one the code builds."""
    text = PROTOCOL.read_text(encoding="utf-8")
    assert build_pubmed_query(include_ncrna=False, date_limited=True) in text


def test_protocol_prespecifies_the_poolability_rule():
    text = PROTOCOL.read_text(encoding="utf-8")
    for required in ["10 studies", "comparable comparator", "pre-registered null"]:
        assert required in text, f"poolability rule must state {required!r}"


def test_protocol_prespecifies_screening_validation():
    text = PROTOCOL.read_text(encoding="utf-8")
    for required in ["0.75", "1,000", "false negative"]:
        assert required in text


def test_protocol_declares_ai_use_and_non_authorship():
    text = PROTOCOL.read_text(encoding="utf-8").lower()
    assert "not an author" in text or "not authors" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_protocol.py -v`
Expected: FAIL — protocol.md does not exist

- [ ] **Step 3: Write the protocol**

Create `egm/protocol/protocol.md`. It must contain, at minimum, these sections, with content drawn verbatim from the spec so that the registered record and the implementation cannot drift:

1. **Title, investigator, affiliation, contact, date, version.**
2. **Background and rationale** — spec §1.
3. **Objectives** — spec §2, primary and secondary stated separately.
4. **Eligibility criteria** — spec §4.1 and §4.3 as a table, including the chain-completeness definition (§4.2) and the ncRNA exclusion with its stated rationale (§4.4).
5. **Information sources and search strategy** — spec §5.1, with the **exact query string** produced by `build_pubmed_query(include_ncrna=False, date_limited=True)` pasted verbatim (the test asserts this), plus the validated counts table from §5.2.
6. **Screening procedure** — spec §7.1 in full: the κ ≥ 0.75 calibration gate, AI screening, and the 1,000-record confidence-stratified validation of AI **excludes**, with the commitment to report a poor recall estimate rather than re-run.
7. **Data items and coding schema** — spec §8.2 table.
8. **Risk of bias** — spec §7.2, tools per modality plus the six epigenetic-methods items.
9. **Synthesis and the poolability rule** — spec §7.3 verbatim, including: *"≥10 studies sharing a modality, a comparable comparator, an extractable common effect metric with variance, and not uniformly at high risk of bias"*, the pre-commitment against network meta-analysis, and the **pre-registered null** if no cell qualifies.
10. **Contingencies** — spec §10, especially the 2018–2026 date narrowing and the exposure-arm-only fallback if the κ gate cannot be met.
11. **AI use declaration** — which tasks are AI-assisted, which model and version, and the statement that AI systems are **not authors**.
12. **Amendments policy** — all changes recorded in `amendments.md` with date and rationale; none made silently.

Create `egm/protocol/amendments.md`:

```markdown
# Protocol amendments

Every deviation from the registered protocol is recorded here with its date
and rationale. Nothing is changed silently.

| Date | Section | Change | Rationale |
|---|---|---|---|
| — | — | No amendments to date | — |
```

Create `egm/protocol/REGISTRATION.md`:

```markdown
# Registration status

**Status:** NOT YET REGISTERED — screening must not begin.

| Field | Value |
|---|---|
| Registry | PROSPERO (primary) / OSF Registries (fallback for the map component) |
| Registration ID | *pending* |
| Submitted | *pending* |
| Accepted | *pending* |
| Protocol version registered | v1.0 (`protocol.md`) |

## Gate

Task 10 (corpus build) may proceed before registration, since retrieval is
not screening. **Plan B (screening) must not start until the ID above is
filled in.** This file is the gate.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_protocol.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add egm/protocol/ egm/tests/test_protocol.py
git commit -m "docs: add registerable protocol with pre-specified decision rules

Embeds the exact executed query (asserted byte-identical to the builder),
the kappa >= 0.75 calibration gate, the 1,000-record false-negative
validation, and the poolability rule with its pre-registered null.

REGISTRATION.md is the gate: screening does not begin until the
registration ID is recorded.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 10: End-to-end corpus build

Wires the modules into one reproducible command producing the deliverable.

**Files:**
- Create: `egm/pipeline/build_corpus.py`
- Test: `egm/tests/test_build_corpus.py`

**Interfaces:**
- Consumes: `query.build_pubmed_query`, `pubmed.search`, `pubmed.fetch_summaries`, `dedup.deduplicate`, `prisma.PrismaFlow`, `prisma.PrismaStage`, `provenance.RunManifest`, `provenance.write_artefact`, `provenance.query_hash`
- Produces:
  - `build_corpus(output_dir: pathlib.Path, retmax: int, dry_run: bool) -> dict[str, int]`
  - CLI: `python -m pipeline.build_corpus --output egm/search --retmax 10000`

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_build_corpus.py`:

```python
import json

import pytest

from pipeline import build_corpus as bc
from pipeline.integrity import IntegrityError
from pipeline.schema import SearchRecord


def _record(pmid, doi, title="A methylation study"):
    return SearchRecord(
        source_db="pubmed", source_id=pmid, doi=doi, pmid=pmid, title=title,
        abstract=None, year=2020, journal="J Epi", authors=["Smith J"],
        retrieved_at="2026-09-13T10:00:00Z", query_hash="h" * 12,
    )


def test_build_corpus_writes_artefacts_and_reconciles(tmp_path, mocker):
    mocker.patch.object(bc.pubmed, "search", return_value=["1", "2", "3"])
    mocker.patch.object(bc.pubmed, "fetch_summaries", return_value=[
        _record("1", "10.1/a"), _record("2", "10.1/a"), _record("3", "10.1/b"),
    ])

    counts = bc.build_corpus(output_dir=tmp_path, retmax=100, dry_run=False)

    assert counts["input"] == 3
    assert counts["output"] == 2
    assert counts["removed_total"] == 1

    payload = json.loads((tmp_path / "raw" / "pubmed_corpus.json").read_text(encoding="utf-8"))
    assert payload["manifest"]["record_count"] == 2
    assert payload["manifest"]["source_db"] == "pubmed"

    prisma = (tmp_path / "prisma_counts.csv").read_text(encoding="utf-8")
    assert "identification,3,1,2" in prisma


def test_dry_run_writes_nothing(tmp_path, mocker):
    mocker.patch.object(bc.pubmed, "count", return_value=9089)
    counts = bc.build_corpus(output_dir=tmp_path, retmax=100, dry_run=True)
    assert counts["available"] == 9089
    assert not (tmp_path / "raw").exists()


def test_zero_duplicates_across_a_real_corpus_raises(tmp_path, mocker):
    """A multi-thousand-record corpus with no duplicates means dedup silently failed."""
    records = [_record(str(n), f"10.1/{n}") for n in range(1200)]
    mocker.patch.object(bc.pubmed, "search", return_value=[str(n) for n in range(1200)])
    mocker.patch.object(bc.pubmed, "fetch_summaries", return_value=records)

    with pytest.raises(IntegrityError, match="zero exclusions"):
        bc.build_corpus(output_dir=tmp_path, retmax=2000, dry_run=False)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_build_corpus.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.build_corpus'`

- [ ] **Step 3: Write the implementation**

Create `egm/pipeline/build_corpus.py`:

```python
"""End-to-end corpus build: search -> fetch -> deduplicate -> artefacts.

Run:
    python -m pipeline.build_corpus --output egm/search --retmax 10000
    python -m pipeline.build_corpus --output egm/search --dry-run
"""
import argparse
import pathlib

from pipeline import pubmed
from pipeline.dedup import deduplicate
from pipeline.prisma import PrismaFlow, PrismaStage
from pipeline.provenance import RunManifest, query_hash, write_artefact
from pipeline.query import build_pubmed_query


def build_corpus(output_dir: pathlib.Path, retmax: int, dry_run: bool) -> dict[str, int]:
    """Retrieve, deduplicate and persist the PubMed corpus."""
    output_dir = pathlib.Path(output_dir)
    query_string = build_pubmed_query(include_ncrna=False, date_limited=True)

    if dry_run:
        return {"available": pubmed.count(query_string)}

    pmids = pubmed.search(query_string, retmax=retmax)
    records = pubmed.fetch_summaries(pmids, query_hash_value=query_hash(query_string))
    deduped, counts = deduplicate(records)

    write_artefact(
        output_dir / "raw" / "pubmed_corpus.json",
        [record.model_dump() for record in deduped],
        RunManifest.create(
            query_string=query_string,
            source_db="pubmed",
            record_count=len(deduped),
            notes=f"retmax={retmax}; dedup rules: {counts}",
        ),
    )

    # validate() raises if nothing was excluded — see DEPRECATED.md for why.
    flow = PrismaFlow(stages=[
        PrismaStage(
            name="identification",
            identified=counts["input"],
            excluded=counts["removed_total"],
            reason=(
                f"duplicates removed (doi={counts['removed_doi']}, "
                f"pmid={counts['removed_pmid']}, fuzzy={counts['removed_fuzzy']})"
            ),
        )
    ])
    flow.to_csv(output_dir / "prisma_counts.csv")

    (output_dir / "query_executed.txt").write_text(query_string, encoding="utf-8")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the EGM PubMed corpus")
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--retmax", type=int, default=10000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    counts = build_corpus(args.output, args.retmax, args.dry_run)
    for key, value in counts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_build_corpus.py -v`
Expected: 3 passed

- [ ] **Step 5: Run the full suite**

Run: `cd egm && python -m pytest tests/ -v`
Expected: 64 passed (3 + 8 + 8 + 8 + 7 + 6 + 9 + 7 + 5 + 3 — all must pass)

- [ ] **Step 6: Execute the real corpus build**

```bash
cd egm && python -m pipeline.build_corpus --output search --dry-run
```
Expected: `available: ~9089`

Then the full retrieval (takes roughly 10–20 minutes given rate limiting):
```bash
cd egm && python -m pipeline.build_corpus --output search --retmax 10000
```
Expected: non-zero `removed_total`; `search/raw/pubmed_corpus.json`, `search/prisma_counts.csv` and `search/query_executed.txt` written.

If `removed_total` is 0, do **not** work around it — `PrismaFlow.validate()` will raise, and that is correct behaviour signalling a dedup defect to investigate.

- [ ] **Step 7: Commit**

```bash
git add egm/pipeline/build_corpus.py egm/tests/test_build_corpus.py egm/search/
git commit -m "feat: add end-to-end corpus build with PRISMA reconciliation

Search, fetch, deduplicate, and persist with a run manifest. PRISMA
validation raises on a zero-exclusion flow, so a silent dedup failure
cannot produce a plausible-looking artefact.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Plan Completion Criteria

- [ ] `cd egm && python -m pytest tests/ -v` — all pass
- [ ] `DEPRECATED.md` exists; no `schedule:` trigger remains in any workflow
- [ ] `egm/search/raw/pubmed_corpus.json` exists with a manifest whose `record_count` matches its records
- [ ] `egm/search/prisma_counts.csv` shows **non-zero** exclusions
- [ ] `egm/protocol/protocol.md` embeds the byte-identical executed query
- [ ] `egm/protocol/REGISTRATION.md` created (ID may still be pending)

## Gate to Plan B

**Plan B (screening) must not begin until `egm/protocol/REGISTRATION.md` records a registration ID.** Retrieval is not screening, so Task 10 may run beforehand; the first screening decision must not.

## Deferred to later plans

| Deferred | Plan | Why not now |
|---|---|---|
| Embase, Web of Science, CENTRAL, ClinicalTrials.gov, ICTRP retrieval | B | Each needs institutional access or a distinct client; PubMed proves the pipeline shape first |
| AI screening prompts, calibration, recall validation | B | Prompts depend on the Stage 0 pilot against the real corpus |
| Coding schema implementation, full-text extraction | B | Requires the screened set |
| Map generation, both views, manuscript build | C | Requires the coded dataset |
| Meta-analysis pooling | D | Scope is determined by the poolability rule applied to coded data — unknowable now, by design (spec §7.3) |
