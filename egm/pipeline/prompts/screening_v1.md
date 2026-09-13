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
