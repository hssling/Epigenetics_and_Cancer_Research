# Protocol amendments

Every deviation from the registered protocol (OSF 3xtf2) is recorded here with
its date and rationale. Nothing is changed silently.

Each amendment below was decided and enacted **before any eligibility result
existed**, so none can have been shaped by seeing which way a result came out.
That ordering is the point of this file, not a courtesy. Amendment 7 was
decided after a calibration attempt was refused; its section states exactly
what existed at that point and what did not.

| # | Date | Section | Change | Rationale |
|---|---|---|---|---|
| 1 | 2026-09-14 | 4.1 Information sources | Europe PMC substituted for Embase, restricted to `NOT SRC:MED`. Web of Science not substituted. | No institutional access to Embase or Web of Science. See Amendment 1. |
| 2 | 2026-09-14 | 4.4 Deduplication | Publication-year match relaxed to ±2 years, and the DOI-conflict guard disapplied, **for preprint pairs only** | A preprint and its published version necessarily differ in year and always differ in DOI. The registered rule double-counted 136 studies. See Amendment 2. |
| 3 | 2026-09-14 | 5 Screening, Stage 0 | Screening instrument refined `screening_v1.md` → `screening_v2.md` after calibration round 1 | Registered Stage 0 behaviour ("eligibility criteria and AI prompt refined"). Round 1 exposed an unreachable criterion and a missing one. See Amendment 3. |
| 4 | 2026-09-14 | 5 Screening, Stage 0 | Instrument refined `screening_v2.md` → `screening_v3.md` after calibration round 2 | Round 2 exposed two defects introduced by v2's own wording. See Amendment 4. |
| 5 | 2026-09-17 | 5 Screening, Stage 2 | Recall-validation confidence strata reset from (<0.5, <0.8) to (<0.66, <0.81) | The registered boundaries left only 16 of 3,767 exclusions in the stratum the design draws 500 from. See Amendment 5. |
| 6 | 2026-09-17 | 4.1 Information sources | ClinicalTrials.gov searched as a separate registry stream (694 registrations). WHO ICTRP **not** searched. | The registered registry search was outstanding. ICTRP has no endpoint callable unattended; it remains an outstanding manual step. See Amendment 6. |
| 7 | 2026-10-29 | 5 Screening, Stages 0 and 2; 9; 11 | Blind kappa calibration gate withdrawn. Screening becomes AI-led with investigator verification. Recall validation reduced from 1,000 to 200 blind-screened AI-exclusions. | The investigator will not do the registered 300-record blind calibration. A screening design that can actually be executed, and is reported as what it is, is preferable to one that is registered and not carried out. See Amendment 7. |
| 8 | 2026-10-29 | 5 Screening, Stage 2 | Extension rule fixed: one or more false negatives in the 200 triggers blind screening of the remaining 800 of `validation_1000.json`, in a single step; recall is then reported on the full 1,000. | Amendment 7 kept "extend the sample" but left the step and the stopping point unspecified, which would have let them be chosen after seeing the result. See Amendment 8. |

---

## Amendment 1 (enacted 2026-09-14): database substitution

### What the registration says

The registration lists four bibliographic sources under Databases:
PubMed/MEDLINE, **Embase (Elsevier)**, **Web of Science Core Collection
(Clarivate)**, and **Cochrane CENTRAL**; plus ClinicalTrials.gov and WHO ICTRP
as trial registries.

### What was done, and why

The investigator has no institutional subscription to Embase, Web of Science,
or Scopus. Those searches could not be executed as registered. Rather than
search fewer databases than registered and leave the gap implicit:

| Registered | Status | Executed |
|---|---|---|
| PubMed/MEDLINE | searched | 2026-09-13, 9,089 identified |
| Embase | no access | **Europe PMC**, 2026-09-14, 890 retrieved |
| Web of Science | no access | not substituted at this stage |
| Cochrane CENTRAL | access uncertain | not yet searched |
| ClinicalTrials.gov | free | **searched**, 2026-09-17, 694 retrieved (Amendment 6) |
| WHO ICTRP | free, but not callable unattended | not searched — outstanding as a manual step (Amendment 6) |

### The `NOT SRC:MED` restriction, and why it is not a narrowing

Europe PMC was searched restricted to records **not already in MEDLINE**.

MEDLINE had already been searched natively, using controlled vocabulary
(`[MeSH]`), publication-type filters (`[pt]`) and title/abstract field tags
(`[tiab]`). Europe PMC's syntax cannot express those with equivalent
semantics — its free-text terms search **full text** for open-access records,
so the same concept set returns 239,868 records unrestricted against PubMed's
9,089. Even after wrapping every term as `(TITLE:x OR ABSTRACT:x)` to
approximate `[tiab]`, it returns 5,982.

