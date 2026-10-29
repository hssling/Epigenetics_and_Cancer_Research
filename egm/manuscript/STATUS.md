# Manuscript status: what exists, and what does not

**Date:** 2026-10-29 (Amendment 7 filed; Amendment 8 filed; sections 1 and 4 updated)
**Registration:** OSF Registries [3xtf2](https://osf.io/3xtf2) · DOI [10.17605/OSF.IO/3XTF2](https://doi.org/10.17605/OSF.IO/3XTF2)

This document exists because the project it belongs to was created to correct a
manuscript that reported `random.random()` output as research findings. The
single most useful safeguard against repeating that is an unambiguous, current
statement of which numbers are real and which do not yet exist. That is what this
file is. It is written to be read first by anyone — including a future
contributor, or a future session of an AI assistant — who is about to describe
this project's results.

---

## 1. What has actually been done

| Stage | Status | Evidence |
|---|---|---|
| Protocol written and registered | Complete, public, no embargo | OSF 3xtf2, approved 2026-09-13 |
| PubMed search | Complete | `search/query_executed.txt`, `search/count_verification.md` |
| Europe PMC search | Complete | `search/europepmc_count_verification.md` |
| Deduplication | Complete — 9,786 records | `search/prisma_counts_combined_v3.csv` |
| ClinicalTrials.gov registry search | Complete — 694 registrations, separate stream | `search/raw/ctgov_registry.json` |
| WHO ICTRP registry search | NOT DONE — no unattended endpoint; outstanding as a **manual** step | Amendment 6 |
| Corpus characterised | Complete | `search/corpus_description.md` |
| Screening instrument | Frozen at v3, SHA-256 `03fc7b73…` | `pipeline/prompts/screening_v3.md` |
| Instrument shakedown, 2 rounds | Complete, both superseded | Amendments 3 and 4 |
| **Title/abstract screening** | **Complete — 9,786 / 9,786** | `screening/screening_decisions_sonnet.jsonl` |
| Model comparison (Opus vs Sonnet) | Complete — 94.1% on 1,700 shared | `screening/model_comparison_opus_vs_sonnet.json` |
| Validation sample drawn | Complete — 1,000, seeded | `screening/validation_1000.json` |
| Calibration: human screening of 300 | Attempted 2026-10-29; log failed the timing check; not repeated | `screening/human_calibration_INVALID_2026-10-29.jsonl` (untracked) |
| Cohen's kappa / Stage 0 gate | **WITHDRAWN** by Amendment 7 — never computed | OSF 3xtf2 update, approved 2026-10-29 |
| Validation subsample drawn (Amendment 7) | Complete — 200 (100/60/40), seed 20261029 | `screening/validation_200.json` |
| Extension rule (Amendment 8) | Filed and approved on OSF 2026-10-29 — any false negative in the 200 → screen the other 800 in one step; recall on 1,000 | `protocol/amendments.md` |
| **Recall validation: human screening of 200** | **NOT DONE — needs the investigator** | — |
| **Full-text screening** | NOT DONE | — |
| Coding schema (the extraction instrument) | Complete — built, not yet used | `pipeline/coding_schema.py` |
| **Coding / data extraction** | NOT DONE — no study coded | — |
| **Risk-of-bias assessment** | NOT DONE | — |
| **Evidence gap map** | NOT DONE | — |
| **Meta-analysis** | NOT DONE | — |

## 2. Screening is done. It is not reportable.

Every record in the corpus now has a screening decision, recorded with the
model that made it, the SHA-256 of the instrument that produced it, a
calibrated confidence, and a record-specific reason:

| decision | n | |
|---|---:|---:|
| include | 5,745 | 58.7% |
| exclude | 3,767 | 38.5% |
| unclear | 274 | 2.8% |

**None of this may be reported.** The registered gate was Cohen's kappa ≥ 0.75
against the investigator; Amendment 7 (OSF, 2026-10-29) withdrew it. The gate
is now the investigator's blind recall validation of the 200-record sample, and
it has not been done. `pipeline/report_screening.py` refuses to emit PRISMA
screening counts until it has: it recomputes recall from the investigator's
log, the AI log and the registered sample (pinned by record-id hash), and
applies the same human-screener and timing checks the kappa gate applied. A
second AI run cannot satisfy it. There is no recall threshold — a poor result
opens the gate too, and travels with the counts.

*(The three paragraphs below describe the kappa gate as built and attacked
before Amendment 7. They are kept as the record; the hardening they describe
is why the replacement recomputes from logs instead of reading a report.)*

That gate was built *before* the screening run, deliberately. Nearly ten
thousand finished decisions exert real pressure to accept them rather than
re-screen if the kappa comes out low. The gate exists so that pressure has
nowhere to act.

The gate has since been attacked deliberately, and hardened against what
landed: it recomputes kappa from the confusion matrix rather than trusting the
`gate_met` flag, verifies the decision logs still hash to what the agreement
report recorded, and refuses a "human" log whose timestamps show it was
written in one pass. What remains open is stated in METHODS Section 6.3 — a
sufficiently determined fabrication of the investigator's screening log cannot
be detected by anything running on the same filesystem. That is a limit of the
design, not an oversight in it, and the manuscript says so rather than letting
the machinery imply otherwise.

Until the gate passes, the following may not be stated anywhere:

- how many studies are eligible;
- how many studies exist for any approach, care stage, or condition domain;
- where the evidence is dense or sparse;
- what proportion of the literature completes the A→B→C chain;
- any effect estimate, pooled or otherwise;
- any sensitivity, specificity, kappa, or recall figure.

The 5,745 includes are **provisional AI decisions awaiting validation**, not a
count of eligible studies.

## 3. What the two model runs showed

1,700 records were screened twice under the identical instrument — once on
Claude Opus 5, once on Claude Sonnet 5. Raw agreement **94.1%**. Only 23 of
1,700 (1.4%) are the consequential include-vs-exclude split; most disagreements
involve `unclear`, which routes to a human either way.

This is model-selection evidence, **not calibration**. It says two models read
the instrument similarly. It says nothing about whether either agrees with the
investigator, which is the only question the registered gate asks.

## 4. What is needed next, and only you can do it

> **Superseded 2026-10-29.** Amendment 7 withdrew Step 1 and reduced Step 2
> to 200 records. The one remaining step is: screen
> `screening/validation_200.json` blind (about 1–1.5 hours), then run
> `pipeline.report_recall` against it — `screening/RUNBOOK.md`, steps 7–9.
> Once that log exists, `report_screening.py` and `render_prisma.py` will
> produce the screening counts with the recall estimate attached. The text
> below is kept as the record of the registered sequence.
>
> Amendment 8 (filed and approved 2026-10-29) fixes what happens next: if
> the 200 contain one or more
> false negatives, the counts come out marked PROVISIONAL and the other 800
> of `validation_1000.json` must be screened (RUNBOOK step 8), then step 9
> is re-run with `--extension screening/validation_1000.json`.

**Step 1 — Calibration (~1.5–2.5 hours).** Screen the 300-record calibration
sample blind in the local app:

    cd egm
    python -m pipeline.screen_app --sample screening/calibration_300.json \
      --out screening/human_calibration.jsonl --stage calibration

The app cannot display an AI decision, so blindness is structural. Then:

    python -m pipeline.report_agreement --human screening/human_calibration.jsonl \
      --ai screening/screening_decisions_sonnet.jsonl \
      --sample screening/calibration_300.json \
      --out screening/agreement_sonnet.json

(`--sample` names the 300 records the kappa is about. The human log covers
those; the AI log covers all 9,786, so without it the command refuses.)

If kappa ≥ 0.75, the gate opens and the screening counts become reportable. If
not, the registered response is to refine the instrument and re-screen — the
run is cheap to repeat now that the tooling exists.

**Step 2 — Recall validation (~5–8 hours).** Screen `screening/validation_1000.json`
blind. This produces the published recall figure and its exact confidence
interval. It is the strongest claim this review can make, and it cannot be
delegated: an AI re-screen of records the same model already excluded measures
nothing.

Full sequence in `screening/RUNBOOK.md`.

## 5. One open scope decision

At a 58.7% include rate, roughly **5,700 records** would go to full text. That
is consistent with the map stage, which is AI-assisted coding of categorical
fields, but far beyond the 30–60 studies protocol Section 5 anticipates for
manual meta-analysis extraction. The registered contingency is narrowing to the
exposure arm (4,029 records).

This does not block anything: every record is already screened, so the
narrowing is a filter applied later, not a re-run.

## 6. The rule

> A number appears in this project's outputs only if it can be traced to a
> committed artefact produced by code in `pipeline/`, and that artefact records
> the query, timestamp, model and instrument hash that produced it.

Every count in `search/` and `screening/` satisfies this. Nothing else in this
project produces numbers at all, and that is the correct state until the
investigator's screening runs.
