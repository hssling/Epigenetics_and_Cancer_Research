# EGM Screening Implementation Plan (Plan B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the software that screens 9,088 records against the registered eligibility criteria, measures agreement between the investigator and an AI screener, and produces a recall estimate with an exact confidence interval.

**Architecture:** Five focused modules under `egm/pipeline/`, each reading and writing files so every stage is independently resumable and auditable. A Pydantic schema makes an invalid decision record unconstructable. The AI screener uses `client.messages.parse()` with a frozen, SHA-256-hashed prompt, and records per-request token usage so cost is measured rather than estimated. Human screening runs in a local keyboard-driven web app that fsyncs each decision before advancing.

**Tech Stack:** Python 3.11+, Pydantic v2, `anthropic` SDK 0.86+, `http.server` (stdlib), pytest + pytest-mock. No new dependencies beyond `anthropic`, which is already installed.

**Spec:** [docs/superpowers/specs/2026-09-13-egm-screening-design.md](../specs/2026-09-13-egm-screening-design.md)

**Registration:** [osf.io/3xtf2](https://osf.io/3xtf2) — DOI `10.17605/OSF.IO/3XTF2`. The methodology is a public commitment; nothing in this plan may change it without a dated amendment in `egm/protocol/amendments.md`.

## Global Constraints

Every task's requirements implicitly include this section.

- **Python 3.11+, Pydantic v2.** `Optional[X]` without a default is a *required* field that accepts `None` — absence must be stated, never assumed. Never add `= None`.
- **No default values in the data path.** Missing data stays `None`. A function substituting a constant is a defect.
- **Fail loud.** A missing required value raises. **An API failure is never recorded as a screening decision** — the decision log contains judgements, not error states.
- **No RNG outside `egm/pipeline/sampling.py`.** Enforced by an AST scan in `tests/test_integrity.py` that covers all of `egm/` except `egm/tests/`.
- **Append-only.** Decision logs are JSONL; a changed decision appends a new line with `supersedes` set. No line is ever edited or removed.
- **Model IDs, exact strings:** `claude-opus-5` and `claude-haiku-4-5`. Never append date suffixes.
- **The API key is read from the environment only.** Never write it to a file, a log, an artefact, or a commit.
- **Every test must fail without its fix.** A test that passes either way is worthless — verify by mutation, not by green output.
- Commit after every task, Conventional Commits, message ending with:
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- Do NOT push. Local commits only.

---

## File Structure

| Path | Responsibility |
|---|---|
| `egm/pipeline/screen_schema.py` | `Decision`, `Criterion`, `Screener`, `Stage`, `ScreeningDecision`. The cross-field rules live here |
| `egm/pipeline/prompts/screening_v1.md` | The frozen screening instructions — plain text, no code |
| `egm/pipeline/ai_screener.py` | Anthropic client: prompt loading + hashing, structured output, caching, resumable run, usage recording |
| `egm/pipeline/screen_app.py` | Local HTTP server + single-page keyboard UI; durable append |
| `egm/pipeline/agreement.py` | Cohen's kappa with CI, per-criterion breakdown, disagreement listing |
| `egm/pipeline/recall.py` | Sensitivity, specificity, Clopper-Pearson intervals, confusion matrix, stratum weighting |
| `egm/pipeline/draw_sample.py` | CLI wrapping `sampling.stratified_sample` for the two registered draws |
| `egm/screening/` | Artefacts (git-tracked): samples, decision logs, prompt snapshot, reports |
| `egm/tests/test_screen_schema.py` … `test_recall.py` | Tests, one file per module |

---

## Task 1: The decision record

The schema is the integrity mechanism. An exclusion without a criterion, or an AI decision without a model ID and prompt hash, must be impossible to construct — not merely discouraged.

**Files:**
- Create: `egm/pipeline/screen_schema.py`
- Test: `egm/tests/test_screen_schema.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `Decision = Literal["include", "exclude", "unclear"]`
  - `Criterion = Literal["not_human", "not_primary", "no_measured_marker", "ncrna_only", "no_approach_link", "out_of_window", "not_english"]`
  - `Screener = Literal["human", "ai"]`
  - `Stage = Literal["calibration", "screening", "validation"]`
  - `ScreeningDecision` (Pydantic model, fields per spec §4)
  - `CRITERIA: tuple[Criterion, ...]` — ordered, index 0 is criterion 1
  - `read_decisions(path) -> list[ScreeningDecision]`
  - `append_decision(path, decision) -> None` — appends and fsyncs

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_screen_schema.py`:

```python
"""The decision record. Invalid combinations must be unconstructable."""
import pytest
from pydantic import ValidationError

from pipeline.screen_schema import (
    CRITERIA,
    ScreeningDecision,
    append_decision,
    read_decisions,
)


def _human(**overrides):
    base = dict(
        record_id="egm-000001", pmid="111", decision="include", criterion=None,
        confidence=None, reason=None, screener="human", model_id=None,
        prompt_sha256=None, stage="calibration",
        decided_at="2026-09-13T10:00:00Z", supersedes=None,
    )
    return {**base, **overrides}


def _ai(**overrides):
    return _human(**{
        "screener": "ai", "model_id": "claude-opus-5",
        "prompt_sha256": "a" * 64, "confidence": 0.9,
        "reason": "Measures DNA methylation after a dietary intervention.",
        **overrides,
    })


def test_there_are_exactly_seven_criteria_in_registered_order():
    assert CRITERIA == (
        "not_human", "not_primary", "no_measured_marker", "ncrna_only",
        "no_approach_link", "out_of_window", "not_english",
    )


def test_a_valid_human_include_is_accepted():
    assert ScreeningDecision(**_human()).decision == "include"


def test_exclude_without_a_criterion_is_rejected():
    """An exclusion with no reason is not reportable in a PRISMA diagram."""
    with pytest.raises(ValidationError, match="criterion"):
        ScreeningDecision(**_human(decision="exclude", criterion=None))


def test_include_with_a_criterion_is_rejected():
    with pytest.raises(ValidationError, match="criterion"):
        ScreeningDecision(**_human(decision="include", criterion="not_human"))


def test_unclear_with_a_criterion_is_rejected():
    with pytest.raises(ValidationError, match="criterion"):
        ScreeningDecision(**_human(decision="unclear", criterion="not_human"))


def test_ai_decision_without_model_id_is_rejected():
    """A decision that cannot be traced to a model is not auditable."""
    with pytest.raises(ValidationError, match="model_id"):
        ScreeningDecision(**_ai(model_id=None))


def test_ai_decision_without_prompt_hash_is_rejected():
    with pytest.raises(ValidationError, match="prompt_sha256"):
        ScreeningDecision(**_ai(prompt_sha256=None))


def test_ai_decision_without_confidence_is_rejected():
    """Confidence stratifies the validation sample; it cannot be optional for AI."""
    with pytest.raises(ValidationError, match="confidence"):
        ScreeningDecision(**_ai(confidence=None))


def test_human_decision_with_a_model_id_is_rejected():
    with pytest.raises(ValidationError, match="model_id"):
        ScreeningDecision(**_human(model_id="claude-opus-5"))


def test_confidence_outside_zero_to_one_is_rejected():
    with pytest.raises(ValidationError):
        ScreeningDecision(**_ai(confidence=1.5))


def test_omitting_a_nullable_field_raises_rather_than_defaulting():
    kwargs = _human()
    del kwargs["supersedes"]
    with pytest.raises(ValidationError, match="supersedes"):
        ScreeningDecision(**kwargs)


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        ScreeningDecision(**_human(notes="extra"))


def test_append_and_read_round_trip(tmp_path):
    path = tmp_path / "decisions.jsonl"
    append_decision(path, ScreeningDecision(**_human(record_id="egm-1")))
    append_decision(path, ScreeningDecision(**_ai(record_id="egm-2")))

    decisions = read_decisions(path)
    assert [d.record_id for d in decisions] == ["egm-1", "egm-2"]
    assert decisions[1].model_id == "claude-opus-5"


def test_append_never_rewrites_earlier_lines(tmp_path):
    """Append-only: an amendment adds a line, it does not edit one."""
    path = tmp_path / "decisions.jsonl"
    append_decision(path, ScreeningDecision(**_human(record_id="egm-1")))
    first_line = path.read_text(encoding="utf-8").splitlines()[0]

    append_decision(path, ScreeningDecision(
        **_human(record_id="egm-1", decision="exclude", criterion="not_human",
                 supersedes="2026-09-13T10:00:00Z")))

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[0] == first_line


def test_read_decisions_on_missing_file_returns_empty(tmp_path):
    assert read_decisions(tmp_path / "absent.jsonl") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_screen_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.screen_schema'`

- [ ] **Step 3: Write the implementation**

Create `egm/pipeline/screen_schema.py`:

```python
"""The screening decision record.

One schema for every judgement, human or AI. The cross-field rules are
enforced here rather than checked later: an exclusion without a criterion, or
an AI decision that cannot be traced to a model and a prompt, cannot be
constructed at all.
"""
import json
import os
import pathlib
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

Decision = Literal["include", "exclude", "unclear"]
Criterion = Literal[
    "not_human",
    "not_primary",
    "no_measured_marker",
    "ncrna_only",
    "no_approach_link",
    "out_of_window",
    "not_english",
]
Screener = Literal["human", "ai"]
Stage = Literal["calibration", "screening", "validation"]

# Registered order. Index 0 is criterion 1 on the screening keypad.
CRITERIA: tuple[Criterion, ...] = (
    "not_human",
    "not_primary",
    "no_measured_marker",
    "ncrna_only",
    "no_approach_link",
    "out_of_window",
    "not_english",
)

CRITERION_LABELS: dict[Criterion, str] = {
    "not_human": "Not a human study (animal, in vitro, cell-line only)",
    "not_primary": "Not a primary study (review, editorial, comment, letter, abstract without data)",
    "no_measured_marker": "No directly measured epigenetic marker",
    "ncrna_only": "Non-coding RNA as the sole marker",
    "no_approach_link": "No modifiable exposure/intervention and no clinical or public health decision",
    "out_of_window": "Outside 2015-2026",
    "not_english": "Not in English",
}


class ScreeningDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    pmid: str
    decision: Decision
    criterion: Optional[Criterion]
    confidence: Optional[float] = Field(ge=0.0, le=1.0)
    reason: Optional[str]
    screener: Screener
    model_id: Optional[str]
    prompt_sha256: Optional[str]
    stage: Stage
    decided_at: str
    supersedes: Optional[str]

    @model_validator(mode="after")
    def _cross_field_rules(self) -> "ScreeningDecision":
        if self.decision == "exclude" and self.criterion is None:
            raise ValueError(
                "criterion is required when decision is 'exclude': an exclusion "
                "without a stated reason cannot be reported in a PRISMA diagram"
            )
        if self.decision != "exclude" and self.criterion is not None:
            raise ValueError(
                f"criterion must be None when decision is {self.decision!r}"
            )

        if self.screener == "ai":
            if not self.model_id:
                raise ValueError("model_id is required for an AI decision")
            if not self.prompt_sha256:
                raise ValueError("prompt_sha256 is required for an AI decision")
            if self.confidence is None:
                raise ValueError(
                    "confidence is required for an AI decision: it stratifies "
                    "the validation sample"
                )
        else:
            if self.model_id is not None:
                raise ValueError("model_id must be None for a human decision")
            if self.prompt_sha256 is not None:
                raise ValueError("prompt_sha256 must be None for a human decision")
        return self


def append_decision(path: pathlib.Path, decision: ScreeningDecision) -> None:
    """Append one decision and flush it to disk before returning.

    The fsync matters: human screening is irreplaceable work, and a decision
    that is buffered rather than written is lost on a crash.
    """
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(decision.model_dump(), sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def read_decisions(path: pathlib.Path) -> list[ScreeningDecision]:
    """Read a decision log. A missing file is an empty log, not an error."""
    path = pathlib.Path(path)
    if not path.exists():
        return []
    return [
        ScreeningDecision(**json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_screen_schema.py -v`
Expected: 15 passed

- [ ] **Step 5: Commit**

```bash
git add egm/pipeline/screen_schema.py egm/tests/test_screen_schema.py
git commit -m "feat: add screening decision schema with cross-field rules

An exclusion without a criterion, and an AI decision without a model id,
prompt hash and confidence, are unconstructable rather than merely
discouraged. append_decision fsyncs before returning: human screening is
irreplaceable work and a buffered write is a lost decision.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: The frozen prompt and its hash

The prompt is the screening instrument. Its hash goes into every AI decision, so a decision traces to the exact text that produced it and a modified prompt is detectable rather than asserted.

**Files:**
- Create: `egm/pipeline/prompts/screening_v1.md`
- Create: `egm/pipeline/prompt_loader.py`
- Test: `egm/tests/test_prompt_loader.py`

**Interfaces:**
- Consumes: `screen_schema.CRITERIA`, `CRITERION_LABELS`
- Produces:
  - `load_prompt(version: str = "v1") -> tuple[str, str]` returning `(text, sha256_hex)`
  - `PROMPT_DIR: pathlib.Path`

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_prompt_loader.py`:

```python
"""The frozen prompt and its hash."""
import hashlib

import pytest

from pipeline.prompt_loader import load_prompt
from pipeline.screen_schema import CRITERIA


def test_loads_text_and_hash():
    text, digest = load_prompt("v1")
    assert text.strip()
    assert len(digest) == 64
    assert digest == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_hash_is_stable_across_loads():
    assert load_prompt("v1")[1] == load_prompt("v1")[1]


def test_prompt_names_every_registered_criterion():
    """A criterion the screener is never told about cannot be applied."""
    text, _ = load_prompt("v1")
    for criterion in CRITERIA:
        assert criterion in text, f"prompt does not mention {criterion}"


def test_prompt_states_the_uncertainty_rule():
    """The registration commits to resolving uncertainty toward inclusion."""
    text, _ = load_prompt("v1")
    assert "unclear" in text.lower()


def test_unknown_version_raises():
    with pytest.raises(FileNotFoundError, match="v99"):
        load_prompt("v99")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_prompt_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.prompt_loader'`

- [ ] **Step 3: Write the prompt**

Create `egm/pipeline/prompts/screening_v1.md`. This is the screening instrument; write it exactly as given:

```markdown
You are screening records for a systematic evidence gap map on epigenetic
approaches in health and public health practice. You are applying
pre-registered eligibility criteria (OSF 3xtf2) to a title and abstract.

Decide one of: include, exclude, unclear.

## Include if ALL of these hold

1. Human study (not animal, not in vitro, not cell-line only).
2. Primary study: randomised controlled trial, non-randomised trial, cohort,
   case-control, or cross-sectional.
3. Directly measures at least one eligible epigenetic marker: DNA methylation
   (global, candidate-gene, or epigenome-wide), histone modification,
   chromatin state, or an epigenetic clock / DNAm age measure.
4. Relates that marker to EITHER (a) a modifiable exposure or intervention,
   OR (b) a clinical or public health decision (screening, risk
   stratification, treatment selection, prognosis, monitoring).
5. Published 2015-2026.
6. In English.

## Exclude, using the FIRST criterion below that applies

1. `not_human` — animal, in vitro, or cell-line only.
2. `not_primary` — review, systematic review, meta-analysis, editorial,
   comment, letter, or conference abstract without data.
3. `no_measured_marker` — no directly measured epigenetic marker. This
   includes intervention trials assumed to act epigenetically that did not
   measure a marker: without measurement the epigenetic claim is not testable
   from the study.
4. `ncrna_only` — non-coding RNA (miRNA, lncRNA) is the ONLY epigenetic
   marker. If an eligible marker is also measured, the study is not excluded
   on this ground.
5. `no_approach_link` — neither a modifiable exposure/intervention nor a
   clinical or public health decision.
6. `out_of_window` — outside 2015-2026.
7. `not_english`.

## Return `unclear` when the abstract does not let you decide

This matters more than getting a borderline case right. A record marked
`unclear` goes to a human reviewer. A record you exclude on a guess is never
looked at again, and an eligible study lost that way is invisible in the
final review.

Return `unclear` — do not guess — when:

- the abstract does not say whether a marker was measured or only discussed;
- you cannot tell the study design;
- the abstract is absent, truncated, or uninformative.

## Judging the measured-marker criterion

Judge what the study MEASURED, not what it argues or speculates about. A
study that discusses epigenetic mechanisms in its introduction or discussion,
but measures only gene expression, protein levels, or clinical outcomes, does
not measure an epigenetic marker.

## Confidence

Report your confidence in the decision, 0 to 1. Be honest: low confidence
routes a record into the validation sample, which is how errors get caught.
Uniformly high confidence defeats that mechanism.

## Reason

One sentence, stating what in the record drove the decision.
```

- [ ] **Step 4: Write the loader**

Create `egm/pipeline/prompt_loader.py`:

```python
"""Load the frozen screening prompt and hash it.

The hash is written into every AI decision, so a decision traces to the exact
instruction text that produced it. A changed prompt changes the hash, which
makes drift detectable in the decision log rather than a matter of trust.
"""
import hashlib
import pathlib

PROMPT_DIR = pathlib.Path(__file__).resolve().parent / "prompts"


def load_prompt(version: str = "v1") -> tuple[str, str]:
    """Return (prompt_text, sha256_hex) for the named prompt version."""
    path = PROMPT_DIR / f"screening_{version}.md"
    if not path.exists():
        raise FileNotFoundError(
            f"no screening prompt for version {version!r} at {path}"
        )
    text = path.read_text(encoding="utf-8")
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_prompt_loader.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add egm/pipeline/prompts/ egm/pipeline/prompt_loader.py egm/tests/test_prompt_loader.py
git commit -m "feat: add frozen screening prompt with content hash

The prompt is the screening instrument. Its SHA-256 goes into every AI
decision, so a decision traces to the exact text that produced it and
prompt drift is detectable in the log rather than asserted.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: The AI screener

**Files:**
- Create: `egm/pipeline/ai_screener.py`
- Test: `egm/tests/test_ai_screener.py`

**Interfaces:**
- Consumes: `screen_schema.ScreeningDecision`, `append_decision`, `read_decisions`; `prompt_loader.load_prompt`
- Produces:
  - `ScreenerOutput` (Pydantic: `decision`, `criterion`, `confidence`, `reason`) — the structured-output schema
  - `UsageRecord` (Pydantic: `record_id`, `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`)
  - `screen_record(client, record, model_id, prompt_text, prompt_sha, stage) -> tuple[ScreeningDecision, UsageRecord]`
  - `screen_sample(client, records, model_id, out_path, usage_path, stage, prompt_version="v1") -> dict[str, int]`
  - `ScreenerError(Exception)`

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_ai_screener.py`:

```python
"""The AI screener. Structured output, provenance, resumability, fail-loud."""
import json

import pytest

from pipeline import ai_screener as ais
from pipeline.screen_schema import ScreeningDecision, read_decisions


def _record(pmid="111", title="Diet and DNA methylation", abstract="We measured..."):
    return {
        "record_id": f"egm-{pmid}", "pmid": pmid, "title": title,
        "abstract": abstract, "year": 2020, "journal": "J Epi",
    }


class _FakeParsed:
    def __init__(self, parsed, usage=None):
        self.parsed_output = parsed
        self.usage = usage or _FakeUsage()


class _FakeUsage:
    input_tokens = 500
    output_tokens = 120
    cache_read_input_tokens = 1300
    cache_creation_input_tokens = 0


def _client(mocker, parsed):
    client = mocker.MagicMock()
    client.messages.parse.return_value = _FakeParsed(parsed)
    return client


def test_include_decision_carries_full_provenance(mocker):
    parsed = ais.ScreenerOutput(
        decision="include", criterion=None, confidence=0.92,
        reason="Measures methylation after a dietary intervention.",
    )
    client = _client(mocker, parsed)

    decision, usage = ais.screen_record(
        client, _record(), "claude-opus-5", "PROMPT TEXT", "b" * 64, "calibration"
    )

    assert isinstance(decision, ScreeningDecision)
    assert decision.decision == "include"
    assert decision.model_id == "claude-opus-5"
    assert decision.prompt_sha256 == "b" * 64
    assert decision.confidence == 0.92
    assert decision.screener == "ai"
    assert decision.stage == "calibration"
    assert usage.output_tokens == 120


def test_exclude_decision_carries_its_criterion(mocker):
    parsed = ais.ScreenerOutput(
        decision="exclude", criterion="not_primary", confidence=0.97,
        reason="Narrative review.",
    )
    decision, _ = ais.screen_record(
        _client(mocker, parsed), _record(), "claude-opus-5", "P", "c" * 64, "screening"
    )
    assert decision.criterion == "not_primary"


def test_exclude_without_a_criterion_from_the_model_raises(mocker):
    """The model returned something the schema forbids; that must not be stored."""
    parsed = ais.ScreenerOutput(
        decision="exclude", criterion=None, confidence=0.8, reason="No reason given.",
    )
    with pytest.raises(ais.ScreenerError, match="criterion"):
        ais.screen_record(
            _client(mocker, parsed), _record(), "claude-opus-5", "P", "d" * 64, "screening"
        )


def test_api_failure_raises_and_records_nothing(mocker, tmp_path):
    """A failure must never become an exclusion in the decision log."""
    client = mocker.MagicMock()
    client.messages.parse.side_effect = RuntimeError("connection reset")

    out = tmp_path / "decisions.jsonl"
    with pytest.raises(ais.ScreenerError, match="111"):
        ais.screen_sample(
            client, [_record("111")], "claude-opus-5", out,
            tmp_path / "usage.jsonl", "screening",
        )
    assert read_decisions(out) == []


def test_run_is_resumable_and_skips_completed_records(mocker, tmp_path):
    parsed = ais.ScreenerOutput(
        decision="include", criterion=None, confidence=0.9, reason="Eligible.",
    )
    client = _client(mocker, parsed)
    out, usage = tmp_path / "d.jsonl", tmp_path / "u.jsonl"

    ais.screen_sample(client, [_record("111")], "claude-opus-5", out, usage, "screening")
    first_calls = client.messages.parse.call_count

    counts = ais.screen_sample(
        client, [_record("111"), _record("222")], "claude-opus-5", out, usage, "screening"
    )

    assert counts == {"total": 2, "screened": 1, "skipped": 1}
    assert client.messages.parse.call_count == first_calls + 1
    assert len(read_decisions(out)) == 2


def test_system_prompt_is_cached_and_carries_the_frozen_text(mocker):
    parsed = ais.ScreenerOutput(
        decision="unclear", criterion=None, confidence=0.3, reason="Abstract absent.",
    )
    client = _client(mocker, parsed)
    ais.screen_record(client, _record(), "claude-opus-5", "FROZEN", "e" * 64, "screening")

    kwargs = client.messages.parse.call_args.kwargs
    system = kwargs["system"]
    assert system[0]["text"] == "FROZEN"
    assert system[0]["cache_control"] == {"type": "ephemeral"}
    assert kwargs["output_format"] is ais.ScreenerOutput
    assert kwargs["model"] == "claude-opus-5"


def test_record_content_reaches_the_model(mocker):
    parsed = ais.ScreenerOutput(
        decision="include", criterion=None, confidence=0.9, reason="ok",
    )
    client = _client(mocker, parsed)
    ais.screen_record(
        client, _record(title="Unique Title Here", abstract="Unique Abstract Here"),
        "claude-opus-5", "P", "f" * 64, "screening",
    )
    content = client.messages.parse.call_args.kwargs["messages"][0]["content"]
    assert "Unique Title Here" in content
    assert "Unique Abstract Here" in content


def test_usage_is_recorded_per_record(mocker, tmp_path):
    parsed = ais.ScreenerOutput(
        decision="include", criterion=None, confidence=0.9, reason="ok",
    )
    out, usage = tmp_path / "d.jsonl", tmp_path / "u.jsonl"
    ais.screen_sample(
        _client(mocker, parsed), [_record("111")], "claude-opus-5", out, usage, "screening"
    )

    lines = [json.loads(l) for l in usage.read_text(encoding="utf-8").splitlines()]
    assert lines[0]["record_id"] == "egm-111"
    assert lines[0]["output_tokens"] == 120
    assert lines[0]["cache_read_input_tokens"] == 1300


def test_missing_abstract_is_sent_as_an_explicit_marker(mocker):
    """5 of 9,088 records genuinely have no abstract; the model must be told."""
    parsed = ais.ScreenerOutput(
        decision="unclear", criterion=None, confidence=0.2, reason="No abstract.",
    )
    client = _client(mocker, parsed)
    ais.screen_record(
        client, _record(abstract=None), "claude-opus-5", "P", "a" * 64, "screening"
    )
    content = client.messages.parse.call_args.kwargs["messages"][0]["content"]
    assert "[no abstract available]" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_ai_screener.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.ai_screener'`

- [ ] **Step 3: Write the implementation**

Create `egm/pipeline/ai_screener.py`:

```python
"""AI title/abstract screening against the frozen prompt.

Every decision carries the model id and the prompt hash, so it traces to the
exact instrument that produced it. An API failure raises; it is never recorded
as a screening decision, because a failure silently converted into an
exclusion corrupts both the PRISMA count and the recall estimate and is
undetectable afterwards.
"""
import pathlib
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from pipeline.prompt_loader import load_prompt
from pipeline.screen_schema import (
    Criterion,
    Decision,
    ScreeningDecision,
    Stage,
    append_decision,
    read_decisions,
)

# Classification needs little output. Opus 5 runs adaptive thinking by
# default and thinking bills as output, so this ceiling also bounds cost per
# record; the calibration run measures what is actually used.
MAX_TOKENS = 2048


class ScreenerError(Exception):
    """Screening failed for a record. Never caught internally."""


class ScreenerOutput(BaseModel):
    """The structured response required from the model."""

    model_config = ConfigDict(extra="forbid")

    decision: Decision
    criterion: Optional[Criterion]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class UsageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    model_id: str
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int


def _render(record: dict[str, Any]) -> str:
    abstract = record.get("abstract") or "[no abstract available]"
    return (
        f"Title: {record['title']}\n"
        f"Journal: {record.get('journal') or '[not reported]'}\n"
        f"Year: {record.get('year') or '[not reported]'}\n\n"
        f"Abstract:\n{abstract}"
    )


def screen_record(
    client: Any,
    record: dict[str, Any],
    model_id: str,
    prompt_text: str,
    prompt_sha: str,
    stage: Stage,
) -> tuple[ScreeningDecision, UsageRecord]:
    """Screen one record. Raises ScreenerError on any failure."""
    try:
        response = client.messages.parse(
            model=model_id,
            max_tokens=MAX_TOKENS,
            system=[{
                "type": "text",
                "text": prompt_text,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": _render(record)}],
            output_format=ScreenerOutput,
        )
    except Exception as exc:  # noqa: BLE001 - re-raised as ScreenerError
        raise ScreenerError(
            f"screening failed for pmid {record['pmid']}: {exc}"
        ) from exc

    parsed = response.parsed_output
    usage = response.usage

    try:
        decision = ScreeningDecision(
            record_id=record["record_id"],
            pmid=record["pmid"],
            decision=parsed.decision,
            criterion=parsed.criterion,
            confidence=parsed.confidence,
            reason=parsed.reason,
            screener="ai",
            model_id=model_id,
            prompt_sha256=prompt_sha,
            stage=stage,
            decided_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            supersedes=None,
        )
    except Exception as exc:  # noqa: BLE001 - schema violation from the model
        raise ScreenerError(
            f"model returned an invalid decision for pmid {record['pmid']} "
            f"({parsed.decision!r}, criterion={parsed.criterion!r}): {exc}"
        ) from exc

    return decision, UsageRecord(
        record_id=record["record_id"],
        model_id=model_id,
        input_tokens=getattr(usage, "input_tokens", 0),
        output_tokens=getattr(usage, "output_tokens", 0),
        cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
        cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
    )


def screen_sample(
    client: Any,
    records: list[dict[str, Any]],
    model_id: str,
    out_path: pathlib.Path,
    usage_path: pathlib.Path,
    stage: Stage,
    prompt_version: str = "v1",
) -> dict[str, int]:
    """Screen records, appending as it goes. Resumable; skips completed ids."""
    prompt_text, prompt_sha = load_prompt(prompt_version)

    done = {d.record_id for d in read_decisions(out_path) if d.screener == "ai"}
    screened = 0

    usage_path = pathlib.Path(usage_path)
    usage_path.parent.mkdir(parents=True, exist_ok=True)

    for record in records:
        if record["record_id"] in done:
            continue
        decision, usage = screen_record(
            client, record, model_id, prompt_text, prompt_sha, stage
        )
        append_decision(out_path, decision)
        with usage_path.open("a", encoding="utf-8") as handle:
            handle.write(usage.model_dump_json() + "\n")
        screened += 1

    return {
        "total": len(records),
        "screened": screened,
        "skipped": len(records) - screened,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_ai_screener.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add egm/pipeline/ai_screener.py egm/tests/test_ai_screener.py
git commit -m "feat: add AI screener with provenance and fail-loud semantics

Structured output via client.messages.parse; the frozen prompt is cached
and its hash written into every decision. An API failure raises rather
than being recorded, because a failure converted into an exclusion
corrupts the PRISMA count and the recall estimate undetectably.

Records per-request token usage so full-run cost is projected from
measurement rather than estimated — Opus 5 runs adaptive thinking by
default and thinking bills as output.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: Cohen's kappa and the gate

**Files:**
- Create: `egm/pipeline/agreement.py`
- Test: `egm/tests/test_agreement.py`

**Interfaces:**
- Consumes: `screen_schema.ScreeningDecision`, `read_decisions`, `CRITERIA`
- Produces:
  - `AgreementReport` (Pydantic: `n`, `observed_agreement`, `expected_agreement`, `kappa`, `kappa_ci_low`, `kappa_ci_high`, `confusion`, `disagreements`, `gate_met`)
  - `cohens_kappa(human: list[str], ai: list[str]) -> tuple[float, float, float]` → `(kappa, ci_low, ci_high)`
  - `compare(human_path, ai_path, gate=0.75) -> AgreementReport`

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_agreement.py`:

```python
"""Cohen's kappa and the kappa >= 0.75 gate."""
import pytest

from pipeline.agreement import cohens_kappa, compare
from pipeline.screen_schema import ScreeningDecision, append_decision


def test_perfect_agreement_gives_kappa_one():
    labels = ["include", "exclude", "unclear", "include"]
    kappa, _, _ = cohens_kappa(labels, list(labels))
    assert kappa == pytest.approx(1.0)


def test_chance_level_agreement_gives_kappa_near_zero():
    """Agreement that is no better than chance must not look like skill."""
    human = ["include"] * 50 + ["exclude"] * 50
    ai = (["include", "exclude"] * 50)
    kappa, _, _ = cohens_kappa(human, ai)
    assert abs(kappa) < 0.1


def test_systematic_disagreement_gives_negative_kappa():
    kappa, _, _ = cohens_kappa(["include"] * 10 + ["exclude"] * 10,
                               ["exclude"] * 10 + ["include"] * 10)
    assert kappa < 0


def test_high_but_imperfect_agreement():
    human = ["include"] * 40 + ["exclude"] * 60
    ai = ["include"] * 38 + ["exclude"] * 2 + ["exclude"] * 58 + ["include"] * 2
    kappa, low, high = cohens_kappa(human, ai)
    assert 0.85 < kappa < 1.0
    assert low < kappa < high


def test_confidence_interval_narrows_with_more_data():
    small = cohens_kappa(["include", "exclude"] * 10, ["include", "exclude"] * 10)
    large = cohens_kappa(["include", "exclude"] * 200, ["include", "exclude"] * 200)
    assert (large[2] - large[1]) < (small[2] - small[1])


def test_mismatched_lengths_raise():
    with pytest.raises(ValueError, match="length"):
        cohens_kappa(["include"], ["include", "exclude"])


def test_empty_input_raises():
    with pytest.raises(ValueError, match="empty"):
        cohens_kappa([], [])


# --- compare() over decision logs ------------------------------------------


def _write(path, pairs, screener):
    for record_id, decision, criterion in pairs:
        append_decision(path, ScreeningDecision(
            record_id=record_id, pmid=record_id.split("-")[1], decision=decision,
            criterion=criterion, confidence=0.9 if screener == "ai" else None,
            reason="r" if screener == "ai" else None, screener=screener,
            model_id="claude-opus-5" if screener == "ai" else None,
            prompt_sha256="a" * 64 if screener == "ai" else None,
            stage="calibration", decided_at="2026-09-13T10:00:00Z", supersedes=None,
        ))


def test_compare_reports_gate_met_when_kappa_high(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    pairs = [(f"egm-{n}", "include" if n < 40 else "exclude",
              None if n < 40 else "not_primary") for n in range(100)]
    _write(human_p, pairs, "human")
    _write(ai_p, pairs, "ai")

    report = compare(human_p, ai_p, gate=0.75)
    assert report.n == 100
    assert report.kappa == pytest.approx(1.0)
    assert report.gate_met is True
    assert report.disagreements == []


def test_compare_lists_every_disagreement(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    _write(human_p, [("egm-1", "include", None), ("egm-2", "include", None)], "human")
    _write(ai_p, [("egm-1", "include", None),
                  ("egm-2", "exclude", "not_primary")], "ai")

    report = compare(human_p, ai_p, gate=0.75)
    assert len(report.disagreements) == 1
    d = report.disagreements[0]
    assert d["record_id"] == "egm-2"
    assert d["human"] == "include" and d["ai"] == "exclude"
    assert d["ai_criterion"] == "not_primary"


def test_compare_fails_the_gate_on_poor_agreement(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    hp = [(f"egm-{n}", "include" if n % 2 else "exclude",
           None if n % 2 else "not_primary") for n in range(100)]
    ap = [(f"egm-{n}", "exclude" if n % 3 else "include",
           "not_primary" if n % 3 else None) for n in range(100)]
    _write(human_p, hp, "human")
    _write(ai_p, ap, "ai")

    assert compare(human_p, ai_p, gate=0.75).gate_met is False


def test_compare_raises_when_records_do_not_align(tmp_path):
    """Comparing different record sets would silently compute nonsense."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    _write(human_p, [("egm-1", "include", None)], "human")
    _write(ai_p, [("egm-2", "include", None)], "ai")

    with pytest.raises(ValueError, match="egm-1"):
        compare(human_p, ai_p, gate=0.75)


def test_compare_uses_the_latest_decision_when_one_supersedes_another(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    _write(human_p, [("egm-1", "include", None)], "human")
    append_decision(human_p, ScreeningDecision(
        record_id="egm-1", pmid="1", decision="exclude", criterion="not_human",
        confidence=None, reason=None, screener="human", model_id=None,
        prompt_sha256=None, stage="calibration",
        decided_at="2026-09-13T11:00:00Z", supersedes="2026-09-13T10:00:00Z",
    ))
    _write(ai_p, [("egm-1", "exclude", "not_human")], "ai")

    assert compare(human_p, ai_p, gate=0.75).disagreements == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_agreement.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.agreement'`

- [ ] **Step 3: Write the implementation**

Create `egm/pipeline/agreement.py`:

```python
"""Cohen's kappa between the investigator and an AI screener.

The registration gates further work at kappa >= 0.75 on a 300-record
calibration sample. This module computes it, reports its confidence interval,
and lists every disagreement so they can be inspected individually.
"""
import math
import pathlib
from collections import Counter
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from pipeline.screen_schema import ScreeningDecision, read_decisions


class AgreementReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n: int
    observed_agreement: float
    expected_agreement: float
    kappa: float
    kappa_ci_low: float
    kappa_ci_high: float
    confusion: dict[str, int]
    disagreements: list[dict[str, Any]]
    gate: float
    gate_met: bool


def cohens_kappa(human: list[str], ai: list[str]) -> tuple[float, float, float]:
    """Return (kappa, ci_low, ci_high) with a normal-approximation interval."""
    if len(human) != len(ai):
        raise ValueError(
            f"length mismatch: {len(human)} human vs {len(ai)} ai decisions"
        )
    if not human:
        raise ValueError("cannot compute kappa on empty input")

    n = len(human)
    observed = sum(h == a for h, a in zip(human, ai)) / n

    human_counts, ai_counts = Counter(human), Counter(ai)
    labels = set(human_counts) | set(ai_counts)
    expected = sum(
        (human_counts[label] / n) * (ai_counts[label] / n) for label in labels
    )

    if expected == 1.0:
        # Both raters used a single identical label throughout: agreement is
        # total but kappa is undefined. Report 1.0 with a degenerate interval
        # rather than dividing by zero.
        return 1.0, 1.0, 1.0

    kappa = (observed - expected) / (1 - expected)

    se = math.sqrt(observed * (1 - observed) / (n * (1 - expected) ** 2))
    return kappa, kappa - 1.96 * se, kappa + 1.96 * se


def _latest(decisions: list[ScreeningDecision]) -> dict[str, ScreeningDecision]:
    """Last decision wins: the log is append-only and amendments append."""
    latest: dict[str, ScreeningDecision] = {}
    for decision in decisions:
        latest[decision.record_id] = decision
    return latest


def compare(
    human_path: pathlib.Path,
    ai_path: pathlib.Path,
    gate: float = 0.75,
) -> AgreementReport:
    """Compare two decision logs over the same records."""
    human = _latest(read_decisions(human_path))
    ai = _latest(read_decisions(ai_path))

    only_human = sorted(set(human) - set(ai))
    only_ai = sorted(set(ai) - set(human))
    if only_human or only_ai:
        raise ValueError(
            "decision logs cover different records; comparing them would "
            f"compute a meaningless statistic. Only in human: {only_human[:5]}; "
            f"only in ai: {only_ai[:5]}"
        )

    record_ids = sorted(human)
    human_labels = [human[r].decision for r in record_ids]
    ai_labels = [ai[r].decision for r in record_ids]

    kappa, low, high = cohens_kappa(human_labels, ai_labels)

    n = len(record_ids)
    observed = sum(h == a for h, a in zip(human_labels, ai_labels)) / n
    hc, ac = Counter(human_labels), Counter(ai_labels)
    expected = sum((hc[l] / n) * (ac[l] / n) for l in set(hc) | set(ac))

    confusion = Counter(
        f"{h}->{a}" for h, a in zip(human_labels, ai_labels)
    )

    disagreements = [
        {
            "record_id": r,
            "pmid": human[r].pmid,
            "human": human[r].decision,
            "human_criterion": human[r].criterion,
            "ai": ai[r].decision,
            "ai_criterion": ai[r].criterion,
            "ai_confidence": ai[r].confidence,
            "ai_reason": ai[r].reason,
        }
        for r in record_ids
        if human[r].decision != ai[r].decision
    ]

    return AgreementReport(
        n=n,
        observed_agreement=observed,
        expected_agreement=expected,
        kappa=kappa,
        kappa_ci_low=low,
        kappa_ci_high=high,
        confusion=dict(confusion),
        disagreements=disagreements,
        gate=gate,
        gate_met=kappa >= gate,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_agreement.py -v`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add egm/pipeline/agreement.py egm/tests/test_agreement.py
git commit -m "feat: add Cohen's kappa and the calibration gate

Computes kappa with a confidence interval, the confusion matrix, and a
listing of every disagreement for individual inspection. Raises rather
than computing a statistic when the two logs cover different records,
and honours the append-only log by taking the latest decision per record.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: Recall and the Clopper-Pearson interval

This produces the number the registration commits to publishing. It must be right, and it must not be capable of flattering itself.

**Files:**
- Create: `egm/pipeline/recall.py`
- Test: `egm/tests/test_recall.py`

**Interfaces:**
- Consumes: `screen_schema.read_decisions`
- Produces:
  - `clopper_pearson(successes: int, n: int, confidence: float = 0.95) -> tuple[float, float]`
  - `RecallReport` (Pydantic: `n_validated`, `false_negatives`, `sensitivity`, `sensitivity_ci_low`, `sensitivity_ci_high`, `fn_rate`, `fn_rate_ci_high`, `implied_missed_low`, `implied_missed_high`, `by_stratum`, `weighted_fn_rate`)
  - `validate_recall(human_path, ai_path, stratum_sizes: dict[str, int], confidence=0.95) -> RecallReport`

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_recall.py`:

```python
"""Recall validation. This produces a number the registration publishes."""
import pytest

from pipeline.recall import clopper_pearson, validate_recall
from pipeline.screen_schema import ScreeningDecision, append_decision


def test_zero_events_in_one_thousand_matches_the_registered_figure():
    """The registration states 0.368% as the two-sided 95% upper bound."""
    low, high = clopper_pearson(0, 1000, confidence=0.95)
    assert low == 0.0
    assert high == pytest.approx(0.00368, abs=0.00002)


def test_all_successes_gives_upper_bound_one():
    low, high = clopper_pearson(1000, 1000, confidence=0.95)
    assert high == 1.0
    assert low > 0.99


def test_interval_brackets_the_point_estimate():
    low, high = clopper_pearson(50, 1000)
    assert low < 0.05 < high


def test_interval_narrows_as_n_grows():
    small = clopper_pearson(5, 100)
    large = clopper_pearson(50, 1000)
    assert (large[1] - large[0]) < (small[1] - small[0])


def test_successes_exceeding_n_raises():
    with pytest.raises(ValueError, match="exceed"):
        clopper_pearson(11, 10)


def test_zero_n_raises():
    with pytest.raises(ValueError, match="positive"):
        clopper_pearson(0, 0)


# --- validate_recall --------------------------------------------------------


def _decision(path, record_id, decision, screener, confidence=None, criterion=None):
    append_decision(path, ScreeningDecision(
        record_id=record_id, pmid=record_id.split("-")[1], decision=decision,
        criterion=criterion, confidence=confidence,
        reason="r" if screener == "ai" else None, screener=screener,
        model_id="claude-opus-5" if screener == "ai" else None,
        prompt_sha256="a" * 64 if screener == "ai" else None,
        stage="validation", decided_at="2026-09-13T10:00:00Z", supersedes=None,
    ))


def test_no_false_negatives_reports_perfect_sensitivity_with_an_upper_bound(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    for n in range(100):
        rid = f"egm-{n}"
        _decision(ai_p, rid, "exclude", "ai", confidence=0.9, criterion="not_primary")
        _decision(human_p, rid, "exclude", "human", criterion="not_primary")

    report = validate_recall(human_p, ai_p, {"high": 1000})

    assert report.false_negatives == 0
    assert report.sensitivity == 1.0
    assert report.fn_rate == 0.0
    assert report.fn_rate_ci_high > 0
    assert report.implied_missed_high > 0


def test_false_negatives_are_counted_and_reported(tmp_path):
    """A human include among AI excludes is a false negative."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    for n in range(100):
        rid = f"egm-{n}"
        _decision(ai_p, rid, "exclude", "ai", confidence=0.9, criterion="not_primary")
        _decision(human_p, rid, "include" if n < 3 else "exclude", "human",
                  criterion=None if n < 3 else "not_primary")

    report = validate_recall(human_p, ai_p, {"high": 1000})

    assert report.false_negatives == 3
    assert report.sensitivity == pytest.approx(0.97)
    assert report.fn_rate == pytest.approx(0.03)


def test_human_unclear_counts_as_a_false_negative(tmp_path):
    """An 'unclear' the AI excluded should have reached a human. That is a miss."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    for n in range(10):
        rid = f"egm-{n}"
        _decision(ai_p, rid, "exclude", "ai", confidence=0.9, criterion="not_primary")
        _decision(human_p, rid, "unclear" if n == 0 else "exclude", "human",
                  criterion=None if n == 0 else "not_primary")

    assert validate_recall(human_p, ai_p, {"high": 100}).false_negatives == 1


def test_validating_a_non_excluded_record_raises(tmp_path):
    """The validation sample is drawn from AI excludes only."""
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    _decision(ai_p, "egm-1", "include", "ai", confidence=0.9)
    _decision(human_p, "egm-1", "include", "human")

    with pytest.raises(ValueError, match="not excluded"):
        validate_recall(human_p, ai_p, {"high": 10})


def test_stratum_weighting_differs_from_the_raw_rate(tmp_path):
    """Low-confidence exclusions are over-sampled, so the raw rate is biased.

    50 low-confidence records sampled from a population of 100, with 5 misses;
    50 high-confidence sampled from 9,900, with 0. The raw rate is 5%, but the
    population rate is far lower because high-confidence records dominate.
    """
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    for n in range(50):
        rid = f"egm-low{n}"
        _decision(ai_p, rid, "exclude", "ai", confidence=0.2, criterion="not_primary")
        _decision(human_p, rid, "include" if n < 5 else "exclude", "human",
                  criterion=None if n < 5 else "not_primary")
    for n in range(50):
        rid = f"egm-high{n}"
        _decision(ai_p, rid, "exclude", "ai", confidence=0.95, criterion="not_primary")
        _decision(human_p, rid, "exclude", "human", criterion="not_primary")

    report = validate_recall(human_p, ai_p, {"low": 100, "high": 9900})

    assert report.fn_rate == pytest.approx(0.05)
    assert report.weighted_fn_rate < 0.002
    assert set(report.by_stratum) == {"low", "high"}
    assert report.by_stratum["low"]["false_negatives"] == 5


def test_report_has_no_option_to_drop_a_block(tmp_path):
    """The registration forbids re-running until the estimate looks good."""
    import inspect

    from pipeline import recall

    source = inspect.getsource(recall.validate_recall)
    for forbidden in ("exclude_block", "drop_", "ignore_", "min_rate"):
        assert forbidden not in source
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_recall.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.recall'`

- [ ] **Step 3: Write the implementation**

Create `egm/pipeline/recall.py`:

```python
"""Recall validation for AI screening.

Produces the sensitivity estimate and confidence interval the registration
commits to publishing, including when the result is unflattering. There is
deliberately no parameter that excludes a block of the sample from the
calculation.
"""
import pathlib
from collections import defaultdict
from typing import Any

from pydantic import BaseModel, ConfigDict

from pipeline.screen_schema import ScreeningDecision, read_decisions

# Confidence below this is the "low" stratum, and so on. Boundaries are
# recorded here so the stratification is reproducible from the code.
STRATUM_BOUNDARIES: tuple[tuple[str, float], ...] = (
    ("low", 0.5),
    ("mid", 0.8),
    ("high", 1.01),
)


class RecallReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_validated: int
    false_negatives: int
    sensitivity: float
    sensitivity_ci_low: float
    sensitivity_ci_high: float
    fn_rate: float
    fn_rate_ci_low: float
    fn_rate_ci_high: float
    implied_missed_low: float
    implied_missed_high: float
    total_excluded: int
    by_stratum: dict[str, dict[str, Any]]
    weighted_fn_rate: float


def _beta_ppf(p: float, a: float, b: float) -> float:
    """Inverse beta CDF by bisection.

    Used for exact Clopper-Pearson bounds without a SciPy dependency.
    """
    if a <= 0:
        return 0.0
    if b <= 0:
        return 1.0

    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if _beta_cdf(mid, a, b) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _beta_cdf(x: float, a: float, b: float) -> float:
    """Regularised incomplete beta function via its continued fraction."""
    import math

    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0

    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a

    f, c, d = 1.0, 1.0, 0.0
    for i in range(300):
        m = i // 2
        if i == 0:
            numerator = 1.0
        elif i % 2 == 0:
            numerator = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            numerator = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))

        d = 1.0 + numerator * d
        d = 1e-30 if abs(d) < 1e-30 else d
        d = 1.0 / d

        c = 1.0 + numerator / c
        c = 1e-30 if abs(c) < 1e-30 else c

        f *= c * d
        if abs(1.0 - c * d) < 1e-12:
            break

    result = front * (f - 1.0)
    return min(max(result, 0.0), 1.0)


def clopper_pearson(
    successes: int, n: int, confidence: float = 0.95
) -> tuple[float, float]:
    """Exact binomial confidence interval (Clopper-Pearson)."""
    if n <= 0:
        raise ValueError("n must be positive")
    if successes > n:
        raise ValueError(f"successes ({successes}) cannot exceed n ({n})")
    if successes < 0:
        raise ValueError("successes cannot be negative")

    alpha = 1.0 - confidence
    low = 0.0 if successes == 0 else _beta_ppf(alpha / 2, successes, n - successes + 1)
    high = 1.0 if successes == n else _beta_ppf(
        1 - alpha / 2, successes + 1, n - successes
    )
    return low, high


def stratum_of(confidence: float) -> str:
    for name, upper in STRATUM_BOUNDARIES:
        if confidence < upper:
            return name
    return STRATUM_BOUNDARIES[-1][0]


def _latest(decisions: list[ScreeningDecision]) -> dict[str, ScreeningDecision]:
    latest: dict[str, ScreeningDecision] = {}
    for decision in decisions:
        latest[decision.record_id] = decision
    return latest


def validate_recall(
    human_path: pathlib.Path,
    ai_path: pathlib.Path,
    stratum_sizes: dict[str, int],
    confidence: float = 0.95,
) -> RecallReport:
    """Estimate screening recall from hand-screened AI exclusions.

    `stratum_sizes` gives the population size of each confidence stratum
    across ALL AI exclusions, which is what makes the weighted estimate
    meaningful: the sample deliberately over-samples low-confidence records,
    so its raw rate is not the population rate.
    """
    human = _latest(read_decisions(human_path))
    ai = _latest(read_decisions(ai_path))

    shared = sorted(set(human) & set(ai))
    if not shared:
        raise ValueError("no records appear in both decision logs")

    not_excluded = [r for r in shared if ai[r].decision != "exclude"]
    if not_excluded:
        raise ValueError(
            "validation sample contains records the AI did not exclude "
            f"({not_excluded[:5]}); recall is estimated from exclusions only"
        )

    per_stratum: dict[str, dict[str, int]] = defaultdict(
        lambda: {"n": 0, "false_negatives": 0}
    )
    false_negatives = 0

    for record_id in shared:
        stratum = stratum_of(ai[record_id].confidence)
        per_stratum[stratum]["n"] += 1
        # The AI excluded it. If a human would not have, it is a miss —
        # 'unclear' counts, because that record should have reached a human.
        if human[record_id].decision in ("include", "unclear"):
            per_stratum[stratum]["false_negatives"] += 1
            false_negatives += 1

    n = len(shared)
    sensitivity = (n - false_negatives) / n
    sens_low, sens_high = clopper_pearson(n - false_negatives, n, confidence)
    fn_low, fn_high = clopper_pearson(false_negatives, n, confidence)

    total_excluded = sum(stratum_sizes.values())

    weighted = 0.0
    by_stratum: dict[str, dict[str, Any]] = {}
    for stratum, size in stratum_sizes.items():
        counts = per_stratum.get(stratum, {"n": 0, "false_negatives": 0})
        rate = counts["false_negatives"] / counts["n"] if counts["n"] else 0.0
        weighted += rate * (size / total_excluded) if total_excluded else 0.0
        by_stratum[stratum] = {
            "population": size,
            "sampled": counts["n"],
            "false_negatives": counts["false_negatives"],
            "fn_rate": rate,
        }

    return RecallReport(
        n_validated=n,
        false_negatives=false_negatives,
        sensitivity=sensitivity,
        sensitivity_ci_low=sens_low,
        sensitivity_ci_high=sens_high,
        fn_rate=false_negatives / n,
        fn_rate_ci_low=fn_low,
        fn_rate_ci_high=fn_high,
        implied_missed_low=fn_low * total_excluded,
        implied_missed_high=fn_high * total_excluded,
        total_excluded=total_excluded,
        by_stratum=by_stratum,
        weighted_fn_rate=weighted,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_recall.py -v`
Expected: 12 passed

- [ ] **Step 5: Verify the registered figure independently**

Run:
```bash
cd egm && python -c "
from pipeline.recall import clopper_pearson
low, high = clopper_pearson(0, 1000, 0.95)
print(f'0/1000 two-sided 95% upper bound: {high:.5f} = {high*100:.3f}%')
print(f'across 10,500 exclusions: {high*10500:.1f} studies')
print(f'across 14,500 exclusions: {high*14500:.1f} studies')
"
```
Expected: `0.00368 = 0.368%`, and 38.7 / 53.4 studies — matching the figures published in the registration. If these differ, the registration's stated bound and the code disagree, which must be investigated before any screening runs.

- [ ] **Step 6: Commit**

```bash
git add egm/pipeline/recall.py egm/tests/test_recall.py
git commit -m "feat: add recall validation with exact Clopper-Pearson intervals

Produces the sensitivity estimate the registration commits to
publishing. Reproduces the registered 0.368% upper bound for 0/1000
independently, via a bisection beta-quantile rather than a SciPy
dependency.

Reports both the raw sample rate and the stratum-weighted population
rate, because low-confidence exclusions are deliberately over-sampled
and presenting the raw rate as the population rate would understate the
false-negative rate. A human 'unclear' over an AI exclusion counts as a
miss: that record should have reached a human.

There is deliberately no parameter that drops a block from the
calculation; a test asserts the absence.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: The human screening app

**Files:**
- Create: `egm/pipeline/screen_app.py`
- Test: `egm/tests/test_screen_app.py`

**Interfaces:**
- Consumes: `screen_schema.ScreeningDecision`, `append_decision`, `read_decisions`, `CRITERIA`, `CRITERION_LABELS`
- Produces:
  - `load_queue(sample_path, out_path) -> list[dict]` — unscreened records, in order
  - `record_decision(out_path, record, decision, criterion, stage) -> ScreeningDecision`
  - `build_page(record, position, total, elapsed_s) -> str` — the HTML
  - `serve(sample_path, out_path, stage, port) -> None`

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_screen_app.py`:

```python
"""The human screening app. Durability and blindness are the properties."""
import json

import pytest

from pipeline import screen_app
from pipeline.screen_schema import CRITERIA, read_decisions


def _sample(tmp_path, n=3):
    path = tmp_path / "sample.json"
    path.write_text(json.dumps([
        {"record_id": f"egm-{i}", "pmid": str(i), "title": f"Study {i}",
         "abstract": f"Abstract {i}", "year": 2020, "journal": "J Epi"}
        for i in range(n)
    ]), encoding="utf-8")
    return path


def test_queue_starts_with_every_record(tmp_path):
    queue = screen_app.load_queue(_sample(tmp_path, 3), tmp_path / "out.jsonl")
    assert [r["record_id"] for r in queue] == ["egm-0", "egm-1", "egm-2"]


def test_queue_resumes_after_partial_screening(tmp_path):
    sample, out = _sample(tmp_path, 3), tmp_path / "out.jsonl"
    record = json.loads(sample.read_text(encoding="utf-8"))[0]
    screen_app.record_decision(out, record, "include", None, "calibration")

    assert [r["record_id"] for r in screen_app.load_queue(sample, out)] == [
        "egm-1", "egm-2"
    ]


def test_decision_is_written_immediately(tmp_path):
    sample, out = _sample(tmp_path, 1), tmp_path / "out.jsonl"
    record = json.loads(sample.read_text(encoding="utf-8"))[0]

    screen_app.record_decision(out, record, "exclude", "not_primary", "calibration")

    decisions = read_decisions(out)
    assert len(decisions) == 1
    assert decisions[0].decision == "exclude"
    assert decisions[0].criterion == "not_primary"
    assert decisions[0].screener == "human"
    assert decisions[0].model_id is None


def test_amending_a_decision_appends_with_supersedes(tmp_path):
    sample, out = _sample(tmp_path, 1), tmp_path / "out.jsonl"
    record = json.loads(sample.read_text(encoding="utf-8"))[0]

    screen_app.record_decision(out, record, "include", None, "calibration")
    screen_app.record_decision(out, record, "exclude", "not_human", "calibration")

    decisions = read_decisions(out)
    assert len(decisions) == 2
    assert decisions[1].supersedes == decisions[0].decided_at


def test_page_shows_the_record_and_all_seven_criteria(tmp_path):
    record = {"record_id": "egm-1", "pmid": "1", "title": "A Distinctive Title",
              "abstract": "A Distinctive Abstract", "year": 2020, "journal": "J Epi"}
    html = screen_app.build_page(record, position=5, total=300, elapsed_s=120.0)

    assert "A Distinctive Title" in html
    assert "A Distinctive Abstract" in html
    assert "5" in html and "300" in html
    for criterion in CRITERIA:
        assert criterion in html


def test_module_has_no_path_by_which_an_ai_decision_could_reach_the_page():
    """Blindness is structural, not a matter of discipline.

    Asserted on the interfaces rather than by grepping for the word
    "confidence" — record_decision legitimately writes confidence=None for a
    human decision, so a naive text scan would fail on correct code.
    """
    import inspect

    # build_page can only ever see one record and its position.
    assert list(inspect.signature(screen_app.build_page).parameters) == [
        "record", "position", "total", "elapsed_s",
    ]
    # No public function accepts a second decision log to read from.
    for name in ("load_queue", "record_decision", "serve"):
        params = list(inspect.signature(getattr(screen_app, name)).parameters)
        assert not any("ai" in p.lower() for p in params), f"{name} takes {params}"

    source = inspect.getsource(screen_app)
    assert 'screener == "ai"' not in source
    assert "ai_decisions" not in source


def test_missing_abstract_is_shown_explicitly(tmp_path):
    record = {"record_id": "egm-1", "pmid": "1", "title": "T", "abstract": None,
              "year": 2020, "journal": "J"}
    assert "no abstract" in screen_app.build_page(record, 1, 10, 0.0).lower()


def test_record_decision_rejects_an_exclusion_without_a_criterion(tmp_path):
    sample, out = _sample(tmp_path, 1), tmp_path / "out.jsonl"
    record = json.loads(sample.read_text(encoding="utf-8"))[0]
    with pytest.raises(Exception):
        screen_app.record_decision(out, record, "exclude", None, "calibration")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_screen_app.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.screen_app'`

- [ ] **Step 3: Write the implementation**

Create `egm/pipeline/screen_app.py`:

```python
"""Local keyboard-driven app for human title/abstract screening.

Two properties matter more than features:

  - Durability. Each decision is appended and fsynced before the next record
    renders, because 1,300 screening judgements are irreplaceable and a
    buffered write is a lost afternoon.
  - Blindness. This module never loads AI decisions. The registration's
    blind-screening commitment is therefore structural rather than a matter
    of discipline: there is no code path by which an AI decision could reach
    the page.
"""
import argparse
import html
import json
import pathlib
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from pipeline.screen_schema import (
    CRITERIA,
    CRITERION_LABELS,
    ScreeningDecision,
    Stage,
    append_decision,
    read_decisions,
)


def load_queue(
    sample_path: pathlib.Path, out_path: pathlib.Path
) -> list[dict[str, Any]]:
    """Records not yet screened, in sample order."""
    records = json.loads(pathlib.Path(sample_path).read_text(encoding="utf-8"))
    done = {d.record_id for d in read_decisions(out_path)}
    return [r for r in records if r["record_id"] not in done]


def record_decision(
    out_path: pathlib.Path,
    record: dict[str, Any],
    decision: str,
    criterion: Optional[str],
    stage: Stage,
) -> ScreeningDecision:
    """Append one human decision. Amends append with `supersedes` set."""
    previous = [
        d for d in read_decisions(out_path) if d.record_id == record["record_id"]
    ]
    entry = ScreeningDecision(
        record_id=record["record_id"],
        pmid=record["pmid"],
        decision=decision,
        criterion=criterion,
        confidence=None,
        reason=None,
        screener="human",
        model_id=None,
        prompt_sha256=None,
        stage=stage,
        decided_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        supersedes=previous[-1].decided_at if previous else None,
    )
    append_decision(out_path, entry)
    return entry


def build_page(
    record: dict[str, Any], position: int, total: int, elapsed_s: float
) -> str:
    """Render one record. No AI information is available to this function."""
    abstract = record.get("abstract") or "[no abstract available for this record]"
    rate = f"{elapsed_s / position:.0f}s/record" if position else "-"
    remaining = total - position + 1
    eta = f"{(elapsed_s / position) * remaining / 60:.0f} min left" if position else "-"

    buttons = "\n".join(
        f'<li><b>{i + 1}</b> &nbsp;{html.escape(CRITERION_LABELS[c])} '
        f'<code>{html.escape(c)}</code></li>'
        for i, c in enumerate(CRITERIA)
    )

    return f"""<!doctype html><meta charset="utf-8">
<title>Screening {position}/{total}</title>
<style>
 body {{ font: 16px/1.55 system-ui, sans-serif; max-width: 46rem;
        margin: 2rem auto; padding: 0 1rem; }}
 .bar {{ height: 6px; background: #eee; border-radius: 3px; margin: .5rem 0 1.5rem; }}
 .bar > i {{ display:block; height:6px; background:#2563eb; border-radius:3px;
             width: {100 * position / max(total, 1):.1f}%; }}
 .meta {{ color:#666; font-size:.85rem; display:flex; justify-content:space-between; }}
 h1 {{ font-size: 1.25rem; line-height:1.35; margin:.5rem 0 .25rem; }}
 .j {{ color:#666; font-size:.9rem; margin-bottom:1rem; }}
 .a {{ white-space: pre-wrap; background:#fafafa; padding:1rem;
       border-left:3px solid #ddd; }}
 ul {{ list-style:none; padding:0; font-size:.9rem; }}
 li {{ padding:.15rem 0; }}
 kbd {{ background:#eee; border-radius:3px; padding:.1rem .4rem; font-size:.85rem; }}
 #crit {{ display:none; margin-top:1rem; }}
</style>
<div class="meta"><span>{position} / {total}</span><span>{rate} &middot; {eta}</span></div>
<div class="bar"><i></i></div>
<h1>{html.escape(record["title"])}</h1>
<div class="j">{html.escape(str(record.get("journal") or "-"))} &middot;
 {html.escape(str(record.get("year") or "-"))} &middot; PMID {html.escape(record["pmid"])}</div>
<div class="a">{html.escape(abstract)}</div>
<p><kbd>i</kbd> include &nbsp; <kbd>e</kbd> exclude &nbsp; <kbd>u</kbd> unclear</p>
<div id="crit"><b>Exclusion criterion:</b><ul>{buttons}</ul></div>
<script>
let awaiting = false;
document.addEventListener("keydown", (ev) => {{
  const k = ev.key.toLowerCase();
  if (!awaiting) {{
    if (k === "i") go("include", "");
    else if (k === "u") go("unclear", "");
    else if (k === "e") {{ awaiting = true; document.getElementById("crit").style.display = "block"; }}
  }} else {{
    const n = parseInt(k, 10);
    const crits = {json.dumps(list(CRITERIA))};
    if (n >= 1 && n <= crits.length) go("exclude", crits[n - 1]);
    else if (k === "escape") {{ awaiting = false; document.getElementById("crit").style.display = "none"; }}
  }}
}});
function go(decision, criterion) {{
  window.location = "/decide?decision=" + decision + "&criterion=" + criterion;
}}
</script>"""


def serve(
    sample_path: pathlib.Path, out_path: pathlib.Path, stage: Stage, port: int
) -> None:
    """Run the screening server until the queue is empty."""
    total = len(json.loads(pathlib.Path(sample_path).read_text(encoding="utf-8")))
    started = time.monotonic()
    state: dict[str, Any] = {"queue": load_queue(sample_path, out_path)}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # noqa: A003 - silence per-request logging
            return

        def _send(self, body: str, status: int = 200) -> None:
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802 - stdlib naming
            url = urlparse(self.path)

            if url.path == "/decide":
                params = parse_qs(url.query)
                decision = params["decision"][0]
                criterion = params.get("criterion", [""])[0] or None
                record = state["queue"][0]
                record_decision(out_path, record, decision, criterion, stage)
                state["queue"] = state["queue"][1:]
                self.send_response(303)
                self.send_header("Location", "/")
                self.end_headers()
                return

            if not state["queue"]:
                self._send(
                    "<!doctype html><meta charset='utf-8'>"
                    f"<p style='font:16px system-ui;margin:3rem'>All {total} records "
                    f"screened. Decisions are in <code>{html.escape(str(out_path))}</code>.</p>"
                )
                return

            done = total - len(state["queue"])
            self._send(build_page(
                state["queue"][0], done + 1, total, time.monotonic() - started
            ))

    print(f"Screening {len(state['queue'])} of {total} records.")
    print(f"Open http://127.0.0.1:{port}/  —  keys: i / e / u, then 1-7 on exclude")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Human title/abstract screening")
    parser.add_argument("--sample", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument(
        "--stage", choices=["calibration", "screening", "validation"], required=True
    )
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    serve(args.sample, args.out, args.stage, args.port)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_screen_app.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add egm/pipeline/screen_app.py egm/tests/test_screen_app.py
git commit -m "feat: add local keyboard-driven human screening app

One record per screen, keys i/e/u then 1-7 for the exclusion criterion.
Each decision is appended and fsynced before the next record renders:
1,300 judgements are irreplaceable and a buffered write is a lost
afternoon. Resumes at the first unscreened record.

Blindness is structural — the module never loads AI decisions, and a
test asserts the source contains no path by which one could reach the
page.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 7: Sample drawing and the runbook

**Files:**
- Create: `egm/pipeline/draw_sample.py`
- Create: `egm/screening/RUNBOOK.md`
- Test: `egm/tests/test_draw_sample.py`

**Interfaces:**
- Consumes: `sampling.stratified_sample`, `screen_schema.read_decisions`
- Produces:
  - `draw_calibration(corpus_path, out_path, n=300, seed=...) -> dict[str, int]`
  - `draw_validation(corpus_path, decisions_path, out_path, per_stratum, seed) -> dict[str, int]`
  - `stratum_sizes(decisions_path) -> dict[str, int]`

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_draw_sample.py`:

```python
"""Drawing the two registered samples."""
import json

import pytest

from pipeline.draw_sample import draw_calibration, draw_validation, stratum_sizes
from pipeline.screen_schema import ScreeningDecision, append_decision


def _corpus(tmp_path, n=1000):
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps({"manifest": {"record_count": n}, "records": [
        {"record_id": f"egm-{i:06d}", "pmid": str(i), "title": f"T{i}",
         "abstract": f"A{i}", "year": 2020, "journal": "J"} for i in range(n)
    ]}), encoding="utf-8")
    return path


def test_calibration_draw_is_the_registered_size(tmp_path):
    out = tmp_path / "cal.json"
    counts = draw_calibration(_corpus(tmp_path), out, n=300, seed=20260913)
    assert counts["drawn"] == 300
    records = json.loads(out.read_text(encoding="utf-8"))
    assert len({r["record_id"] for r in records}) == 300


def test_calibration_draw_is_reproducible_from_the_seed(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    corpus = _corpus(tmp_path)
    draw_calibration(corpus, a, n=300, seed=20260913)
    draw_calibration(corpus, b, n=300, seed=20260913)
    assert a.read_text(encoding="utf-8") == b.read_text(encoding="utf-8")


def test_different_seed_draws_a_different_sample(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    corpus = _corpus(tmp_path)
    draw_calibration(corpus, a, n=300, seed=1)
    draw_calibration(corpus, b, n=300, seed=2)
    assert a.read_text(encoding="utf-8") != b.read_text(encoding="utf-8")


def test_refuses_to_overwrite_an_existing_sample(tmp_path):
    """A redrawn sample would silently invalidate screening already done."""
    out = tmp_path / "cal.json"
    corpus = _corpus(tmp_path)
    draw_calibration(corpus, out, n=300, seed=1)
    with pytest.raises(FileExistsError):
        draw_calibration(corpus, out, n=300, seed=2)


def _ai_exclusion(path, record_id, confidence):
    append_decision(path, ScreeningDecision(
        record_id=record_id, pmid=record_id.split("-")[1], decision="exclude",
        criterion="not_primary", confidence=confidence, reason="r", screener="ai",
        model_id="claude-opus-5", prompt_sha256="a" * 64, stage="screening",
        decided_at="2026-09-13T10:00:00Z", supersedes=None,
    ))


def test_stratum_sizes_counts_exclusions_by_confidence(tmp_path):
    decisions = tmp_path / "d.jsonl"
    for i in range(10):
        _ai_exclusion(decisions, f"egm-{i}", 0.2)
    for i in range(10, 40):
        _ai_exclusion(decisions, f"egm-{i}", 0.95)

    assert stratum_sizes(decisions) == {"low": 10, "mid": 0, "high": 30}


def test_validation_draw_oversamples_low_confidence(tmp_path):
    corpus, decisions = _corpus(tmp_path), tmp_path / "d.jsonl"
    for i in range(100):
        _ai_exclusion(decisions, f"egm-{i:06d}", 0.2)
    for i in range(100, 900):
        _ai_exclusion(decisions, f"egm-{i:06d}", 0.95)

    out = tmp_path / "val.json"
    counts = draw_validation(
        corpus, decisions, out, {"low": 50, "mid": 0, "high": 50}, seed=20260913
    )

    assert counts["drawn"] == 100
    records = json.loads(out.read_text(encoding="utf-8"))
    assert len(records) == 100


def test_validation_draw_raises_when_a_stratum_is_too_small(tmp_path):
    corpus, decisions = _corpus(tmp_path), tmp_path / "d.jsonl"
    for i in range(5):
        _ai_exclusion(decisions, f"egm-{i:06d}", 0.2)

    with pytest.raises(ValueError, match="only 5 available"):
        draw_validation(
            corpus, decisions, tmp_path / "v.json", {"low": 50}, seed=1
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_draw_sample.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.draw_sample'`

- [ ] **Step 3: Write the implementation**

Create `egm/pipeline/draw_sample.py`:

```python
"""Draw the two registered samples.

Both draws are seeded and reproducible, which the registration commits to: a
reader must be able to redraw the same sample from the published seed and
check the reported statistics.
"""
import argparse
import json
import pathlib
from collections import defaultdict
from typing import Any

from pipeline.recall import STRATUM_BOUNDARIES, stratum_of
from pipeline.sampling import stratified_sample
from pipeline.screen_schema import read_decisions


def _load_records(corpus_path: pathlib.Path) -> list[dict[str, Any]]:
    payload = json.loads(pathlib.Path(corpus_path).read_text(encoding="utf-8"))
    return payload["records"]


def _write(out_path: pathlib.Path, records: list[dict[str, Any]]) -> None:
    out_path = pathlib.Path(out_path)
    if out_path.exists():
        raise FileExistsError(
            f"{out_path} exists. Redrawing would invalidate any screening "
            "already done against the current sample; draw to a new path and "
            "record why in the amendments log."
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, indent=2), encoding="utf-8")


def draw_calibration(
    corpus_path: pathlib.Path,
    out_path: pathlib.Path,
    n: int = 300,
    seed: int = 20260913,
) -> dict[str, int]:
    """Draw the calibration sample: n records at random from the corpus."""
    records = _load_records(corpus_path)
    drawn = stratified_sample(
        records, ["corpus"] * len(records), {"corpus": n}, seed=seed
    )
    _write(out_path, drawn)
    return {"population": len(records), "drawn": len(drawn), "seed": seed}


def stratum_sizes(decisions_path: pathlib.Path) -> dict[str, int]:
    """Count AI exclusions in each confidence stratum."""
    sizes = {name: 0 for name, _ in STRATUM_BOUNDARIES}
    for decision in read_decisions(decisions_path):
        if decision.screener == "ai" and decision.decision == "exclude":
            sizes[stratum_of(decision.confidence)] += 1
    return sizes


def draw_validation(
    corpus_path: pathlib.Path,
    decisions_path: pathlib.Path,
    out_path: pathlib.Path,
    per_stratum: dict[str, int],
    seed: int,
) -> dict[str, int]:
    """Draw the validation sample from AI exclusions, stratified by confidence."""
    by_id = {r["record_id"]: r for r in _load_records(corpus_path)}

    excluded: list[dict[str, Any]] = []
    strata: list[str] = []
    for decision in read_decisions(decisions_path):
        if decision.screener != "ai" or decision.decision != "exclude":
            continue
        record = by_id.get(decision.record_id)
        if record is None:
            raise ValueError(
                f"decision log references {decision.record_id}, absent from the corpus"
            )
        excluded.append(record)
        strata.append(stratum_of(decision.confidence))

    drawn = stratified_sample(excluded, strata, per_stratum, seed=seed)
    _write(out_path, drawn)

    counts = defaultdict(int)
    for stratum in strata:
        counts[stratum] += 1
    return {
        "excluded_population": len(excluded),
        "drawn": len(drawn),
        "seed": seed,
        **{f"population_{k}": v for k, v in counts.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Draw a registered sample")
    sub = parser.add_subparsers(dest="which", required=True)

    cal = sub.add_parser("calibration")
    cal.add_argument("--corpus", type=pathlib.Path, required=True)
    cal.add_argument("--out", type=pathlib.Path, required=True)
    cal.add_argument("--n", type=int, default=300)
    cal.add_argument("--seed", type=int, default=20260913)

    val = sub.add_parser("validation")
    val.add_argument("--corpus", type=pathlib.Path, required=True)
    val.add_argument("--decisions", type=pathlib.Path, required=True)
    val.add_argument("--out", type=pathlib.Path, required=True)
    val.add_argument("--low", type=int, default=500)
    val.add_argument("--mid", type=int, default=300)
    val.add_argument("--high", type=int, default=200)
    val.add_argument("--seed", type=int, default=20260913)

    args = parser.parse_args()
    if args.which == "calibration":
        counts = draw_calibration(args.corpus, args.out, args.n, args.seed)
    else:
        counts = draw_validation(
            args.corpus, args.decisions, args.out,
            {"low": args.low, "mid": args.mid, "high": args.high}, args.seed,
        )
    for key, value in counts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_draw_sample.py -v`
Expected: 7 passed

- [ ] **Step 5: Write the runbook**

Create `egm/screening/RUNBOOK.md`:

```markdown
# Screening runbook

Execution sequence for the registered screening procedure (OSF 3xtf2).
Each step's artefacts are committed before the next begins.

**Prerequisite:** `ANTHROPIC_API_KEY` exported, or `ant auth login` completed.
The key is read from the environment and never written to the repository.

## 1. Draw the calibration sample

    cd egm
    python -m pipeline.draw_sample calibration \
      --corpus search/raw/pubmed_corpus_with_abstracts.json \
      --out screening/calibration_300.json

Records the seed. Commit the sample.

## 2. Screen it blind

    python -m pipeline.screen_app \
      --sample screening/calibration_300.json \
      --out screening/human_calibration.jsonl \
      --stage calibration

Open http://127.0.0.1:8765/. Keys: `i` include, `e` exclude then `1`-`7`,
`u` unclear. Resumable — stop and restart freely. Roughly 1.5-2.5 hours.

**Do not run step 3 first.** Screening after seeing AI decisions is not blind,
and the registration commits to blind calibration.

## 3. Screen the same sample with each candidate model

    python -m pipeline.run_screening \
      --sample screening/calibration_300.json \
      --model claude-opus-5 \
      --out screening/ai_calibration_opus5.jsonl \
      --usage screening/usage_calibration_opus5.jsonl \
      --stage calibration

Repeat with `claude-haiku-4-5`. Expected cost: ~$1.83 and ~$0.37.
Check the usage log for actual token spend — Opus 5 runs adaptive thinking
and thinking bills as output, so the full-run projection comes from here, not
from an estimate.

## 4. Compute agreement and inspect disagreements

    python -m pipeline.report_agreement \
      --human screening/human_calibration.jsonl \
      --ai screening/ai_calibration_opus5.jsonl \
      --out screening/agreement_opus5.json

Read every disagreement. Where one reveals genuine ambiguity, revise — and
note which kind of revision it is:

- **Prompt wording only:** the AI re-screens the same 300. Your decisions stand.
- **Criteria changed:** draw a FRESH 300 with a new seed and screen it blind
  again. Your earlier decisions were made under criteria that no longer apply,
  and you have now seen the disagreements, so a re-screen would not be blind.

Record every round — seed, kappa, what was revised — in
`egm/protocol/amendments.md`.

## 5. Gate

Proceed only when kappa >= 0.75. Screen the full corpus with whichever model
has the better kappa. If the gate cannot be met after revision, the registered
contingency applies: narrow to the exposure arm (4,029 records) as a recorded
amendment.

## 6. Screen the corpus

    python -m pipeline.run_screening \
      --sample search/raw/pubmed_corpus_with_abstracts.json \
      --model <selected> \
      --out screening/screening_decisions.jsonl \
      --usage screening/usage_screening.jsonl \
      --stage screening

Resumable; interrupt freely. Route every `unclear` to yourself before
proceeding.

## 7. Draw and screen the validation sample

    python -m pipeline.draw_sample validation \
      --corpus search/raw/pubmed_corpus_with_abstracts.json \
      --decisions screening/screening_decisions.jsonl \
      --out screening/validation_1000.json

    python -m pipeline.screen_app \
      --sample screening/validation_1000.json \
      --out screening/human_validation.jsonl \
      --stage validation

Roughly 5-8 hours. This is the step that produces the published recall figure.

## 8. Compute recall

    python -m pipeline.report_recall \
      --human screening/human_validation.jsonl \
      --ai screening/screening_decisions.jsonl \
      --out screening/recall.json

Report whatever it says. The registration commits to publishing a poor recall
estimate rather than re-running until it improves; `recall.py` has no parameter
that would allow otherwise.
```

- [ ] **Step 6: Run the full suite**

Run: `cd egm && python -m pytest tests/ -v`
Expected: 189 passed (121 existing + 68 from tasks 1-7)

- [ ] **Step 7: Commit**

```bash
git add egm/pipeline/draw_sample.py egm/tests/test_draw_sample.py egm/screening/RUNBOOK.md
git commit -m "feat: add sample drawing and the screening runbook

Both registered draws are seeded and reproducible. Drawing refuses to
overwrite an existing sample, because a redraw would silently invalidate
screening already done against the current one.

The runbook records the execution sequence, including the distinction
that matters most: a prompt-wording change reuses the calibration
sample, a criteria change forces a fresh one, because a re-screen after
seeing the disagreements is not blind.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 8: The three CLI entry points

The runbook references `run_screening`, `report_agreement` and `report_recall`. They are thin wrappers, grouped into one task because none carries its own meaningful test cycle alone.

**Files:**
- Create: `egm/pipeline/run_screening.py`
- Create: `egm/pipeline/report_agreement.py`
- Create: `egm/pipeline/report_recall.py`
- Test: `egm/tests/test_cli_entrypoints.py`

**Interfaces:**
- Consumes: `ai_screener.screen_sample`, `agreement.compare`, `recall.validate_recall`, `draw_sample.stratum_sizes`
- Produces: three `main()` functions and three importable `run(...)` helpers

- [ ] **Step 1: Write the failing test**

Create `egm/tests/test_cli_entrypoints.py`:

```python
"""The three CLI wrappers. Thin, but they must not swallow failures."""
import json

import pytest

from pipeline import report_agreement, report_recall, run_screening
from pipeline.screen_schema import ScreeningDecision, append_decision


def _ai(path, record_id, decision, confidence, criterion=None):
    append_decision(path, ScreeningDecision(
        record_id=record_id, pmid=record_id.split("-")[1], decision=decision,
        criterion=criterion, confidence=confidence, reason="r", screener="ai",
        model_id="claude-opus-5", prompt_sha256="a" * 64, stage="screening",
        decided_at="2026-09-13T10:00:00Z", supersedes=None,
    ))


def _human(path, record_id, decision, criterion=None, stage="validation"):
    append_decision(path, ScreeningDecision(
        record_id=record_id, pmid=record_id.split("-")[1], decision=decision,
        criterion=criterion, confidence=None, reason=None, screener="human",
        model_id=None, prompt_sha256=None, stage=stage,
        decided_at="2026-09-13T10:00:00Z", supersedes=None,
    ))


def test_run_screening_loads_records_from_a_corpus_payload(tmp_path, mocker):
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps({"manifest": {}, "records": [
        {"record_id": "egm-1", "pmid": "1", "title": "T", "abstract": "A",
         "year": 2020, "journal": "J"}]}), encoding="utf-8")

    screen = mocker.patch.object(
        run_screening.ai_screener, "screen_sample",
        return_value={"total": 1, "screened": 1, "skipped": 0},
    )
    mocker.patch.object(run_screening.anthropic, "Anthropic")

    run_screening.run(corpus, "claude-opus-5", tmp_path / "d.jsonl",
                      tmp_path / "u.jsonl", "screening")

    assert screen.call_args.args[1][0]["record_id"] == "egm-1"


def test_run_screening_accepts_a_bare_list_sample(tmp_path, mocker):
    """Drawn samples are a bare list; the corpus is {manifest, records}."""
    sample = tmp_path / "sample.json"
    sample.write_text(json.dumps([
        {"record_id": "egm-9", "pmid": "9", "title": "T", "abstract": "A",
         "year": 2020, "journal": "J"}]), encoding="utf-8")

    screen = mocker.patch.object(
        run_screening.ai_screener, "screen_sample",
        return_value={"total": 1, "screened": 1, "skipped": 0},
    )
    mocker.patch.object(run_screening.anthropic, "Anthropic")

    run_screening.run(sample, "claude-opus-5", tmp_path / "d.jsonl",
                      tmp_path / "u.jsonl", "calibration")

    assert screen.call_args.args[1][0]["record_id"] == "egm-9"


def test_run_screening_propagates_a_screener_error(tmp_path, mocker):
    """A failed run must fail, not report a partial success."""
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps({"records": [
        {"record_id": "egm-1", "pmid": "1", "title": "T", "abstract": "A",
         "year": 2020, "journal": "J"}]}), encoding="utf-8")

    mocker.patch.object(run_screening.anthropic, "Anthropic")
    mocker.patch.object(
        run_screening.ai_screener, "screen_sample",
        side_effect=run_screening.ai_screener.ScreenerError("boom"),
    )

    with pytest.raises(run_screening.ai_screener.ScreenerError):
        run_screening.run(corpus, "claude-opus-5", tmp_path / "d.jsonl",
                          tmp_path / "u.jsonl", "screening")