Fetching all 5,982 and deduplicating would have imported several thousand
MEDLINE records that the registered PubMed strategy deliberately excludes via
filters Europe PMC cannot reproduce — quietly *widening* a registered search
under the appearance of merely adding a database. The restriction confines
Europe PMC's contribution to the coverage it uniquely offers: preprints,
PMC-only deposits, theses and agricultural literature, which is precisely the
role the Embase substitution is meant to fill.

### What this costs, stated plainly

Coverage is **not** equivalent to a review with full commercial database
access. Europe PMC does not replicate Embase's indexing of European and
pharmacological literature, and no substitute was found for Web of Science.
This is carried in the manuscript's limitations
(`manuscript/METHODS.md`, Section 11), not offset by a claim of equivalence.

---

## Amendment 2 (enacted 2026-09-14): deduplication of preprint pairs

### The registered rule

Deduplication by DOI, then PMID, then fuzzy title match additionally requiring
the same first-author surname and the same publication year; and separately,
that two records which both carry an identifier and disagree on it are never
merged.

### The defect

Both of those guards are correct for two journal articles and wrong for a
preprint and its own published version:

- a preprint necessarily **precedes** publication, so the years never match;
- a preprint and the published article **always** carry different DOIs
  (`10.1101/...` from bioRxiv/medRxiv, `10.21203/rs.3.rs-...` from Research
  Square, against the journal's own).

In the combined corpus, 137 preprints shared an exact normalised title and an
identical first author with a PubMed record. The year gate blocked all of
them; once that was relaxed, the DOI-conflict guard still blocked 136. Every
one was being counted as two separate studies.

### The change

- Publication-year equality relaxed to a ±2-year window **when one record of
  the pair is a preprint**; exact-year matching retained for all other pairs.
- The DOI-conflict guard **disapplied for preprint pairs**; retained in full
  for every other pair.
- The PMID guard is untouched. Europe PMC preprints carry no PMID, so a
  preprint pair never reaches it; any pair that does is two indexed records
  disagreeing on a MEDLINE identifier, which remains decisive.

A preprint is identified from Europe PMC's own `SRC:PPR` source
classification, which is authoritative, not inferred from a DOI prefix, which
would be a heuristic.

What carries a preprint merge is therefore the conjunction that remains: fuzzy
title ≥ 95, identical first-author surname, and year within ±2.

### Effect and audit

192 duplicates removed from a 9,978-record union, leaving **9,786**. All 184
cross-source merges were inspected: 139 matched on an exactly identical
normalised title, and the 45 non-exact matches differ only by casing, dash
style, an added word such as "novel", or a conference-abstract prefix. No
over-merging was found.

---

## Amendment 3 (enacted 2026-09-14): screening instrument v1 → v2

### This is registered behaviour, not a deviation from it

Protocol Section 5, Stage 0 commits to: "Cohen's kappa computed, all
disagreements inspected, **eligibility criteria and AI prompt refined**.
Repeated until kappa ≥ 0.75." Refining the instrument after a calibration
round is what the registration says will happen. It is recorded here because
the instrument's SHA-256 is written into every decision, so the change must be
traceable — not because it is unexpected.

### What round 1 found

150 of the 300 calibration records were screened under `screening_v1.md`
(SHA-256 `dbf587fc…`). Two defects were identified independently by all three
screening runs:

**(a) No criterion for an ineligible study design.** Include criterion 2
required one of five designs (RCT, non-randomised trial, cohort, case-control,
cross-sectional), but the exclusion list's `not_primary` covered only reviews,
editorials, comments, letters and conference abstracts. A study with a design
on neither list — a case series, a descriptive molecular-profiling series, an
in-silico database re-analysis, a Mendelian randomisation on summary data —
could not be excluded on any available criterion. Such records were being
included at confidence 0.5–0.65 for want of a criterion that existed. The
observed include rate was **57%**, far above what protocol Section 5 Stage 3
anticipates.

**(b) `ncrna_only` was unreachable.** The instrument directs the screener to
use "the FIRST criterion that applies". An ncRNA-only study also has no
eligible measured marker, so `no_measured_marker` (listed third) always
pre-empted `ncrna_only` (listed fourth). The criterion could never fire as
written.

### The changes in v2

Each is traced to its authority. Where the protocol settles the question, v2
aligns the instrument *with* the registered protocol rather than changing it.

| Change | Authority |
|---|---|
| `not_primary` extended to cover a design not among the five eligible ones | Protocol §3.1 already restricts Design to those five; v1 simply provided no criterion to enforce it |
| `ncrna_only` applied **before** `no_measured_marker` whenever an ncRNA was measured, by re-wording rather than reordering the registered `CRITERIA` tuple | Restores the criterion's evident registered intent; the tuple order is preserved because it maps to the human screening keypad |
| "diagnosis" added to the approach-link list | Protocol §3.1 says "a clinical or public health decision"; the registered PubMed query already searched `diagnos*`. v1 omitted it inconsistently |
| Study protocols (planned work, no data) → `not_primary` | Directly analogous to the registered "conference abstract without data" |
| Marker measured only in non-human material, in a study that has human participants → `no_measured_marker` | Protocol §3.1 requires a measured marker in a human study; v1's `not_human` says "animal, in vitro, or cell-line **only**" and so did not reach hybrid designs |
| Mendelian randomisation / summary-data designs → `not_primary` | The study did not measure the marker and its design is not among the five |
| Analyses of individual-level data from an eligible underlying design remain eligible | Protocol §3.1 is about study design, and the design is that of the underlying study |

**Two changes are investigator judgement with no direct protocol basis**, and
are flagged as such so a reader can disagree with them specifically:

1. **Histone marks measured as a circulating protein.** A histone
   modification assayed on chromatin or in cells is eligible *including* when
   the authors read it as a damage or inflammation signal (γ-H2AX by
   immunohistochemistry), because judging intent rather than measurement is
   unreliable at title/abstract. A histone protein measured in plasma or serum
   as a circulating biomarker (citrullinated H3 as a NET marker) is treated as
   a protein assay, not a chromatin-state measurement, and excluded.
2. **Sperm chromatin integrity tests** (SCSA, DNA fragmentation index, high
   DNA stainability) are excluded as `no_measured_marker`: they measure DNA
   strand breakage and packaging, not a regulatory epigenetic mark.

### Consequences for the decision log

Round-1 decisions were made under `dbf587fc…` and are **superseded, not
reused**. They are retained in the log for audit but take no part in any
reported statistic. Calibration is re-run in full under v2
(`0b2565e2d7be6fe29dcb81e6d34b831546476f85c5256cdabfc313e353d335da`).

### What remains outstanding

The registered Stage 0 gate is Cohen's kappa ≥ 0.75 **between the investigator
and the model**, on the same 300 records screened blind. No human screening has
been done, so no kappa exists and the gate has not been passed. Round 1 was an
instrument-shakedown, not a calibration in the registered sense, and it is not
reported as one.

---

## Amendment 4 (enacted 2026-09-14): screening instrument v2 → v3

### What round 2 found

All 300 calibration records were screened under `screening_v2.md`
(`0b2565e2…`). The v2 changes worked as intended — `not_primary` fired 49
times where under v1 it could not fire at all — but two defects **introduced
by v2's own wording** were identified independently by multiple batches.

**(a) "Tool development" was miscategorised as a design.** v2 listed "a
methods or tool-development paper" among examples of a design not on the
eligible list. Tool development is a study's *purpose*, not its design: a
methylation classifier developed and evaluated in cases and controls is a
case-control diagnostic-accuracy study. Protocol §6 lists
`diagnostic-accuracy` as an in-scope modality, so these are eligible. The
inconsistency was visible in the decisions — in one batch, four records of
the same class were split, one excluded and three included.

**(b) Two v2 bullets contradicted each other on secondary data.** v2 said
analyses of existing individual-level cohort data are eligible, and *also*
that a purely in-silico re-analysis of an existing database is
`not_primary`. For a TCGA or GEO methylation paper both bullets apply and
point opposite ways. Two batches reported being unable to resolve it; a third
resolved it by following each paper's self-description, which makes
eligibility depend on an author's choice of wording.

Both classes are common in this corpus, so neither could be left to the
full run.

### The changes in v3

| Change | Authority |
|---|---|
| "Tool development" removed from the ineligible-design examples; a classifier, assay or score developed **or evaluated in human participants forming an eligible design** is eligible, judged on the ordinary criteria | Protocol §6 lists `diagnostic-accuracy` as an in-scope modality; §3.1 restricts by design, and the design here is case-control or cohort |
| A purely technical paper with **no human evaluation sample** remains `not_primary` | Protocol §3.1: no eligible design, no human measurement |
| The "purely in-silico re-analysis" bullet is **deleted**. Eligibility never depends on who generated the data: secondary analysis of individual-level human data is eligible; only work using solely published summary statistics or database aggregates is `not_primary` | Investigator judgement. Protocol §3.1 defines eligibility by design and measurement and says nothing about data provenance, so v2's provenance test had no registered basis |
| The human-measurement question is checked **before** `ncrna_only`, resolving a reported ordering collision | Protocol §3.1 requires the marker to be measured in a human study |
| A bare tissue or tumour series with **no stated analytic design** returns `unclear` rather than being assumed to be cross-sectional or assumed to be a case series | The registered `unclear` route exists for exactly this; assuming either way would be a guess |

### Stopping rule for instrument refinement

Refinement stops here. The registered Stage 0 gate is Cohen's kappa between
the **investigator** and the model, and no human screening has been done, so
there is no anchor against which further refinement could be checked.
Continuing to refine without one would tune the instrument toward the
model's own judgement and call the result calibration, which it would not be.

Rounds 1 and 2 were instrument shakedowns. They are reported as such, and
the decisions from both are superseded.

### Outstanding

- No kappa exists. The Stage 0 gate has **not** been passed.
- The include rate observed under v2 was 53.7%, which projects to roughly
  5,250 full-text records from the 9,786-record corpus. That is consistent
  with the map stage, which is AI-assisted coding of categorical fields, but
  far above the 30-60 studies protocol §5 anticipates for manual
  meta-analysis extraction. The registered contingency — narrowing to the
  exposure arm (4,029 records) — is an investigator decision and has not
  been taken.

---

## Amendment 5 (enacted 2026-09-17): recall-validation strata boundaries

### This is directed by the design, not a departure from it

The design spec (`docs/superpowers/specs/2026-09-13-egm-screening-design.md`,
Section 8 risk table) states that the strata boundaries are "set after
inspecting the confidence distribution, recorded before drawing". They could
not have been fixed in advance: nobody knew how confident the screener would
be until it had screened something. This entry is that record.

### What the registered boundaries assumed, and what actually happened

The placeholder boundaries were `low < 0.5`, `mid < 0.8`, `high` otherwise,
written before any screening existed. Against the completed run they give:

| stratum | registered boundary | N of 3,767 exclusions |
|---|---|---:|
| low | < 0.5 | **16** |
| mid | 0.5–0.8 | 1,695 |
| high | ≥ 0.8 | 2,056 |

The registered allocation draws **500** records from `low`. There are 16.

`stratified_sample` refused to draw, raising `stratum 'low': requested 500,
only 16 available`. That refusal is why this was noticed at all — a function
that silently returned 16 would have produced a 516-record "1,000-record
validation sample" and a recall estimate computed on a denominator nobody
checked.

### The new boundaries and why these

`low < 0.66`, `mid < 0.81`, `high` otherwise, giving N = 790 / 1,369 / 1,608.

The binding constraint is not that the draw succeeds — several candidate
boundaries allow that. It is that the **sampling fraction must fall
monotonically as confidence rises**, because over-sampling the error-prone
tail is the entire purpose of stratifying. With the registered 500/300/200
allocation:

| boundaries | N (low/mid/high) | sampling fraction | monotonic? |
|---|---|---|---|
| < 0.5 / < 0.8 | 16 / 1,695 / 2,056 | — | not drawable |
| **< 0.66 / < 0.81** | **790 / 1,369 / 1,608** | **63% / 22% / 12%** | **yes** |
| < 0.66 / < 0.86 | 790 / 2,291 / 686 | 63% / 13% / 29% | no |
| < 0.71 / < 0.86 | 1,153 / 1,928 / 686 | 43% / 16% / 29% | no |

The two rejected candidates would have sampled *high*-confidence exclusions
more heavily than mid — inverting the design. Only one candidate preserved it.

### Why this is not strata-shopping

Adjusting strata after seeing data is normally a serious red flag, so the
ordering matters and is stated plainly:

1. The boundaries were chosen from the confidence distribution alone.
2. They were fixed **before** the sample was drawn.
3. No human screening has occurred, so no false negative has been observed.
4. **No recall figure exists, or can exist, yet.** There is nothing to tune
   toward.

The criterion applied was structural — preserve monotonic over-sampling — not
outcome-based. Anyone may recompute the table above from
`screening/screening_decisions_sonnet.jsonl` and check that only one candidate
satisfies it.

### Effect

`screening/validation_1000.json` drawn: 1,000 AI-excluded records, 500 low /
300 mid / 200 high, seed 20260913, reproducible from the published seed.

The stratum-weighted recall estimate uses these population sizes, so the
weights change with them. Both the unweighted and the weighted estimate are
reported, as Section 8 requires.

---

## Amendment 6 (enacted 2026-09-17): trial registry search

### What the registration says

Protocol Section 4.1 lists two trial registries, **ClinicalTrials.gov** and
**WHO ICTRP**, with a purpose distinct from the bibliographic databases:
"identifying unpublished and ongoing studies, and populating a 'registered but
unreported' overlay on the map that indicates where evidence is in flight."

Both stood recorded as "not yet searched" in Amendment 1 and in PRISMA-S item 3.

### What was done

**ClinicalTrials.gov: searched.** 694 registrations, 2026-09-17, via API v2,
which requires no credential. `search/raw/ctgov_registry.json`.

**WHO ICTRP: not searched.** The reason is narrower than "no access", and
worth stating precisely because it determines what can still be done.

ICTRP does publish a Search Portal Web Service, and its portal does allow
search results to be downloaded in CSV and XML, including all records of a
search, under WHO's Terms and Conditions. Neither route is an open endpoint
this pipeline can call unattended: the web service operates on an agreed-partner
basis arranged with WHO, and the portal download is an interactive action
requiring acceptance of those Terms. Accepting terms on the investigator's
behalf is not something this pipeline does.

**ICTRP therefore remains available to the investigator as a manual step**, and
is recorded as outstanding rather than impossible. Executing it would be a
further amendment, with the downloaded export entering as its own stream
alongside ClinicalTrials.gov.

ICTRP aggregates ClinicalTrials.gov together with the other primary registries,
so much of its content for this topic is already reached through the search
that was run. The gap is real for trials registered **only** in a non-US
registry (ChiCTR, ISRCTN, CTRI, IRCT and the rest), and is carried in the
limitations rather than offset by a claim of equivalence.

### These records are a separate stream, not corpus additions

The 694 registrations do **not** join the 9,786-record screening corpus, and
the existing screening is therefore untouched by this amendment.

The reason is not procedural convenience. A registration is not a publication.
A trial that was registered and never published is the *absence* of evidence,
and merging the two streams would let it be counted as evidence — the precise
inversion the overlay exists to expose. PRISMA 2020 gives registers their own
identification column for this reason, and so does `render_prisma.py`.

They are modelled separately too: `RegistryRecord` rather than `SearchRecord`,
with no journal, no author list and no abstract, so the type system refuses the
conflation rather than relying on anyone remembering it.

### How the registered strategy was translated, and what it cost

The PubMed strategy is CORE AND HUMAN AND (EXPOSURE OR CLINICAL_USE) AND DESIGN
AND YEARS, every term restricted to `[tiab]`. Clause by clause, with counts
measured live before the module was written:

| Clause | Decision | Why |
|---|---|---|
| CORE | kept | the concept the map is about |
| `[tiab]` | kept, as `AREA[BriefTitle]` OR `AREA[BriefSummary]` | unrestricted, `query.term` matches eligibility criteria and outcome text: 1,771 vs 694 |
| HUMAN | dropped | ClinicalTrials.gov registers human studies only — vacuous, not relaxed |
| DESIGN | dropped | its purpose is excluding reviews, editorials and case reports; a registry contains none |
| EXPOSURE OR CLINICAL_USE | **dropped** | see below |
| YEARS | kept, against StartDate | a registration has no publication year |

The last one is a judgement rather than a formality, so the measurements are
given in full: restricted to title/summary like the core block it yields 535;
applied unrestricted, 679; omitted, 694.

It was dropped because in a registry those concepts live in the structured
intervention and outcome-measure fields, not in the summary prose — a diet
trial's brief summary frequently never uses the word "diet". Dropping a fifth
of the registry stream on a clause the record format cannot express would be an
artefact of the source, not an eligibility decision. Eligibility is decided at
screening, on the same instrument as everything else.

The net effect is a wider net over a much smaller pool: 694 registrations
against 9,786 bibliographic records. For an overlay whose question is "what is
in flight that we cannot yet see", under-retrieval is the expensive error.

### What the stream contains

| | n |
|---|---:|
| registrations retrieved | 694 |
| interventional | 380 |
| observational | 314 |
| completed | 194 |
| results posted to the registry | 25 |
| with a registry-linked result publication | 125 |
| **unreported-overlay candidates** | **123** |

An overlay candidate is a registration that is COMPLETED, carries an **ACTUAL**
(not estimated) completion date, has no results posted to the registry, and has
no linked result publication.

**123 is a count of candidates, not a finding.** Confirmation requires checking
each against the bibliographic corpus, which has not been done and cannot be
reported before the Stage 0 gate. The ACTUAL-versus-ESTIMATED distinction is
enforced in the data model rather than by convention: an abandoned 2019
*projected* completion date says nothing about whether a trial finished, and
collapsing the two would manufacture overdue trials out of projections —
inventing exactly the finding this overlay is meant to report.

---

## Amendment 7 (enacted 2026-10-29): AI-led screening with investigator verification

> **Status: filed and approved.** Submitted as an update to OSF registration
> 3xtf2 at 05:06 UTC on 2026-10-29 and approved at 05:07 UTC (schema response
> `6ae2d2e5e556501fd0fdef5e`; updated questions: Screening stages, Screening
> reliability, Sampling). It is the registration's current version. The
> 200-record validation sample was drawn after approval, not before.

### What the registration says

Protocol Section 5, Stage 0: "The investigator screens all 300 blind; the AI
screens the same 300 independently. Cohen's kappa computed … Repeated until
kappa >= 0.75. The final kappa is reported in the manuscript."

Section 5, Stage 2: AI exclusions validated by "a 1,000-record sample,
stratified by AI confidence … hand-screened blind by the investigator".

Section 11 describes title/abstract screening as "gated by the calibration
requirement in Section 5 (kappa >= 0.75) and validated against 1,000
hand-screened AI-excludes".

### What happened

On 2026-10-29 a calibration log for the 300-record sample was produced. It
recorded 300 decisions, every one `include`, over 378 seconds (1.3 seconds per
record). The investigator describes it as assisted screening. The agreement
gate refused it before computing anything, because the log is faster than a
person can read and judge a title and abstract (`agreement.py`,
`MIN_SECONDS_PER_DECISION` = 3 s). Separately from timing, a log with no
variation cannot calibrate anything: if one rater gives a single answer
throughout, kappa is 0 by construction, whatever the other rater did.

The log is kept, unused, as
`screening/human_calibration_INVALID_2026-10-29.jsonl`. **No kappa was
computed, and no comparison between human and AI decisions has been seen by
anyone.** The investigator has decided not to do the 300-record blind
calibration.

### What existed when this was decided

| Artefact | State on 2026-10-29 |
|---|---|
| AI title/abstract decisions, all 9,786 records | complete, provisional |
| Inter-model agreement, Opus 5 vs Sonnet 5, 1,700 shared records | 94.1% raw agreement |
| Human calibration decisions | none valid |
| Kappa between investigator and model | never computed |
| Human recall-validation decisions | none |
| Recall or false-negative estimate | does not exist |

So the change cannot have been tuned towards a favourable kappa or recall,
because neither has ever existed. It is, however, a weakening of the
registered design, made because the registered design will not be carried out.
It is not presented as anything else.

### The change

**Section 5, Stage 0: withdrawn.** There is no kappa gate. In its place:

- The instrument's reliability is reported as **inter-model agreement**: Opus 5
  vs Sonnet 5 under the identical frozen instrument (`screening_v3.md`, SHA-256
  `03fc7b73…`), 94.1% on 1,700 records, with the full confusion matrix. It is
  labelled as model-to-model consistency, and the manuscript says in terms
  that it is **not** agreement with a human reviewer.
- No Cohen's kappa against the investigator is reported, because none exists.

**Section 5, Stage 1: unchanged in procedure; its status changes.** The Sonnet
decisions on all 9,786 records become the screening decisions of record.
Every AI `include` proceeds to full text, where the investigator makes the
eligibility decision directly, so false positives remain self-correcting.
Every `unclear` (274) is decided by the investigator.

**Section 5, Stage 2: reduced from 1,000 to 200, still blind.**

- **Sample:** 200 AI-excluded records, drawn from the existing
  `screening/validation_1000.json` by `pipeline.sampling.stratified_sample`
  with **seed 20261029**. Allocation is 100 / 60 / 40 across the Amendment 5
  strata (populations 790 / 1,369 / 1,608), which keeps the sampling fraction
  falling as confidence rises (12.7% / 4.4% / 2.5%). The allocation and seed
  are fixed here, before the draw.
- **Drawn** 2026-10-29, after OSF approval, as
  `screening/validation_200.json` (SHA-256 `a6b922a1…`), by
  `python -m pipeline.draw_sample subsample`. Records are copied unchanged
  from `validation_1000.json`, which had already passed the batch-file drift
  check, so the text the investigator sees is the text the model saw.
- **Screening:** blind, in `pipeline.screen_app`, which cannot show an AI
  decision and refuses any decision made less than 3 seconds after its record
  is shown. The rule-based keyword highlighting (METHODS 6.3, `TERMS_VERSION`
  1) is permitted; any model-generated summary or suggestion is not.
- **Validity check:** the human log must pass the existing timing and
  integrity checks in `agreement.py`. A log that fails is reported as failed,
  not replaced by an assisted one. `recall.validate_recall` enforces this
  (human screener only; the 3-second floor, judged on the drawn records).
- **Reporting:** the observed false-negative rate, both unweighted and
  stratum-weighted, each with an exact Clopper-Pearson 95% interval. If none
  of the 200 is a false negative, the two-sided upper bound on the
  false-negative rate is **1.83%**. Against 3,767 exclusions, that is **up to
  about 69 eligible studies plausibly missed**. The registered 1,000-record
  design would have bounded that at 0.37%, about 14 studies. The manuscript
  states both figures, so the cost of the change is visible.
- **Extension:** the registered rule still applies. If false negatives are
  found, they are reported as observed and the sample is extended within the
  already-drawn 1,000. A poor estimate is reported, not re-run until it looks
  better.

**Section 9, contingencies.** The row that triggers narrowing to the exposure
arm when "kappa >= 0.75 … cannot be reached" no longer has a trigger. Narrowing
to the exposure arm (4,029 records) remains available as a separate scope
decision, which would need its own amendment.

**Section 11, AI use declaration.** The title/abstract screening bullet is
replaced with:

> Title/abstract screening (Stage 1) was performed by Claude Sonnet 5 under a
> frozen instrument. It was not calibrated against a human reviewer. Its
> consistency was assessed as agreement with a second model (Claude Opus 5,
> 94.1% on 1,700 records). Its false-negative rate was estimated from 200
> AI-excluded records screened blind by the investigator (Section 5, Stage
> 2, as amended). Every AI inclusion and every `unclear` record was decided
> by the investigator.

### What this costs, stated plainly

- **No human-AI agreement figure.** Readers and reviewers who expect a kappa
  will not find one. The manuscript says why: a calibration attempt was made,
  failed the integrity checks, and was not repeated.
- **A wider recall interval.** The worst case for missed eligible studies rises
  from about 14 to about 69. For an evidence gap map, whose findings are about
  where evidence is dense or sparse, a few dozen missing studies against ~5,700
  provisional AI inclusions is unlikely to change a cell from dense to empty. It could matter
  for a sparse cell, and the headline sparse-cell claims (the complete
  A→B→C chain) are worded with that in mind.
- **Single-reviewer human judgement throughout.** This was already the
  registered design. It is unchanged, but it is no longer offset by a measured
  kappa.

These go into the limitations in `manuscript/METHODS.md` (Section 10), and the
abstract describes screening as "AI-led with investigator verification".

### Correction (2026-10-29, after filing): the cost was understated

The figures above — 1.83%, "up to about 69 eligible studies", against 0.37%
and about 14 for the registered design — are the **unweighted** bounds. The
figure the pipeline reports as eligible studies plausibly missed
(`RecallReport.implied_missed_high`, printed beside the screening counts) is
the **stratum-weighted** bound, each stratum's Clopper-Pearson upper bound
weighted by its population share. With zero false negatives:

| design | unweighted upper bound | weighted upper bound | studies plausibly missed (weighted) |
|---|---:|---:|---:|
| registered, 500 / 300 / 200 | 0.37% | 1.38% | about 52 |
| amended, 100 / 60 / 40 | 1.83% | 6.69% | **about 252** |

Computed with `pipeline.recall.clopper_pearson` against stratum populations
790 / 1,369 / 1,608. The weighted bound is wider because the high-confidence
stratum, which holds 43% of exclusions, is sampled at only 40 records.

This changes the "few dozen" reasoning in the cost section: up to about 252
missed studies against ~5,700 provisional inclusions is still unlikely to
empty a dense cell, but it is a materially larger exposure for sparse cells
than stated. ~~The OSF update text quotes no figures, so the filed amendment is
not wrong.~~ **That was wrong** (found 2026-10-29, while filing Amendment 8):
the short text below quotes no figures, but the "Reason for update" actually
filed on OSF does — "the two-sided upper bound is 1.83% (about 69 of 3,767
exclusions), against 0.37% (about 14)". The public record therefore carried
the understated figure. The Amendment 8 filing corrects it on OSF. This file
and `manuscript/METHODS.md` now state both bounds. Found
while drafting METHODS, before any validation screening; nothing about the
design, allocation or seed has changed.

