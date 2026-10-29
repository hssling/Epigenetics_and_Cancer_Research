# EGM Screening: Calibration, AI Screening and Recall Validation

**Design specification (Plan B)**
**Date:** 2026-09-13
**Investigator:** Dr. Siddalingaiah H S
**Implements:** OSF registration [3xtf2](https://osf.io/3xtf2), DOI `10.17605/OSF.IO/3XTF2`
**Predecessor:** [2026-09-13-epigenetics-evidence-gap-map-design.md](2026-09-13-epigenetics-evidence-gap-map-design.md) (Plan A, delivered)

---

## 1. What this builds

Plan A delivered a registered protocol and a corpus of 9,088 deduplicated PubMed
records, 9,083 of which carry abstracts. Plan B screens that corpus down to the
set of eligible studies, and measures how reliably it did so.

Three deliverables:

1. **A calibrated screener.** Agreement between the investigator and an AI
   screener on a 300-record sample, reported as Cohen's kappa, gating further
   work at kappa >= 0.75.
2. **A screened corpus.** Every record classified include / exclude / unclear,
   with the criterion invoked and a confidence value, in an append-only log.
3. **A measured recall estimate.** Sensitivity with an exact confidence
   interval, from 1,000 AI-excluded records hand-screened blind.

Deliverable 3 is the one that matters most. It is what converts "we screened
9,088 records with AI assistance" from an assertion into a quantity a reader can
weigh.

## 2. Constraints fixed by the registration

These are public commitments at `osf.io/3xtf2`. Changing any of them requires a
dated amendment recorded in `egm/protocol/amendments.md` **before** the change is
acted on. They are inputs to this design, not open questions.

| Commitment | Source |
|---|---|
| Four stages: calibration -> AI screening -> validation -> full text | Screening stages |
| 300-record calibration, human screens blind, kappa >= 0.75 to proceed | Screening stages, Screening reliability |
| Validation targets AI-**excludes**, 1,000 records, confidence-stratified | Sampling and sample size |
| Sensitivity reported with exact (Clopper-Pearson) 95% CI, plus specificity and full confusion matrix | Screening reliability |
| A poor recall estimate is reported, not re-run until favourable | Screening reliability |
| AI returns decision + criterion invoked + confidence | Screener instructions |
| `unclear` routes to the investigator | Screening stages |
| Seven ordered exclusion criteria | Used exclusion criteria |
| Uncertainty at title/abstract resolves toward inclusion | Used exclusion criteria |
| Decisions append-only; a changed decision is appended with its reason | Data management and sharing |
| Prompts, model ID and run dates recorded as dated artefacts | Screener instructions |
| Instructions frozen after calibration; later changes force re-screening | Screener instructions |
| Contingency: if kappa >= 0.75 is unreachable, narrow to the exposure arm (4,029 records) | Screening stages |

## 3. Architecture

```
corpus_with_abstracts.json (9,088)
      |
      |-- stratified_sample(seed) --> calibration_300.json
      |            |
      |     +------+-------+
      |     v              v
      |  screen_app     ai_screener x2 (claude-opus-5, claude-haiku-4-5)
      |  (human, blind)
      |     |              |
      |     +------+-------+
      |            v
      |      agreement.py --> kappa per model --> GATE kappa >= 0.75
      |                                              |
      |-- ai_screener (selected model, 9,088) <------+
                   |
                   |--> screening_decisions.jsonl
                   v
           stratified_sample by confidence (seed) --> validation_1000.json
                   |
                   v
             screen_app (human, blind) --> recall.py
                   |
                   +--> sensitivity + Clopper-Pearson CI + confusion matrix
```

Each arrow is a file. No stage holds state in memory across a run, so every stage
is independently resumable and independently auditable.

### 3.1 File structure

| Path | Responsibility |
|---|---|
| `egm/pipeline/screen_schema.py` | `ScreeningDecision`, `Criterion`, `Decision` — the record written for every judgement, human or AI |
| `egm/pipeline/ai_screener.py` | Anthropic API client: frozen prompt, structured output, prompt caching, resumable batch loop |
| `egm/pipeline/screen_app.py` | Local HTTP server + single-page keyboard UI for human screening |
| `egm/pipeline/agreement.py` | Cohen's kappa with confidence interval; disagreement listing |
| `egm/pipeline/recall.py` | Sensitivity, specificity, Clopper-Pearson intervals, confusion matrix |
| `egm/pipeline/prompts/screening_v1.md` | The frozen screening instructions |
| `egm/screening/` | Artefacts: samples, decision logs, prompt snapshots, agreement and recall reports |
| `egm/tests/test_screen_schema.py`, `test_ai_screener.py`, `test_screen_app.py`, `test_agreement.py`, `test_recall.py` | Tests |

## 4. The decision record

One schema for every judgement, whoever made it. Written append-only as JSONL.

| Field | Type | Notes |
|---|---|---|
| `record_id`, `pmid` | str | identifies the screened record |
| `decision` | `include` / `exclude` / `unclear` | |
| `criterion` | `Optional[Criterion]` | required when `decision == "exclude"`; must be `None` otherwise |
| `confidence` | `Optional[float]` | 0–1; required for AI decisions, `None` for human |
| `reason` | `Optional[str]` | free text; AI supplies it, human optional |
| `screener` | `human` / `ai` | |
| `model_id` | `Optional[str]` | required when `screener == "ai"` (e.g. `claude-opus-5`) |
| `prompt_sha256` | `Optional[str]` | required when `screener == "ai"` |
| `stage` | `calibration` / `screening` / `validation` | |
| `decided_at` | str | UTC, `%Y-%m-%dT%H:%M:%SZ` |
| `supersedes` | `Optional[str]` | set when this decision replaces an earlier one; the earlier line is never edited |

The cross-field rules are enforced by the schema, not by convention: an exclusion
without a criterion, or an AI decision without a model ID and prompt hash, cannot
be constructed. This continues Plan A's approach of putting integrity
constraints in the type rather than in a later check.

`Criterion` is the registered ordered list:

1. `not_human` — animal, in vitro, or cell-line only
2. `not_primary` — review, meta-analysis, editorial, comment, letter, abstract without data
3. `no_measured_marker` — no directly measured epigenetic marker
4. `ncrna_only` — non-coding RNA as the sole marker
5. `no_approach_link` — no modifiable exposure/intervention and no clinical or public health decision
6. `out_of_window` — outside 2015–2026
7. `not_english`

## 5. The screening app

A local `http.server` serving one page; no framework, no build step, no network
egress. Run as `python -m pipeline.screen_app --sample <file> --out <jsonl>`.

**Interaction.** One record per screen: title, abstract, journal, year. `i`
include, `e` exclude, `u` unclear. On `e`, keys `1`–`7` select the criterion. `b`
goes back one record to amend the previous decision (which appends a new line
with `supersedes` set, never edits the old one). Progress and running
time-per-record are shown, because 1,300 judgements is a marathon and knowing the
pace makes it manageable.

**Durability.** Each decision is appended and `fsync`ed **before** the next record
renders. A crash, a closed laptop or a power cut costs at most the record on
screen. On restart the app reads the existing JSONL and resumes at the first
unscreened record.

**Blindness.** The server never loads AI decisions. The registration's
blind-screening commitment is therefore structural — there is no code path by
which an AI decision could reach the page — rather than a matter of discipline.

## 6. The AI screener

`client.messages.parse()` against a JSON schema returning `{decision, criterion,
confidence, reason}`. One record per request. Prompt caching on the frozen system
prompt, which is the difference between $108 and $55 across the corpus.

**Prompt provenance.** The instructions live in
`egm/pipeline/prompts/screening_v1.md`, are SHA-256 hashed at load, and the hash
is written into every decision record. A decision therefore traces to the exact
text that produced it, and a modified prompt is detectable rather than asserted.
After calibration the file is frozen; a change requires a protocol amendment and
re-screening of everything decided under the earlier version.

**Resumability.** The run appends as it goes and skips `record_id`s already
present in the output. A 9,088-record run interrupted at any point resumes
without re-spending on completed records.

**Failure handling.** Inherits Plan A's discipline: a record that fails after
retries raises rather than being recorded as an exclusion. A screening run that
dies loudly is recoverable; one that silently converts API failures into
exclusions is not, and would corrupt both the PRISMA count and the recall
estimate.

### 6.1 Reproducibility: what is and is not claimed

The registration states that screening decisions are "reproducible and
auditable". This design honours the second word fully and the first in a specific,
limited sense that must be stated plainly in the manuscript rather than left to
implication.

**Not reproducible:** re-running the screener will not return identical
decisions. Language model sampling is not deterministic, and `temperature` has
been removed from the current models entirely, so no setting would make it so.

**Reproducible:** the sample selection (seeded), the frozen prompt (hashed and
published), the pinned model identifier, the run dates, and the complete decision
log. A reader can verify what was asked, of which model, about which records, and
what came back — and can re-run the same prompt against the same records to see
how far a second pass diverges.

The methods text must say "auditable, with the prompt, model and full decision log
published" and must not say or imply bit-reproducibility. Measuring the divergence
of a second pass over the calibration set is cheap (~$2) and would be a more
informative thing to report than a reproducibility claim that cannot hold.

## 7. Calibration and the gate

1. Draw 300 records with `stratified_sample`, seed recorded in the repository.
2. The investigator screens all 300 blind in `screen_app`.
3. Each candidate model screens the same 300 via `ai_screener`.
4. `agreement.py` computes Cohen's kappa with a confidence interval per model, a
   per-criterion agreement breakdown, and a listing of every disagreement.
5. The investigator inspects the disagreements and revises the prompt, or the
   criteria, where a disagreement reveals genuine ambiguity rather than error.
   Revisions are recorded; the human decisions are **not** revised to match the AI.
6. Repeat — but what repeats depends on what changed, and the distinction matters:

   - **Prompt wording only** (the criteria themselves unchanged): the AI
     re-screens the same 300 records under the revised prompt. The investigator's
     decisions stand and are not re-made — they were reached under the same
     criteria and remain valid. kappa is recomputed against them.

   - **Criteria changed** (a definition altered, a boundary case reclassified):
     a **fresh 300-record sample is drawn**, with a new recorded seed, and the
     investigator screens it blind under the revised criteria. The previous
     round's kappa is reported but superseded.

   The second case cannot reuse the original sample. Once the investigator has
   seen the disagreements, a re-screen of those records is no longer blind, and
   the original decisions were made against criteria that no longer apply.
   Recomputing kappa against them after changing the criteria would measure
   agreement with a superseded standard while presenting it as agreement with the
   current one.

   The cost of a fresh round is $1.83 in API spend and roughly 1.5 hours of
   screening. That is the honest price of changing the criteria mid-calibration,
   and it is a reason to get the criteria right before starting rather than a
   reason to avoid recording the change.

   Every round is recorded — its seed, its kappa, and what was revised — so the
   published calibration history shows how many rounds it took and what moved.

**Model selection.** Two models are calibrated: `claude-opus-5` and
`claude-haiku-4-5`. Measured cost across the whole corpus is $55.34 and $11.07
respectively with prompt caching, so the ~$44 spread does not discriminate; a
single calibration round costs $1.83 and $0.37. The model that screens the corpus
is the one with the better kappa on identical inputs, chosen empirically rather
than argued. The comparison is reported in the methods.

**If the gate cannot be met** after prompt revision, the registered contingency
applies: narrow scope to the exposure arm of the search (4,029 records), which is
feasible for single-human screening. That is a protocol amendment, recorded before
it is acted on.

## 8. Recall validation

1. Partition AI-excluded records into confidence strata.
2. Draw 1,000 with `stratified_sample`, over-sampling low-confidence exclusions,
   seed recorded.
3. The investigator screens all 1,000 blind.
4. `recall.py` reports sensitivity with an exact (Clopper-Pearson) 95% interval,
   specificity, the full confusion matrix, and the implied upper bound on eligible
   studies missed across the whole exclusion set.

Stratification means the raw sample proportions are not the population
proportions, so `recall.py` reports both the unweighted sample statistics and the
stratum-weighted population estimate, and labels which is which. Reporting a
stratified sample's raw rate as if it were the population rate would **overstate**
the false-negative rate, precisely because low-confidence records — the stratum
where a missed study is most likely to be hiding — are deliberately over-sampled.
The sample is therefore enriched for error relative to the population, and its
raw rate is biased upward.

That direction matters and is easy to get wrong: an earlier draft of this
section asserted the opposite. The implemented weighting was checked against
it — on the same validation inputs, the raw basis implies 336.0–588.5 eligible
studies missed across the exclusion set, while the stratum-weighted estimate
implies 37.6–127.3. The raw figure is the conservative one, not the optimistic
one. Reporting only the weighted estimate would be the error to guard against;
reporting only the raw one would be alarmist. `recall.py` reports both.

**If false negatives are found**, the observed rate and its exact interval are
reported as they stand, and the sample is extended in blocks of 500. The
registration commits to this explicitly: a recall estimate that comes out poor is
reported, not re-run until it looks favourable. `recall.py` therefore has no
option to exclude a block from the calculation.

## 9. Inherited integrity rules

Plan A's rules apply unchanged, and the existing test suite enforces them across
the whole `egm/` tree:

1. No default values — a missing field is `None`, never a substituted constant.
2. Fail loud — a missing required value raises rather than being filled.
3. No RNG in the data path except `sampling.py`, which is allowlisted and now
   covered by 15 tests verified against five mutants.
4. Single source of truth — every number in the manuscript is generated from the
   decision logs at build time, never typed.

One addition specific to this plan: **an API failure is never recorded as a
screening decision.** The decision log contains judgements, not error states.

## 10. Cost

Measured against the real corpus (17,738,028 characters of title and abstract,
~488 tokens per record variable, ~1,300 token cached system prompt, ~120 tokens
output):

| Model | No caching | Prompt caching | Caching + Batch |
|---|---:|---:|---:|
| `claude-opus-5` | $108.51 | $55.34 | $27.67 |
| `claude-sonnet-5` | $43.40 | $22.14 | $11.07 |
| `claude-haiku-4-5` | $21.70 | $11.07 | $5.53 |

Calibration rounds: $1.83 (Opus 5) and $0.37 (Haiku 4.5) per 300 records.

The Batch API halves cost at the price of up to 24h latency. It suits the
single full-corpus run; it does not suit calibration, which is iterative and needs
fast turnaround. The implementation uses streaming requests for calibration and
leaves the batch path as an option for the full run, decided when the run is
scheduled.

**Prerequisite:** no `ANTHROPIC_API_KEY` and no `ant` CLI credential exists on the
machine. One must be provided before any AI screening runs. The key is read from
the environment; it is never written to the repository, and no artefact records it.

## 11. Risks and contingencies

| Risk | Mitigation |
|---|---|
| kappa >= 0.75 unreachable | Registered contingency: narrow to the exposure arm (4,029 records), as an amendment |
| Human screening fatigue over 1,300 records degrades judgement | App shows pace; screening is resumable across sessions; recall validation is itself the check on systematic human error |
| API failures mid-run | Run is resumable and skips completed records; failures raise rather than being recorded as exclusions |
| Low-confidence stratum too small to over-sample as planned | `stratified_sample` raises rather than silently returning fewer; strata boundaries set after inspecting the confidence distribution, recorded before drawing |
| Second pass diverges materially from the first | Measured on the calibration set and reported, rather than assumed away |
| Prompt drift between calibration and the full run | Prompt hash written into every decision; a mismatch is detectable in the log |
| Criteria revised mid-calibration, invalidating the human decisions already made | A criteria change forces a fresh 300-record sample rather than recomputing kappa against decisions made under superseded criteria (section 7, step 6) |

## 12. Out of scope

- Full-text screening and coding — the next plan, gated on this one
- Map construction and the nested meta-analysis — later plans
- Embase, Web of Science, CENTRAL and registry retrieval — deferred; the registration records them as not yet executed
- Any change to the registered methodology without a recorded amendment

## 13. Decision log

| Decision | Rejected alternative | Rationale |
|---|---|---|
| Scripted API client | Screening conversationally in-session | Only the scripted path gives a frozen prompt, a pinned model and a re-runnable artefact; the in-session route could not honour the registration's auditability commitment |
| Calibrate two models, select by kappa | Picking a model by argument | A calibration round costs ~$2 and the cost spread across the corpus is ~$44, so the choice can be settled empirically; the comparison is itself reportable |
| Local keyboard-driven web app | Terminal CLI; CSV round-trip; hosted artifact | 1,300 judgements make interaction cost dominant; a CSV cannot enforce valid values or immediate saves, and a terminal renders long abstracts poorly |
| Append-and-fsync per decision | Batch write at session end | The failure mode of the alternative is losing hours of irreplaceable human judgement |
| Amendments append with `supersedes` | Editing the decision in place | The registration commits to an append-only log; an edited decision destroys the audit trail |
| State the reproducibility limit explicitly | Letting "reproducible" stand unqualified | LLM sampling is non-deterministic and temperature is removed on current models; the claim cannot hold as stated, and a reviewer finding that is worse than saying it first |
| API failure raises | Recording a failed record as excluded | A failure silently converted into an exclusion corrupts both the PRISMA count and the recall estimate, and is undetectable afterwards |
| Fresh sample when criteria change; reuse when only prompt wording changes | Reusing the same 300 in all cases | After the investigator has seen the disagreements a re-screen is no longer blind, and decisions made under superseded criteria cannot measure agreement with the current ones |
| Report both unweighted and stratum-weighted recall | Reporting only one of them | Low-confidence exclusions are deliberately over-sampled, so the raw rate is not the population rate: presenting it alone **overstates** the false-negative rate (336.0-588.5 implied missed vs 37.6-127.3 weighted, on the same inputs), while presenting the weighted estimate alone hides the conservative bound |
