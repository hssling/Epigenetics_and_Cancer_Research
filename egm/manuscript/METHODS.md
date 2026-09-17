# Methods (draft)

Draft Methods section for *Epigenetic Approaches in Health and Public Health
Practice: An Evidence Gap Map*. Written to PRISMA 2020 with the PRISMA-S search
extension (`PRISMA_S_search_report.md`) and Campbell Collaboration guidance on
evidence and gap maps.

**Scope of this draft.** Sections 1-4 and 6 describe work that has been
executed. Sections 7-9 describe the registered design for stages that have not
run; they are written in the future tense and carry no results. The boundary is
marked explicitly after Section 6.

**No screening result in this document is reportable.** Title/abstract screening
is complete, but the registered Stage 0 gate — Cohen's kappa >= 0.75 between the
investigator and the model — has not been passed. `pipeline/report_screening.py`
refuses to emit PRISMA screening counts without it, and `PRISMA_flow.md` is
generated through that same gated function, so the figure withholds them too.
See `STATUS.md`.

---

## 1. Protocol and registration

The protocol was written in full, then registered prospectively with OSF
Registries before any record was screened (registration 3xtf2, DOI
10.17605/OSF.IO/3XTF2, approved 13 September 2026, public with no embargo,
CC-BY 4.0). The registered document is v1.0 of `protocol/protocol.md` and is
reproduced without alteration in the registration.

PROSPERO was considered first and is not used. PROSPERO's scope explicitly
excludes evidence and gap maps, and registering this work there would have
required describing it as something it is not. OSF Registries accepts the
Generalized Systematic Review Registration template, which accommodates a
map-plus-nested-synthesis design.

Every deviation from the registered protocol enacted since registration is
listed, dated, and given a rationale in `protocol/amendments.md`. Five have been
enacted to date: the substitution of freely accessible databases for subscription
databases the investigator cannot access (Section 2); a narrowly scoped
relaxation of the deduplication rules for preprint pairs (Section 4); two
refinements of the screening instrument between calibration rounds, which
protocol Section 5 Stage 0 explicitly anticipates (Section 6.1); and a reset of the
recall-validation confidence strata, which the design spec directs be set after
inspecting the observed distribution (Section 6.4).

Each was decided and enacted before any eligibility result existed, so none can
have been shaped by seeing which way a result came out. That ordering is recorded
in the amendments file for each entry.

## 2. Information sources

The registered protocol specified PubMed/MEDLINE, Embase, Web of Science Core
Collection and Cochrane CENTRAL, plus ClinicalTrials.gov and WHO ICTRP.

Embase and Web of Science were not searched. The sole investigator has no
institutional subscription to either, and neither offers programmatic access on
free terms. Rather than silently search fewer databases than were registered, an
amendment was filed substituting freely accessible sources, before screening
began:

| Registered | Executed |
|---|---|
| PubMed/MEDLINE | PubMed/MEDLINE, via NCBI E-utilities |
| Embase | **Europe PMC**, via the EBI REST API |
| Web of Science | *not substituted at this stage* |
| Cochrane CENTRAL | *not yet searched* |
| ClinicalTrials.gov, WHO ICTRP | *not yet searched* |

Europe PMC was searched with an explicit `NOT SRC:MED` restriction — that is,
restricted to records **not** already in MEDLINE. The reasoning is that MEDLINE
had already been searched natively, using controlled vocabulary and
publication-type filters that Europe PMC's query syntax cannot express; running a
looser translation across the same content and deduplicating would have imported
MEDLINE records that the registered strategy deliberately excludes, quietly
widening a registered search. Europe PMC's contribution here is therefore
precisely the coverage it uniquely offers: preprints, PMC-only deposits, theses
and agricultural literature.

The consequence for coverage is stated in the limitations and is not minimised:
this review has less coverage than one with full commercial database access, and
Europe PMC is not a substitute for Embase's distinct indexing of European and
pharmacological literature.

## 3. Search strategy

The PubMed strategy combines four concept blocks with Boolean `AND`: eligible
epigenetic markers (DNA methylation, histone and chromatin modification, and
epigenetic clock / DNAm age terms); human restriction; modifiable exposure **or**
clinical use; and a primary-study design filter, with reviews, meta-analyses,
editorials, comments and letters removed. It is limited to 2015-2026.