### Text for the OSF update form

> **Amendment 7 — screening validation.** The registered Stage 0 gate
> (investigator-vs-AI kappa >= 0.75 on 300 blind-screened records) is
> withdrawn. A calibration attempt on 2026-10-29 did not meet the pipeline's
> integrity checks and was not repeated; no kappa was ever computed, and no
> recall estimate existed when this decision was made. Title/abstract
> screening is AI-led (Claude Sonnet 5, frozen instrument v3). Reliability is
> reported as inter-model agreement (94.1% vs Claude Opus 5 on 1,700 records),
> labelled as such. All AI inclusions and all `unclear` records are decided by
> the investigator. Recall validation is reduced from 1,000 to 200 AI-excluded
> records (stratified 100/60/40, seed 20261029), screened blind; the
> false-negative rate is reported with an exact 95% CI alongside the bound the
> registered design would have given. Full rationale and costs:
> `egm/protocol/amendments.md`, Amendment 7.

---

## Amendment 8 (enacted 2026-10-29): the recall-validation extension rule

> **Status: filed and approved.** Submitted as an update to OSF registration
> 3xtf2 at 16:13 UTC on 2026-10-29 and approved at 16:13 UTC (schema response
> `6ae3701d70c04d36f089d078`; updated questions: Screening reliability,
> Sampling and sample size). Decided and filed before any of the 200
> validation records had been screened by the investigator; no human
> validation log existed. The filing also corrects, in its justification and
> under Screening reliability, the unweighted Amendment 7 figures quoted on
> OSF (see the correction under Amendment 7).

