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
| 5 | 2026-09-17 | 5 Screening, Stage 2 | Recall-validation confidence strata reset from (<0.5, <0.8) to (<0.66, <0.81) | The registered boundaries left only 16 of 3,767 exclusions in the stratum the design draws 500 from. See Amendment 5. |
| 6 | 2026-09-17 | 4.1 Information sources | ClinicalTrials.gov searched as a separate registry stream (694 registrations). WHO ICTRP **not** searched. | The registered registry search was outstanding. ICTRP has no endpoint callable unattended; it remains an outstanding manual step. See Amendment 6. |

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