Non-coding RNA is excluded as a *sole* eligible marker. This is a scoping decision
with three stated grounds (protocol Section 3.4): ncRNA regulation is
post-transcriptional rather than a heritable chromatin state and is excluded by
strict definitions of epigenetics; including it raises the PubMed corpus from
11,965 to 21,528 records; and the additional records are predominantly mechanistic
cancer-biology studies expected to fail the eligibility test. Studies measuring
ncRNA *alongside* an eligible marker remain eligible.

Both search strings are generated by committed code rather than transcribed, so
the published strategy and the executed strategy cannot drift. Full strings,
field-tag rationale, limits, and the unmet PRESS peer-review commitment are
reported against all sixteen PRISMA-S items in `PRISMA_S_search_report.md`.

## 4. Selection of sources of evidence: identification and deduplication

Record counts at every stage, per database and per deduplication rule, are given
in `PRISMA_flow.md` and in the machine-readable
`search/prisma_counts_combined_v3.csv`.

Deduplication is automated and applied in a fixed order: exact normalised DOI,
then PMID, then fuzzy title match (rapidfuzz ratio >= 95) additionally requiring an
identical first-author surname and a compatible publication year. Two records that
each carry an identifier and disagree on it are never merged, however similar
their titles — a rule that also prevents a record carrying no identifier from
bridging two records whose identifiers conflict.

The publication-year rule was amended after the Europe PMC records were retrieved.
As registered it required exact year equality, which is correct for two journal
articles but wrong for a preprint and its own published version, since a preprint
necessarily precedes publication. A diagnostic found preprint/article pairs
sharing an identical normalised title and first author, blocked from merging
solely by the year comparison and therefore counted twice. The rule now permits a
+/-2-year window **when one record of the pair is a preprint**, and retains
exact-year matching for every other pair. The amendment is dated and recorded; the
narrower scope is deliberate, preserving the original protection where it earns
its keep.

Preprints are retained rather than excluded. The registered eligibility criteria
turn on study design, not on peer-review status, and are silent on preprints.
Consistent with the treatment of chain completeness (Section 5), peer-review
status is recorded as a coded variable so that any cell of the map can be
recomputed with preprints excluded, rather than being decided by an unregistered
exclusion applied here.

---

## 5. Eligibility criteria

Eligible studies will be primary human studies (randomised trial, non-randomised
trial, cohort, case-control, or cross-sectional), published 2015-2026 in English,
that **directly measure** an epigenetic marker — DNA methylation (global,
candidate-gene, or epigenome-wide), histone modification, chromatin state, or an
epigenetic clock / DNAm age measure — in the context either of a modifiable
exposure or intervention, or of an epigenetic measurement used to inform a
clinical or public health decision.

Animal, in vitro and cell-line-only studies are excluded, as are reviews,
editorials, comments, letters, and conference abstracts without data. Intervention
trials that assume an epigenetic mechanism without measuring a marker are
excluded, since the measured marker is the map's organising axis.

**Chain completeness is a mapped variable, not an exclusion.** Every claim in this
field is a three-link chain: exposure or intervention (A) alters an epigenetic
marker (B), which relates to a health outcome (C). Eligibility requires link B
only. Each included study will be coded A->B, B->C, or A->B->C. A->B->C studies —
the only design that can support a claim that an epigenetic approach *works* — are
expected to be rare, and quantifying that rarity is the map's central intended
finding. Filtering on chain completeness would discard the mechanistic and
prognostic literature that gives the translational gap its meaning; gap maps exist
to report absence as a result, and this is the mechanism by which this one does.

## 6. Screening

The investigator is the sole human reviewer. The design allocates human attention
to errors that are unrecoverable and uses workflow structure for errors that are
not.

### 6.1 Instrument development (executed)

The screening instrument is a frozen text whose SHA-256 is recorded with every
decision, alongside the model identifier, so that no decision can be attributed
to a prompt it was not produced under.

Two refinement rounds were run before the corpus was screened, on 300 randomly
drawn records (seeded, reproducible). Protocol Section 5 Stage 0 explicitly
provides for this ("eligibility criteria and AI prompt refined"). Each round is
recorded as a dated amendment carrying the SHA-256 of both versions.

