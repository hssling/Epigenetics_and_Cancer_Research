**This is a pre-screening description of the retrieved corpus, not findings.**

# Corpus description

Source artefact: `combined_corpus_v3.json`

**Total records retrieved: 9786**

## Records by source database

| source_db | records | % |
| --- | ---: | ---: |
| pubmed | 9088 | 92.9 |
| europepmc | 698 | 7.1 |

### Europe PMC records by source prefix

Derived from `source_id`. PPR = preprint, PMC = PubMed Central (non-MEDLINE), ETH = thesis, AGR = Agricola.

| prefix | records |
| --- | ---: |
| PPR | 490 |
| PMC | 189 |
| ETH | 13 |
| AGR | 6 |

## Publication year

| year | records |
| --- | ---: |
| 2015 | 527 |
| 2016 | 571 |
| 2017 | 636 |
| 2018 | 721 |
| 2019 | 793 |
| 2020 | 876 |
| 2021 | 841 |
| 2022 | 806 |
| 2023 | 717 |
| 2024 | 933 |
| 2025 | 1291 |
| 2026 | 1072 |
| year absent (null) | 0 |
| year outside 2015-2026 | 2 |

Records with no year are counted on their own row, never folded into a year bucket and never dropped: the rows above sum to 9786.

## Journals

Distinct journals: **1566**. Records with no journal recorded: **503**.

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

Records with an abstract: **9781 / 9786 (99.9%)**.

Abstract length in characters, over the 9781 records that HAVE one (records with a null abstract are excluded from these statistics, not counted as zero-length):

| statistic | characters |
| --- | ---: |
| median | 1790.0 |
| Q1 | 1557.0 |
| Q3 | 2063.5 |
| IQR | 506.5 |

Quartiles use Tukey's method (the median is excluded from both halves when n is odd), computed by sorting and indexing.

## Identifier availability

| identifier | records | % |
| --- | ---: | ---: |
| DOI | 9529 | 97.4 |
| PMID | 9088 | 92.9 |

## Deduplication

`dedup_rule` records the rule under which a record absorbed at least one duplicate; `unique` means it absorbed none.

| dedup_rule | records |
| --- | ---: |
| unique | 9596 |
| fuzzy_title | 190 |

Records built from more than one retrieved record (`len(merged_from) > 1`): **190**.

## What this is not

These are records **retrieved by the search**, before any eligibility screening. No record here has been assessed for inclusion: not one has been read against the eligibility criteria, and the corpus certainly contains records that will be excluded. None of these counts is a finding about the epigenetics literature's content, size, or gaps -- they describe what a query returned from two bibliographic databases on one day, and nothing more. Counts of journals, years or abstracts characterise retrieval, not evidence.
