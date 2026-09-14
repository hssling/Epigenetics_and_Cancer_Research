# Protocol amendments

Every deviation from the registered protocol (OSF 3xtf2) is recorded here with
its date and rationale. Nothing is changed silently.

Each amendment below was decided and enacted **before any eligibility result
existed**, so none can have been shaped by seeing which way a result came out.
That ordering is the point of this file, not a courtesy.

| # | Date | Section | Change | Rationale |
|---|---|---|---|---|
| 1 | 2026-09-14 | 4.1 Information sources | Europe PMC substituted for Embase, restricted to `NOT SRC:MED`. Web of Science not substituted. | No institutional access to Embase or Web of Science. See Amendment 1. |
| 2 | 2026-09-14 | 4.4 Deduplication | Publication-year match relaxed to ±2 years, and the DOI-conflict guard disapplied, **for preprint pairs only** | A preprint and its published version necessarily differ in year and always differ in DOI. The registered rule double-counted 136 studies. See Amendment 2. |
| 3 | 2026-09-14 | 5 Screening, Stage 0 | Screening instrument refined `screening_v1.md` → `screening_v2.md` after calibration round 1 | Registered Stage 0 behaviour ("eligibility criteria and AI prompt refined"). Round 1 exposed an unreachable criterion and a missing one. See Amendment 3. |
| 4 | 2026-09-14 | 5 Screening, Stage 0 | Instrument refined `screening_v2.md` → `screening_v3.md` after calibration round 2 | Round 2 exposed two defects introduced by v2's own wording. See Amendment 4. |

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
| ClinicalTrials.gov | free | not yet searched |
| WHO ICTRP | free | not yet searched |

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