Round 1 (`screening_v1`) exposed two structural defects. The instrument required
one of five study designs but provided no exclusion criterion for a design on
neither list, so case series, descriptive profiling series, in-silico
re-analyses and Mendelian randomisation studies could not be excluded on any
available ground. Separately, `ncrna_only` was unreachable: the instrument
directs the screener to the first applicable criterion, and `no_measured_marker`
always preceded it.

Round 2 (`screening_v2`) fixed both but introduced two of its own, each
identified independently by more than one screening run: it classified "tool
development" as an ineligible *design* when it is a *purpose*, and it contained
two mutually contradictory rules for secondary analyses of existing databases.

`screening_v3` resolves those. Refinement stopped there: the registered gate is
agreement with the **investigator**, and with no human screening there is no
anchor against which further refinement could be checked. Continuing would have
tuned the instrument toward the model's own judgement and called the result
calibration. Rounds 1 and 2 are reported as instrument shakedowns, not
calibrations, and their decisions are superseded.

### 6.2 Title and abstract screening (executed)

All 9,786 records were screened under `screening_v3`. Structured output per
record: decision (include / exclude / unclear), the single governing exclusion
criterion where applicable, a free-text reason specific to that record, and a
calibrated confidence. Every `unclear` routes to the investigator.

Decision coverage was verified exact against the corpus — every record decided
once, none invented, none missed. An API failure raises and is never recorded as
a decision: a failure silently converted into an exclusion would corrupt both the
PRISMA count and the recall estimate, undetectably.

A subset of 1,700 records was screened twice under the identical instrument by
two different models. Raw agreement was 94.1%, with 1.4% of records differing on
the consequential include-versus-exclude axis; the remainder involved `unclear`,
which reaches a human either way. This is model-selection evidence and is
reported as such. It is **not** calibration: it establishes that two models read
the instrument similarly, not that either agrees with the investigator.

**The screening counts are not reported in this document.** The registered
Stage 0 gate has not been passed (Section 6.3). `pipeline/report_screening.py`
refuses to emit them, and `PRISMA_flow.md` is generated by calling that same
gated function, so the figure withholds them as well. The decisions exist, are
committed, and are auditable record by record; they are provisional until
validated.

### 6.3 Calibration and the Stage 0 gate (NOT executed)

The gate is Cohen's kappa >= 0.75, computed with a confidence interval, between
the investigator's blind screening of the 300-record calibration sample and the
model's decisions on the same records. The model side already exists, having been
produced as part of the corpus run under the same instrument; only the human side
is outstanding.

No substitute exists. `agreement.compare` requires one human log and one AI log
and refuses an AI-versus-AI comparison, so a second model run cannot stand in.

If the gate is not met after revision, the registered contingency applies:
narrowing to the exposure arm (4,029 records) as a recorded amendment.

### 6.4 Recall validation (sample drawn; screening NOT executed)

False positives are self-correcting — every AI-include proceeds to full text,
where the investigator sees it. The unrecoverable error is the false negative.
Validation therefore targets AI-**exclusions**: a 1,000-record sample stratified
by confidence, deliberately over-sampling low-confidence exclusions,
hand-screened blind.

The sample is drawn (500 / 300 / 200 across three confidence strata, seed
recorded, reproducible). The strata boundaries were reset from their registered
placeholders before drawing, because the observed screener was more confident
than those placeholders assumed: under them, one stratum held 16 of 3,767
exclusions against an allocation that draws 500 from it. The sampling function
refused to draw rather than silently returning 16. New boundaries were chosen on
a single structural criterion — the sampling fraction must fall monotonically as
confidence rises, since over-sampling the error-prone tail is the purpose of
stratifying — and were fixed before the draw, before any human screening, and
before any recall figure could exist.

Because the sample is stratified, its raw proportions are not the population's.
The over-sampled stratum is the one where a missed study is most likely to be
hiding, so the raw sample rate is enriched for error and **overstates** the
false-negative rate. Both the unweighted sample statistics and the
stratum-weighted population estimate will be reported, each labelled, with an
exact Clopper-Pearson 95% interval and the full confusion matrix. If false
negatives are found, the observed rate and its interval are reported as they
stand and the sample is extended in blocks of 500; the software has no option to
drop a block from the calculation. A recall estimate that comes out poor is
reported, not re-run until it looks favourable.

### 6.5 Full text (NOT executed)

Gap-map coding assigns categorical fields and is AI-assisted with investigator
verification of a stratified sample plus every study in any cell driving a
headline claim. Extraction for meta-analysis is done manually by the investigator
without exception, since that is where extraction error causes real harm.