### What the registration says, and what Amendment 7 left open

Protocol Section 5, Stage 2: "If false negatives *are* found, the observed
rate and its exact CI are reported as-is, and the sample is extended to tighten
the estimate." Amendment 7 reduced the base sample to 200 and kept that clause
("extended within the already-drawn 1,000"). Neither says **how many** records
an extension adds, or **when it stops**.

Left open, both would be decided after the false negatives had been seen. An
extension that proceeds in small batches and stops once the interval "looks
tight enough" ends early exactly when the estimate has drifted favourably, so
the reported rate is biased downward even if every individual screening
decision is honest. Fixing the rule now, before the first record is screened,
removes that freedom.

### The rule

- **Trigger:** one or more false negatives among the 200 records of
  `screening/validation_200.json` (a human `include` or `unclear` on a record
  the AI excluded, as `recall.validate_recall` already counts them).
- **No trigger:** if there are zero false negatives, there is no extension.
  The 200-record estimate is final, and the remaining 800 are not screened for
  recall validation.
- **Extension, if triggered:** the investigator screens, blind and under the
  same conditions as the 200 (`screen_app`, 3-second floor, no AI decision
  shown), **all remaining 800 records** of `screening/validation_1000.json`
  in a single step: 400 / 240 / 160 across the low / mid / high strata.
  `validation_1000.json` was drawn on 2026-09-17 by the registered allocation
  (500 / 300 / 200) and the 200 are a stratified subsample of it, so the union
  is exactly the registered 1,000. It is identified by its sorted-record-id
  SHA-256, `54f0b35e59e5afe2d678a071b5a85758bc379ba8c1908be00a94fc5813689181`,
  fixed here.
