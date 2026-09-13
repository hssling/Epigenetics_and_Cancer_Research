**This is a pre-screening description of the retrieved corpus, not findings.**

# Corpus description

Source artefact: `combined_corpus.json`

**Total records retrieved: 9968**

## Records by source database

| source_db | records | % |
| --- | ---: | ---: |
| pubmed | 9088 | 91.2 |
| europepmc | 880 | 8.8 |

### Europe PMC records by source prefix

Derived from `source_id`. PPR = preprint, PMC = PubMed Central (non-MEDLINE), ETH = thesis, AGR = Agricola.

| prefix | records |
| --- | ---: |
| PPR | 672 |
| PMC | 189 |
| ETH | 13 |
| AGR | 6 |

## Publication year

| year | records |
| --- | ---: |
| 2015 | 527 |
| 2016 | 571 |
| 2017 | 639 |
| 2018 | 725 |
| 2019 | 804 |
| 2020 | 895 |
| 2021 | 868 |
| 2022 | 839 |
| 2023 | 743 |
| 2024 | 959 |
| 2025 | 1319 |
| 2026 | 1077 |
| year absent (null) | 0 |
| year outside 2015-2026 | 2 |

Records with no year are counted on their own row, never folded into a year bucket and never dropped: the rows above sum to 9968.

## Journals

Distinct journals: **1566**. Records with no journal recorded: **685**.

Top 20 journals by record count:

| # | journal | records |
| ---: | --- | ---: |
| 1 | Clinical epigenetics | 473 |
| 2 | Scientific reports | 278 |
| 3 | Neuro-oncology | 221 |
| 4 | PloS one | 164 |
| 5 | Epigenetics | 147 |
| 6 | International journal of molecular sciences | 130 |
| 7 | BMC cancer | 118 |
| 8 | International journal of cancer | 109 |
| 9 | Clinical cancer research : an official journal of the American Association for Cancer Research | 97 |
| 10 | Oncotarget | 91 |
| 11 | Nature communications | 85 |
| 12 | Journal of neuro-oncology | 83 |
| 13 | Frontiers in immunology | 75 |
| 14 | Aging | 65 |
| 15 | Epigenomics | 64 |
| 16 | Translational psychiatry | 60 |
| 17 | Acta neuropathologica | 60 |
| 18 | Medicine | 59 |
| 19 | The journals of gerontology. Series A, Biological sciences and medical sciences | 59 |
| 20 | EBioMedicine | 58 |

## Abstract availability

Records with an abstract: **9963 / 9968 (99.9%)**.

Abstract length in characters, over the 9963 records that HAVE one (records with a null abstract are excluded from these statistics, not counted as zero-length):

| statistic | characters |
| --- | ---: |
| median | 1791.0 |
| Q1 | 1560.0 |
| Q3 | 2068.0 |
| IQR | 508.0 |

Quartiles use Tukey's method (the median is excluded from both halves when n is odd), computed by sorting and indexing.

## Identifier availability

| identifier | records | % |
| --- | ---: | ---: |
| DOI | 9711 | 97.4 |
| PMID | 9088 | 91.2 |

## Deduplication

`dedup_rule` records the rule under which a record absorbed at least one duplicate; `unique` means it absorbed none.

| dedup_rule | records |
| --- | ---: |
| unique | 9958 |
| fuzzy_title | 10 |

Records built from more than one retrieved record (`len(merged_from) > 1`): **10**.

## What this is not

These are records **retrieved by the search**, before any eligibility screening. No record here has been assessed for inclusion: not one has been read against the eligibility criteria, and the corpus certainly contains records that will be excluded. None of these counts is a finding about the epigenetics literature's content, size, or gaps -- they describe what a query returned from two bibliographic databases on one day, and nothing more. Counts of journals, years or abstracts characterise retrieval, not evidence.