def test_report_agreement_writes_a_json_report(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    for n in range(20):
        rid = f"egm-{n}"
        decision = "include" if n < 8 else "exclude"
        criterion = None if n < 8 else "not_primary"
        _human(human_p, rid, decision, criterion, stage="calibration")
        _ai(ai_p, rid, decision, 0.9, criterion)

    out = tmp_path / "agreement.json"
    report = report_agreement.run(human_p, ai_p, out, gate=0.75)

    assert report.gate_met is True
    assert json.loads(out.read_text(encoding="utf-8"))["kappa"] == 1.0


def test_report_recall_writes_a_json_report(tmp_path):
    human_p, ai_p = tmp_path / "h.jsonl", tmp_path / "a.jsonl"
    for n in range(50):
        rid = f"egm-{n}"
        _ai(ai_p, rid, "exclude", 0.9, "not_primary")
        _human(human_p, rid, "exclude", "not_primary")

    out = tmp_path / "recall.json"
    report = report_recall.run(human_p, ai_p, out)

    assert report.false_negatives == 0
    assert json.loads(out.read_text(encoding="utf-8"))["sensitivity"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd egm && python -m pytest tests/test_cli_entrypoints.py -v`
Expected: FAIL — `ImportError: cannot import name 'report_agreement'`

- [ ] **Step 3: Write the three wrappers**

Create `egm/pipeline/run_screening.py`:

```python
"""CLI: screen a sample or the full corpus with a named model."""
import argparse
import json
import pathlib
from typing import Any

import anthropic

from pipeline import ai_screener


def _load(path: pathlib.Path) -> list[dict[str, Any]]:
    """Accept either a corpus payload ({manifest, records}) or a bare list."""
    payload = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return payload["records"] if isinstance(payload, dict) else payload


def run(
    sample_path: pathlib.Path,
    model_id: str,
    out_path: pathlib.Path,
    usage_path: pathlib.Path,
    stage: str,
) -> dict[str, int]:
    client = anthropic.Anthropic()
    return ai_screener.screen_sample(
        client, _load(sample_path), model_id, out_path, usage_path, stage
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="AI title/abstract screening")
    parser.add_argument("--sample", type=pathlib.Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--usage", type=pathlib.Path, required=True)
    parser.add_argument(
        "--stage", choices=["calibration", "screening", "validation"], required=True
    )
    args = parser.parse_args()

    counts = run(args.sample, args.model, args.out, args.usage, args.stage)
    for key, value in counts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
```

Create `egm/pipeline/report_agreement.py`:

```python
"""CLI: compute Cohen's kappa between a human and an AI decision log."""
import argparse
import pathlib

from pipeline.agreement import AgreementReport, compare


def run(
    human_path: pathlib.Path,
    ai_path: pathlib.Path,
    out_path: pathlib.Path,
    gate: float = 0.75,
) -> AgreementReport:
    report = compare(human_path, ai_path, gate=gate)
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Human vs AI screening agreement")
    parser.add_argument("--human", type=pathlib.Path, required=True)
    parser.add_argument("--ai", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--gate", type=float, default=0.75)
    args = parser.parse_args()

    report = run(args.human, args.ai, args.out, args.gate)
    print(f"n:        {report.n}")
    print(f"kappa:    {report.kappa:.3f} "
          f"(95% CI {report.kappa_ci_low:.3f} to {report.kappa_ci_high:.3f})")
    print(f"agree:    {report.observed_agreement:.1%}")
    print(f"disagree: {len(report.disagreements)}")
    print(f"GATE {report.gate}: {'MET' if report.gate_met else 'NOT MET'}")


if __name__ == "__main__":
    main()
```

Create `egm/pipeline/report_recall.py`:

```python
"""CLI: estimate screening recall from hand-screened AI exclusions."""
import argparse
import pathlib

from pipeline.draw_sample import stratum_sizes
from pipeline.recall import RecallReport, validate_recall


def run(
    human_path: pathlib.Path,
    ai_path: pathlib.Path,
    out_path: pathlib.Path,
    confidence: float = 0.95,
) -> RecallReport:
    report = validate_recall(
        human_path, ai_path, stratum_sizes(ai_path), confidence=confidence
    )
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Screening recall validation")
    parser.add_argument("--human", type=pathlib.Path, required=True)
    parser.add_argument("--ai", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--confidence", type=float, default=0.95)
    args = parser.parse_args()

    report = run(args.human, args.ai, args.out, args.confidence)
    print(f"validated:        {report.n_validated}")
    print(f"false negatives:  {report.false_negatives}")
    print(f"sensitivity:      {report.sensitivity:.4f} "
          f"(95% CI {report.sensitivity_ci_low:.4f} to {report.sensitivity_ci_high:.4f})")
    print(f"FN rate:          {report.fn_rate:.4%} "
          f"(upper bound {report.fn_rate_ci_high:.4%})")
    print(f"weighted FN rate: {report.weighted_fn_rate:.4%}")
    print(f"implied missed:   {report.implied_missed_low:.0f} to "
          f"{report.implied_missed_high:.0f} of {report.total_excluded} exclusions")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd egm && python -m pytest tests/test_cli_entrypoints.py -v`
Expected: 5 passed

- [ ] **Step 5: Run the full suite**

Run: `cd egm && python -m pytest tests/ -v`
Expected: 194 passed

- [ ] **Step 6: Commit**

```bash
git add egm/pipeline/run_screening.py egm/pipeline/report_agreement.py egm/pipeline/report_recall.py egm/tests/test_cli_entrypoints.py
git commit -m "feat: add the three screening CLI entry points

Thin wrappers over screen_sample, compare and validate_recall, matching
the commands in the runbook. run_screening accepts either a corpus
payload or a bare drawn sample, and propagates ScreenerError rather than
reporting a partial success.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Plan Completion Criteria

- [ ] `cd egm && python -m pytest tests/ -v` — all pass
- [ ] `clopper_pearson(0, 1000)` reproduces the registered 0.368% upper bound
- [ ] `egm/screening/RUNBOOK.md` exists and its commands match the implemented CLIs
- [ ] The RNG AST scan still passes with the new modules present
- [ ] No API key appears in any committed file: `git log -p | grep -ci "sk-ant" ` returns 0

## Not in this plan

| Deferred | Why |
|---|---|
| Running the calibration, screening and validation | Requires an API key and ~8 hours of the investigator's reading; the runbook covers the sequence |
| Batch API path for the full run | Decided when the run is scheduled; streaming suits the iterative calibration, batch halves the cost of the one-off corpus run |
| Full-text screening and coding | Next plan, gated on this one's recall estimate |
| Map construction, meta-analysis | Later plans |
