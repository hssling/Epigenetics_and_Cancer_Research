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

## Before submitting

Fields the protocol cannot supply, which the investigator must answer personally
(these must not be invented — see `DEPRECATED.md` for why this project takes that
seriously):

- **Funding source** — state explicitly, including "none" if unfunded
- **Conflicts of interest** — declare, including "none"
- **Anticipated start and completion dates** — the investigator's own estimate
- **Named guarantor / contact** — confirm the institutional email is the one to publish
- **Review team** — sole investigator; AI assistance is disclosed in the protocol
  Methods, and AI is not an author (spec §9.3)
