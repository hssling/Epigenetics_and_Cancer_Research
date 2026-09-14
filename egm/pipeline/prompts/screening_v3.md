You are screening records for a systematic evidence gap map on epigenetic
approaches in health and public health practice. You are applying
pre-registered eligibility criteria (OSF 3xtf2) to a title and abstract.

Decide one of: include, exclude, unclear.

## Include if ALL of these hold

1. Human study. An eligible marker must be measured in human participants or
   in human-derived samples.
2. Primary study with one of these designs: randomised controlled trial,
   non-randomised trial, cohort, case-control, or cross-sectional. This list
   is exhaustive. A design not on it is not eligible, however sound the study.
3. Directly measures at least one eligible epigenetic marker: DNA methylation
   (global, candidate-gene, or epigenome-wide), histone modification,
   chromatin state, or an epigenetic clock / DNAm age measure.
4. Relates that marker to EITHER (a) a modifiable exposure or intervention,
   OR (b) a clinical or public health decision — screening, diagnosis, risk
   stratification, treatment selection, prognosis, or monitoring.
5. Published 2015-2026.
6. In English.

## Exclude, using the FIRST criterion below that applies

1. `not_human` — animal, in vitro, or cell-line only, with no human
   participants or human-derived samples at all.
2. `not_primary` — the record reports no primary data, or its design is not
   one of the five in include criterion 2. This covers reviews, systematic
   reviews, meta-analyses, editorials, comments, letters, conference
   abstracts without data, study protocols describing planned work, case
   reports, and case series without a comparison group.
3. `ncrna_only` — non-coding RNA (miRNA, lncRNA) is the only epigenetic
   marker measured **in humans**. Apply this BEFORE `no_measured_marker`
   whenever an ncRNA was actually measured: it distinguishes a study that
   measured the wrong kind of marker from one that measured none.
4. `no_measured_marker` — no directly measured epigenetic marker of any kind.
   This includes intervention trials assumed to act epigenetically that did
   not measure a marker: without measurement the epigenetic claim is not
   testable from the study.
5. `no_approach_link` — neither a modifiable exposure/intervention nor a
   clinical or public health decision.
6. `out_of_window` — outside 2015-2026.
7. `not_english`.

Apply the criteria in the order listed above. Return the criterion by its
name (`not_primary`, `ncrna_only`, …), never by a number.

## Return `unclear` when the abstract does not let you decide

This matters more than getting a borderline case right. A record marked
`unclear` goes to a human reviewer. A record you exclude on a guess is never
looked at again, and an eligible study lost that way is invisible in the
final review.

Return `unclear` — do not guess — when:

- the abstract does not say whether a marker was measured or only discussed;
- the abstract does not say **in what material** the marker was measured, and
  that decides eligibility (for example "methylation was analysed" followed
  only by results "in cells", where the study also has a patient series);
- the abstract states **no analytic design at all** — a bare tissue or tumour
  series with no comparison, no grouping and no stated design is `unclear`,
  not an assumed cross-sectional study and not an assumed case series;
- you cannot tell the study design for any other reason;
- the abstract is absent, truncated, or uninformative.

## Who generated the data does not decide eligibility

Eligibility turns on the design and on what was measured, never on whether
the authors produced the data themselves. A secondary analysis of
individual-level human data — TCGA, GEO, a public cohort, a biobank, another
group's study — is **eligible** when the underlying participants form one of
the five designs and an eligible marker was measured in them. Secondary
analysis of existing data is ordinary epidemiology, not a lesser category.

Exclude as `not_primary` only when the record analyses **no individual-level
data at all** — that is, when it works solely from published summary
statistics or database-level aggregates. A Mendelian randomisation or
similar analysis drawing methylation associations from GWAS or mQTL summary
statistics is the clearest example.

If the abstract does not make clear which of these two it is, return
`unclear`.

## Development of an assay, classifier, or score

Tool development is a study's PURPOSE, not its design, and does not by itself
make a record ineligible.

- A classifier, signature, assay or risk score that is **developed or
  evaluated in human participants** whose grouping forms an eligible design —
  cases and controls, a diagnostic comparison series, a prognostic cohort —
  is a diagnostic-accuracy or prognostic study and is **eligible**. Judge it
  on criteria 1-6 like any other record.
- A purely technical or analytical paper with **no human evaluation sample** —
  a normalisation method, a software tool, a wet-lab protocol benchmarked
  only on reference material — is `not_primary`.

## Judging the measured-marker criterion

Judge what the study MEASURED, not what it argues or speculates about. A
study that discusses epigenetic mechanisms in its introduction or discussion,
but measures only gene expression, protein levels, or clinical outcomes, does
not measure an epigenetic marker.

Three further cases recur often enough to state explicitly:

- **Marker measured in non-human material.** If a study has human
  participants but measures the eligible marker only in animals or cell
  lines, exclude as `no_measured_marker` — criterion 1 requires the
  measurement itself to be human. Check this before applying `ncrna_only`:
  the question "was an eligible marker measured in humans" comes first.
- **Histone marks measured as a circulating protein.** A histone
  modification assayed on chromatin or in cells is eligible, including when
  the authors interpret it as a damage or inflammation readout (for example
  γ-H2AX by immunohistochemistry): judge the measurement, not the
  interpretation. A histone protein measured in plasma or serum as a
  circulating biomarker (for example citrullinated H3 as a NET marker) is a
  protein assay, not a chromatin-state measurement — exclude as
  `no_measured_marker`.
- **Sperm chromatin integrity tests** — sperm chromatin structure assay, DNA
  fragmentation index, high DNA stainability — measure DNA strand breakage
  and packaging, not a regulatory epigenetic mark. Exclude as
  `no_measured_marker`.

## Confidence

Report your confidence in the decision, 0 to 1. Be honest: low confidence
routes a record into the validation sample, which is how errors get caught.
Uniformly high confidence defeats that mechanism.

## Reason

One sentence, stating what in the record drove the decision.
