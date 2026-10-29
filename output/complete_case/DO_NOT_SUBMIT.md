# ⚠️ DO NOT SUBMIT — this subset contains randomly generated values

The manuscripts and dataset in this directory are **not safe to publish**.

They present themselves as the rigorous, fallback-free subset. That is true only
of the *constant* placeholders. The randomly generated columns survived the
filter intact.

## Verified 2026-09-13

`epigenetic_master_dataset_complete.csv` (91 studies) was merged on `pmid`
against `data/epigenetic_master_dataset_python.csv`, the output of the original
fabricating pipeline:

| Column | Identical to the RNG-generated original |
|---|---:|
| `sensitivity` | **100.0%** |
| `specificity` | **100.0%** |
| `proportion_positive` | **97.8%** |

Those values originate at `scripts/fetch_pubmed_data.py:268,270-271`:

```python
'proportion_positive': round(__import__('random').random(), 2),
'sensitivity':         round(__import__('random').uniform(0.5, 0.95), 3),
'specificity':         round(__import__('random').uniform(0.5, 0.95), 3),
```

Separately, **32 of 91 effect sizes (35%) are exactly `0.95`** — an artefact of
the extractor taking the first percentage found in each abstract, which is
usually "95% CI".

## What the manuscripts report

`Complete_Case_Evidence_2024-2025.md` presents these as findings:

> "Mean positivity across biomarkers was 0.54 (median 0.58)"

> "Biomarker positivity spans 0.01-1.00, reinforcing the reproducibility of
> assay signals across collection methods"

A uniform random variable spans 0.01-1.00 by construction. The per-exposure
positivity medians (0.42, 0.71, 0.69, 0.49, 0.57, 0.57) are all RNG draws.

The abstract's claim — "Complete-case analysis confirms that reported epigenetic
effects remain clinically relevant without relying on deterministic fallbacks" —
holds only for the constants, not for these columns.

## Why the filter did not catch it

The complete-case filter removed records whose values were **missing and
substituted with a constant** (`0.3`, `200`). It could not remove values that
were **fabricated and therefore complete**. A random number has no nulls and no
missing-data footprint, so filtering for completeness selects *for* the invented
values and *against* the honest gaps.

This is why completeness is not an integrity check.

## What to use instead

Active work is in `egm/`. See `DEPRECATED.md` at the repository root and
`docs/superpowers/specs/2026-09-13-epigenetics-evidence-gap-map-design.md`.

These files are retained for transparency. They were never submitted or cited.
