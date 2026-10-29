# OSF Registries — paste-ready submission sheet

Everything below is ready to paste. Nothing here is invented: each field is either
taken from `protocol.md` or supplied by the investigator on 2026-09-13.

**Route:** <https://osf.io> → create Project → upload `protocol.md` → Registrations →
New Registration → **Open-Ended Registration**.

Open-Ended Registration is the right template here. It timestamps whatever the project
contains — the full protocol document — without forcing the protocol into a
hypothesis-testing preregistration form built for primary studies. PROSPERO is not an
option: it excludes evidence gap maps by review type (see `REGISTRATION.md`).

---

## 1. Project metadata

**Title**
```
Epigenetic Approaches in Health and Public Health Practice: An Evidence Gap Map Protocol
```

**Category:** Project

**Description**
```
A registered protocol for an evidence gap map of human studies measuring epigenetic
markers in relation to modifiable exposures or clinical decisions, across the full
continuum of health and public health practice: health promotion, primary prevention,
screening and early detection, risk stratification, treatment and disease modification,
prognosis and monitoring, and recovery and survivorship.

The map is organised by approach rather than by disease, and covers both interventions
acting through the epigenome (nutrition, physical activity, tobacco and alcohol,
environmental exposure, psychosocial factors, perinatal exposures, epigenetic drugs)
and epigenetic measurements used to guide care (methylation screening tests, epigenetic
clocks, molecular classifiers). Evidence type is coded as a separate dimension so that
intervention effects, diagnostic accuracy and prognostic evidence remain distinguishable
within the same map.

Eligibility requires a directly measured epigenetic marker. Chain completeness is coded
as a mapped variable rather than used as an exclusion: each study is classified as
exposure-to-marker, marker-to-outcome, or the complete exposure-to-marker-to-outcome
chain. Quantifying where that chain is complete is the map's primary contribution.

A nested meta-analysis will be undertaken only where a cell of the map satisfies a
pre-specified poolability rule. If no cell qualifies, that is reported as a
pre-registered null finding.
```

**License:** CC-BY 4.0
**Public:** Yes
**Tags**
```
epigenetics; evidence gap map; DNA methylation; epigenetic clock; cancer prevention;
public health; systematic review methodology; PRISMA 2020
```

---

## 2. Contributors

| Field | Value |
|---|---|
| Name | Dr. Siddalingaiah H S |
| Role | Sole investigator; guarantor |
| Affiliation | Shridevi Institute of Medical Sciences and Research Hospital, Tumkur, India |
| Position | Professor, Community Medicine |
| Contact email | hssling@yahoo.com |

No co-investigators. AI assistance is used for title/abstract screening and full-text
field extraction with human validation, disclosed in the protocol Methods. **AI systems
are not authors** and must not be listed as contributors.

---

## 3. Investigator-supplied declarations

Supplied by the investigator on 2026-09-13:

| Field | Value |
|---|---|
| **Funding** | None. This work is unfunded. |
| **Conflicts of interest** | None declared. |
| **Review start date** | 2026-09-13 |
| **Anticipated completion** | 2027-06-30 |

The start date is the date the PubMed search was executed; it is verifiable from the
corpus run manifest (`egm/search/raw/pubmed_corpus.json`, `run_at`
2026-09-13T15:27:33Z). The completion date is an estimate sized on roughly 1,000
hand-screened records for recall validation plus full-text coding by a single
investigator. Amend the registration if it slips — OSF keeps a dated audit trail.

---

## 4. Review stage at registration

State plainly, because registries ask and honesty here is the point:

```
Search executed and corpus assembled; screening not yet begun.

A PubMed search was run on 2026-09-13 returning 9,089 records, deduplicated to
9,088. No screening, eligibility assessment, data extraction, coding or analysis
has been performed. Abstract retrieval is outstanding and must be completed before
screening can begin.
```

This is retrieval, not extraction. No registry bar is crossed by it.

---

## 5. Files to upload

| File | Purpose |
|---|---|
| `egm/protocol/protocol.md` | The protocol itself — the substantive registration |
| `egm/protocol/amendments.md` | Amendment log, empty at registration |
| `egm/search/query_executed.txt` | The exact 1,635-character executed query |
| `egm/search/prisma_counts.csv` | PRISMA counts to date (9,089 → 1 → 9,088) |
| `egm/search/count_verification.md` | Live count verification with date |

Uploading the executed query as its own file matters: it lets any reader reproduce the
retrieval exactly, rather than trusting a transcription.

---

## 6. After registration

1. Record the registration ID and DOI in `REGISTRATION.md`, replacing `*pending*`.
2. Only then may Plan B screening begin — `REGISTRATION.md` is the gate.
3. The abstract backfill is still outstanding and independently blocks screening: all
   9,088 records currently have `abstract: null`.
