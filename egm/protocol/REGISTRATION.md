# Registration status

**Status: REGISTERED, APPROVED AND PUBLIC.**

| Field | Value |
|---|---|
| Registry | OSF Registries |
| **Registration ID** | **3xtf2** |
| **URL** | **https://osf.io/3xtf2** |
| **DOI** | **10.17605/OSF.IO/3XTF2** |
| Associated project | https://osf.io/zye2p |
| Template | Generalized Systematic Review Registration |
| Submitted | 2026-09-13 22:50:20 |
| Approved | 2026-09-13 |
| Visibility | Public, no embargo |
| Licence | CC-BY 4.0 |
| Protocol version registered | v1.0 (`protocol.md`) |

**Cite as:** Siddalingaiah, H.S. (2026, September 13). *Epigenetic Approaches in
Health and Public Health Practice: An Evidence Gap Map Protocol.* OSF Registries.
https://doi.org/10.17605/OSF.IO/3XTF2

Report this DOI in the PRISMA checklist (item 24a, registration and protocol) and
in the Methods of the final manuscript.

## Template choice

Registered on the **Generalized Systematic Review Registration** template rather
than Open-Ended Registration. Its sections (Review Methods, Search Strategy,
Screening, Extraction, Synthesis and Quality Assessment) map directly onto this
protocol, and the template explicitly covers "any other type of review",
including evidence maps. A structured record is more informative and more
checkable than free text.

## Venue: why not PROSPERO

PROSPERO **categorically excludes evidence gap maps**. Verified 2026-09-13 against
the current eligibility criteria at <https://www.crd.york.ac.uk/prospero/>:

> "PROSPERO prospectively registers systematic reviews with outcomes of direct
> relevance to health within humans. The following are not accepted: … Traditional
> literature reviews that use a systematic search but do not adopt other systematic
> review methods; **Evidence and gap maps**; Systematic critical appraisals or
> reviews of clinical practice guidelines… **Scoping reviews are not currently
> accepted** but may be in future."

This is a categorical exclusion by review type, not a judgement on quality. Submitting
this protocol to PROSPERO would require describing it as a review type it is not.

**PROSPERO remains relevant later.** If the nested meta-analysis (spec §7.3) turns out
to be a systematic review of intervention effects with directly health-relevant human
outcomes, that component may be separately PROSPERO-eligible. It cannot be registered
now: its scope is determined *after* coding, by the poolability rule, and registering a
review whose question we have explicitly said we cannot yet specify would be
registration in name only.

Note PROSPERO's stage rule — registration is refused once data extraction has begun.
Corpus retrieval is not extraction, so that door is still open for the nested review.

## Alternatives considered

| Registry | Accepts EGM | Free | Citable timestamped record |
|---|---|---|---|
| **OSF Registries** | Yes | Yes | Yes (DOI-able) |
| INPLASY | Yes (explicitly) | No (fee) | Yes (DOI ~48h) |
| Research Registry | Yes | No (fee) | Yes |
| Campbell Collaboration | Yes, via its own EGM pipeline | Free to submit | Editorial acceptance required, not self-service |

OSF Registries is chosen: free, citable, timestamped, and accepts the review type
honestly described. Fee-charging registries were not preferred given no funding is
recorded for this work.

## Gate

Corpus retrieval may proceed before registration — retrieval is not screening.
**GATE OPEN.** The registration is approved and public, so the registration
precondition for screening is satisfied.

The abstract-backfill precondition is also met. Completed 2026-09-13 via
efetch: 9,083 of 9,088 records now carry an abstract; 5 genuinely have none
(0.06%) and carry null rather than an empty string. Written as a new artefact,
`search/raw/pubmed_corpus_with_abstracts.json`; the original corpus is
unmodified, raw exports being append-only.

**Screening may now begin.** Remaining Plan B prerequisite (not a gate, but do
it first): `stratified_sample` has no test of its own, and Plan B uses it to draw
both the kappa-300 calibration set and the 1,000-record recall sample. A bug
there would corrupt a headline statistic.
This file is the gate.

## Investigator declarations (supplied 2026-09-13)

| Field | Value |
|---|---|
| Funding | **None** — this work is unfunded |
| Conflicts of interest | **None declared** |
| Review start date | **2026-09-13** (date the search was executed; verifiable from the corpus run manifest) |
| Anticipated completion | **2027-06-30** (estimate; amend if it slips) |
| Contact to publish | **hssling@yahoo.com** |

Paste-ready submission content: `OSF_SUBMISSION.md`.

## Stage at registration

Search executed and corpus assembled; **screening not yet begun**. No eligibility
assessment, extraction, coding or analysis has been performed. Retrieval is not
extraction, so no registry stage bar is crossed.