---

## — Boundary: nothing below this line has been executed —

The remainder describes the registered design for stages that have not run. It
reports no results, because none exist.

---

## 7. Data items

One row per study, with dimensions stored independently of any display format:
approach, care stage, condition domain, modality, chain link, marker class,
design, sample size, population, country, follow-up, effect metric and value with
its variance, risk-of-bias domains and overall judgement, six epigenetic-methods
quality flags and their derived tier, and — for every quantitative value — the
page, table, or figure it came from.

No default value is substituted for missing data at any point. Missing stays null
and propagates as null, enforced by the data model rather than by convention: a
value cannot be constructed without its source location, and a field's absence
must be stated explicitly rather than omitted. This is the specific structural
correction for the superseded pipeline in this repository, which filled
unavailable effect sizes with the constant 0.3 and unavailable sample sizes with
the constant 200.

## 8. Risk of bias

Assessed with the tool matching each study's design and modality: RoB 2 for
randomised trials, ROBINS-I for non-randomised intervention studies, QUADAS-2 for
diagnostic accuracy, and PROBAST for prognostic model studies. A bespoke six-item
epigenetic-methods checklist is applied in addition, covering tissue
appropriateness, cell-type composition adjustment, batch-effect handling,
multiple-testing control, platform and normalisation reporting, and replication.
Risk of bias is reported as a mapped dimension, so that a dense but
methodologically weak cell is visually distinguishable from a dense and sound one.

## 9. Synthesis

The evidence gap map is the primary output: approach by care stage, with condition
domain, chain link, design, and risk of bias as filterable dimensions, generated
from the coded dataset rather than assembled by hand.

Meta-analysis is nested and gated. A cell is pooled only if it meets pre-specified
poolability criteria registered in advance — a minimum number of studies, a common
effect metric, a compatible population and comparator, and extractable variance.
Cells failing the gate are reported as gaps, not pooled with assumptions
substituted for missing variance. The gate is pre-specified precisely so that the
decision not to pool cannot be made after seeing which result pooling would
produce.

## 10. Limitations of the methods as executed

Stated here rather than deferred, because each is a shortfall against the
registered design rather than an inherent limitation of the question:

1. **Two databases, not four.** Embase and Web of Science were inaccessible.
   Coverage is consequently narrower than a fully resourced review's, and the
   Europe PMC substitution adds non-MEDLINE content rather than replicating
   Embase's indexing.
2. **No PRESS peer review of the search.** The protocol commits to it; no
   information specialist was available. A self-assessment is not offered as a
   substitute.
3. **Trial registries not yet searched.** ClinicalTrials.gov and WHO ICTRP remain
   outstanding, so the "registered but unreported" overlay the protocol describes
   cannot yet be populated.
4. **Single human reviewer.** Mitigated by design — a quantified recall estimate
   with an exact confidence interval is a stronger and more auditable claim than
   dual review that never measures its own recall — but it remains a single
   reviewer, and the mitigation is only as good as the recall figure it produces.
5. **Design-filter validation.** The primary-study design filter and the
   secondary-literature exclusion were written for this review and have not been
   externally validated against a reference set.
6. **The screening instrument was revised twice against model behaviour, not
   against the investigator.** Protocol Section 5 provides for refinement
   between calibration rounds, but it assumes each round is anchored by human
   screening. Rounds 1 and 2 were not: the defects they exposed were internal
   incoherences in the instrument (an unreachable criterion, a missing one, two
   contradictory rules), visible without a human comparator. That is why
   refinement stopped at v3 rather than continuing. It remains true that the
   instrument now in use has never been tested against the investigator's own
   judgement, which is precisely what the Stage 0 gate exists to do.
7. **Two models contributed decisions, and only one log is used.** 1,700 records
   were screened on both; the reported log is single-model throughout, and
   `single_ai_provenance` refuses a log spanning two models or two prompts. The
   cross-model agreement (94.1%) is reported as model selection, not as a
   substitute for calibration.
8. **Screening ran through dispatched agents rather than a metered API.** The
   schema, instrument hash, model identifier and per-record confidence are
   recorded identically either way, and every batch was verified set-equal to
   its input before collection. What this path does not give is token-level cost
   accounting, so no per-record cost is reported.
