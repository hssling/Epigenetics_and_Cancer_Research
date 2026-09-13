# Manuscript status: what exists, and what does not

**Date:** 2026-09-14
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
| Protocol written | Complete | `protocol/protocol.md`, v1.0 |
| Protocol registered | Complete, public, no embargo | OSF 3xtf2, approved 2026-09-13 |
| PubMed search executed | Complete | `search/query_executed.txt`, `search/count_verification.md` |
| PubMed abstracts retrieved | Complete | `search/raw/pubmed_corpus_with_abstracts.json` |
| Europe PMC search executed | Complete | `search/europepmc_count_verification.md` |
| Deduplication | Complete | `search/prisma_counts_combined_v2.csv` |
| Corpus characterised | Complete | `search/corpus_description.md` |
| Screening instrument frozen | Complete | `pipeline/prompts/screening_v1.md`, SHA-256 recorded |
| Screening software built and tested | Complete | `pipeline/`, full test suite |
| **Calibration (Cohen's kappa)** | **NOT DONE** | — |
| **Title/abstract screening** | **NOT DONE** | — |
| **Recall validation** | **NOT DONE** | — |
| **Full-text screening** | **NOT DONE** | — |
| **Coding / data extraction** | **NOT DONE** | — |
| **Risk-of-bias assessment** | **NOT DONE** | — |
| **Evidence gap map** | **NOT DONE** | — |
| **Meta-analysis** | **NOT DONE** | — |

## 2. There are no findings

**No record in this corpus has been assessed for eligibility.** Not one.

Everything in `search/corpus_description.md` is a description of *what the search
retrieved*: how many records, published in which years, in which journals, how
many carry an abstract. Those are properties of a database query. They are not
properties of the epigenetics literature, and they are not results.

In particular, none of the following may be stated, in a manuscript, an abstract,
a grant application, or a conversation:

- how many studies are eligible;
- how many studies exist for any approach, care stage, or condition domain;
- where the evidence is dense or sparse;
- what proportion of the literature completes the A->B->C chain;
- any effect estimate, pooled or otherwise;
- any sensitivity, specificity, kappa, or recall figure.

Each of those is an *output of screening*, and screening has not run. A number
offered for any of them today would be invented. That is the precise failure this
project was created to correct, and it would be worse the second time, because
the corrective apparatus is sitting right here unused.

## 3. Why screening has not run

The registered design screens titles and abstracts with an AI model (protocol
Section 5, Stage 1), calibrated against the investigator to Cohen's kappa >= 0.75
and validated by hand-screening a 1,000-record stratified sample of AI-exclusions.

The software for all three stages is built, tested, and committed. It cannot be
executed because **no API key is available for the model**, and the investigator
has stated that none will be provided. Without it, Stage 1 does not run slowly —
it does not run at all.

The registered fallback is manual screening. At a realistic 30 seconds per
title/abstract, the full corpus is roughly 83 hours of the investigator's
attention. Restricting to the exposure arm alone (4,029 records, protocol Section
4.3) is roughly 34 hours. Both are feasible; neither is quick; and the choice
between them is the investigator's to make, not an implementation detail.

The screening interface for exactly this — a local, keyboard-driven,
one-record-at-a-time reviewer that writes an append-only decision log with the
same integrity guarantees as the AI path — is built and documented in
`screening/RUNBOOK.md`. It is the unblocking path that does not depend on
anything the investigator does not already have.

## 4. What could legitimately be published today

Two things, and they are worth saying out loud because "no findings" is not the
same as "nothing to publish":

**A registered protocol / methods paper.** The protocol is complete, registered,
public, and describes a design with features most reviews do not have: a
quantified recall estimate with an exact confidence interval rather than an
unmeasured claim of dual review, chain completeness treated as a mapped variable
rather than an exclusion, and machine-enforced integrity rules that make the
prior failure mode unrepresentable. Several journals publish systematic review
and evidence-map protocols as a standalone article type.

**Nothing else.** Specifically, the corpus description is *not* a bibliometric
paper. It is one database query's output with no screening, no classification,
and no validation behind it. The superseded `re_research_2025/` module in this
repository made exactly that mistake — presenting an unscreened bibliometric
snapshot as a systematic review — and it is quarantined for it.

## 5. The rule

> A number appears in this project's outputs only if it can be traced to a
> committed artefact produced by code in `pipeline/`, and that artefact records
> the query, timestamp, and tool version that produced it.

Every count in `search/` satisfies this. Nothing else in this project currently
produces numbers at all, and that is the correct state until screening runs.
