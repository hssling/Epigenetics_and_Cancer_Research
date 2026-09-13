# Europe PMC Query Count Verification

## Verification Date
2026-09-14

## Query Configuration
- `exclude_medline`: True (`NOT SRC:MED` appended)
- Date limit: PUB_YEAR 2015–2026 (expressed as `PUB_YEAR:[2015 TO 2026]`)
- `resultType`: core (required — `lite` omits `abstractText`)
- Every free-text term restricted to `(TITLE:x OR ABSTRACT:x)`, mirroring
  PubMed's `[tiab]`

## Observed Count
- hitCount, all sources: 5,982
- hitCount, `NOT SRC:MED`: **890**
- Records retrieved: **890**
- Drift between hitCount and records retrieved: **0**

## Expected Count
890 (probed live 2026-09-14, `.superpowers/sdd/2026-09-13-egm-screening/epmc-query-probe.py`)

## Status
✓ VERIFIED — retrieved count matches the probed count exactly (890 = 890), and
the all-sources denominator reproduces exactly as well (5,982 = 5,982).

## Was SRC:MED excluded?
**Yes, deliberately.** PubMed/MEDLINE was searched natively on 2026-09-13
(9,088 deduplicated records) with a precise field-tagged strategy. Europe PMC
is the recorded substitution for Embase (OSF 3xtf2; no institutional access)
and is included for the coverage it adds **beyond** MEDLINE. Fetching MEDLINE
records here and deduplicating would import records the registered PubMed
strategy deliberately excluded via `[pt]` and `[MeSH]` filters
(`NOT (review[pt] OR ... OR letter[pt])`, `humans[MeSH]`) that Europe PMC's
query syntax cannot express — silently loosening a registered strategy.

## Source Breakdown
Computed from the `source_id` prefixes of the 890 fetched records
(`source_id` is `{source}:{id}`, because Europe PMC ids are unique only
within a source).

| Source | Meaning | Records | Share |
|---|---|---:|---:|
| PPR | Preprint | 672 | 75.5% |
| PMC | PMC-only (not MEDLINE-indexed) | 194 | 21.8% |
| ETH | Thesis / dissertation | 13 | 1.5% |
| AGR | Agricola | 11 | 1.2% |
| **Total** | | **890** | **100%** |

PPR (672) and PMC (194) reproduce the probed sub-counts exactly. ETH and AGR
were not broken out in the probe; they are the remaining 24 records.

## Abstract Coverage
- Records carrying an abstract: **890 of 890 (100%)**
- Records without an abstract: 0
- Median abstract length: 1,971 characters

No backfill step is needed for this corpus: unlike PubMed esummary, Europe PMC
`resultType=core` returns `abstractText` in the search response itself.

## Field Completeness
Absences below are stated as `null` / `[]` in the artefact; nothing is
substituted for missing data.

| Field | Present | Absent | Note |
|---|---:|---:|---|
| title | 890 | 0 | required — an absent or blank title raises |
| abstract | 890 | 0 | |
| year | 890 | 0 | range 2015–2026 |
| doi | 675 | 215 | |
| pmid | 0 | 890 | expected: `NOT SRC:MED` excludes MEDLINE-indexed records |
| journal | 205 | 685 | 685 = 672 preprints + 13 theses, which have no journal |
| authors | 836 | 54 | 54 records carry no `authorString` |

`source_id` is unique across all 890 records (no collisions).

## Query Details
- Query length: 3,199 characters
- Query hash: `f1d786a11bc2`
- Query as executed: `egm/search/europepmc_query_executed.txt`
- Endpoint: `https://www.ebi.ac.uk/europepmc/webservices/rest/search`
- Data source: live Europe PMC REST API, `format=json`, `resultType=core`,
  `pageSize=1000`, cursorMark pagination
- Rate limit: 0.34 seconds between pages
- Authentication: none. Europe PMC requires no API key and none was sent.
- Artefact: `egm/search/raw/europepmc_corpus.json`

## Why terms are wrapped in TITLE:/ABSTRACT:
Europe PMC free-text terms search **full text**, not title/abstract. The
identical strategy left unwrapped returns 239,868 records — roughly 40× this
corpus. Wrapping each term as `(TITLE:x OR ABSTRACT:x)` is what makes the
strategy comparable to the registered PubMed `[tiab]` search. This is load
bearing; simplifying it away silently inflates the corpus.
