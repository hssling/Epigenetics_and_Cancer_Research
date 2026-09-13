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
| "Mean positive detection 48.9%" | Mean of `random.random()` (`scripts/fetch_pubmed_data.py:293`) |
| "SEPT9 mean positivity 66.0%" (n=1) | A single `random.random()` draw |
| `sensitivity`, `specificity` columns | `random.uniform(0.5, 0.95)` (`scripts/fetch_pubmed_data.py:295-296`) |
| Exposure effect sizes and ranking | 424 of 616 (69%) are the constant `0.3` (`scripts/prepare_master_dataset.py:88`) |
| "Median sample size 200" | 468 of 616 (76%) are the constant `200` (`scripts/prepare_master_dataset.py:92`) |
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
