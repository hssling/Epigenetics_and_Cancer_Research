# Registration status

**Status:** NOT YET REGISTERED — screening must not begin.

| Field | Value |
|---|---|
| Registry | **OSF Registries** (primary) |
| Registration ID | *pending* |
| Submitted | *pending* |
| Accepted | *pending* |
| Protocol version registered | v1.0 (`protocol.md`) |

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
**Plan B (screening) must not start until the Registration ID above is filled in.**
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