- **No intermediate stopping point.** There is no option to screen part of
  the 800 and stop. A partial extension is treated as an incomplete
  validation, as a partial 200 already is.
- **Reporting, if triggered:** the recall estimate reported with the
  screening counts is the one computed on all 1,000. The 200-record result is
  reported as well, labelled as the first stage that triggered the extension.
  Both unweighted and stratum-weighted estimates, each with an exact
  Clopper-Pearson 95% interval, as Amendment 7 specifies.
- **Between the two stages:** if the 200 trigger the extension, the screening
  counts are not withheld while the 800 are screened; finding missed studies
  must not be what hides the result. They are produced with the 200-record
  estimate and marked **provisional** (`report_screening`,
  `recall_extension_owed`), and no output is submitted while that mark
  stands. An extension supplied when the 200 found no false negative is
  refused.

### Why one step to the full 1,000

A single step to the registered sample has no stopping decision left in it,
needs no further draw or ordering, and lands on a design whose properties
were registered: with zero false negatives in 1,000, the stratum-weighted
upper bound is 1.38%, about 52 studies. Smaller steps would save effort only
in the branch where the first steps happen to look good — which is the branch
that biases the estimate.

The cost is effort: 800 further records, about 3–7 hours at 15–30 seconds a
record, in the case where it is triggered.

### A two-stage rule is not a fixed-sample design

The intervals are computed as if each sample size had been fixed in advance.
Under a rule that extends only after a false negative has been seen, that is
an approximation, and the manuscript says so. In the extended branch the
1,000-record sample contains at least one false negative by construction, so
its estimate leans high, which is the conservative direction for a recall
claim. In the unextended branch the result is the Amendment 7 design exactly.

### Text for the OSF update form

> **Amendment 8 — recall-validation extension rule.** Fixed before any
> validation record was screened. If the investigator's blind screening of
> the 200 AI-excluded records finds one or more false negatives, the
> remaining 800 records of the already-drawn 1,000-record sample (stratified
> 400/240/160) are screened blind in a single step, with no intermediate
> stopping point, and recall is reported on the full 1,000 alongside the
> 200-record first stage. Until the extension is complete, any screening
> counts are reported as provisional and nothing is submitted. If none is
> found, there is no extension and the 200-record estimate is final. Full
> rationale: `egm/protocol/amendments.md`, Amendment 8.
