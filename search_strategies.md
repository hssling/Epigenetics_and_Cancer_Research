# Database Search Strategies

## Epigenetics in Cancer Prevention: Systematic Review & Meta-Analysis

**Date**: November 2025
**Protocol Version**: 1.0
**Search Date**: [To be updated with actual search dates]

---

## 1. OVERVIEW

This document contains optimized search strategies for multiple bibliographic databases to identify studies examining factors that influence epigenetics in cancer prevention contexts. All searches are designed to retrieve original research studies published between January 1, 2019 and December 31, 2025.

### Search Objectives
- Identify all original research studies on epigenetic modifications in cancer prevention
- Capture studies examining modifiable factors (nutritional, behavioral, environmental, screening)
- Include studies with quantifiable epigenetic outcomes
- Exclude reviews, meta-analyses, and non-original research

---

## 2. PUBMED (MEDLINE) SEARCH STRATEGY

### Primary Search Query
```
("epigenetics"[MeSH Terms] OR "DNA methylation"[All Fields] OR "histone modification"[All Fields] OR "epigenetic"[All Fields]) AND ("cancer prevention"[All Fields] OR "neoplasms/prevention"[MeSH Terms]) AND ("risk factors"[MeSH Terms] OR "environmental exposure"[All Fields] OR "lifestyle"[All Fields] OR "nutrition"[All Fields] OR "diet"[All Fields]) AND ("2019:2025"[DP]) AND ("humans"[MeSH Terms]) AND ("english"[lang]) AND ("journal article"[Publication Type] OR "clinical trial"[Publication Type] OR "cohort studies"[MeSH Terms]) NOT ("review"[Publication Type] OR "meta-analysis"[Publication Type])
```

### Query Components Breakdown
1. **Epigenetics Terms**:
   - "epigenetics"[MeSH Terms]
   - "DNA methylation"[All Fields]
   - "histone modification"[All Fields]
   - "epigenetic"[All Fields]

2. **Cancer Prevention Terms**:
   - "cancer prevention"[All Fields]
   - "neoplasms/prevention"[MeSH Terms]

3. **Risk Factor Terms**:
   - "risk factors"[MeSH Terms]
   - "environmental exposure"[All Fields]
   - "lifestyle"[All Fields]
   - "nutrition"[All Fields]
   - "diet"[All Fields]

4. **Date Filter**: "2019:2025"[DP]

5. **Study Type Filters**:
   - "humans"[MeSH Terms]
   - "english"[lang]
   - "journal article"[Publication Type]
   - "clinical trial"[Publication Type]
   - "cohort studies"[MeSH Terms]

6. **Exclusion Filters**:
   - NOT "review"[Publication Type]
   - NOT "meta-analysis"[Publication Type]

### PubMed Limits Applied
- Date range: 2019/01/01 - 2025/12/31
- Languages: English
- Species: Humans
- Publication types: Journal Article, Clinical Trial, Cohort Study
- Exclude: Review, Meta-Analysis

---

## 3. COCHRANE CENTRAL REGISTER OF CONTROLLED TRIALS (CENTRAL)

### Search Strategy
```
#1 MeSH descriptor: [Epigenesis, Genetic] explode all trees
#2 epigenet* OR "DNA methylation" OR "histone modification" OR "histone methylation" OR "histone acetylation" OR miRNA OR microRNA
#3 #1 OR #2
#4 MeSH descriptor: [Neoplasms] explode all trees
#5 MeSH descriptor: [Primary Prevention] explode all trees
#6 cancer prevention OR neoplasm prevention OR cancer risk reduction
#7 #4 OR #5 OR #6
#8 MeSH descriptor: [Risk Factors] explode all trees
#9 nutrition* OR diet* OR lifestyle OR behaviour* OR behavioral OR environmental exposure OR screening OR early detection
#10 #8 OR #9
#11 #3 AND #7 AND #10
#12 #11 AND (2019* OR 2020* OR 2021* OR 2022* OR 2023* OR 2024* OR 2025*)
```

### CENTRAL Limits
- Publication Year: 2019-2025
- Language: English
- Study type: Trials

---

## 4. WEB OF SCIENCE CORE COLLECTION

### Topic Search (TS) Field
```
TS=((epigenet* OR "DNA methylation" OR "histone modification" OR "histone methylation" OR "histone acetylation" OR miRNA OR microRNA) AND (cancer prevention OR neoplasm prevention OR "primary prevention" OR "risk reduction") AND (nutrition* OR diet* OR lifestyle OR behaviour* OR behavioral OR "environmental exposure" OR screening OR "early detection"))
```

### Timespan
- 2019-2025

### Refinements Applied
- Document Types: Article, Clinical Trial, Cohort Study
- Languages: English
- Exclude: Review, Editorial, Letter, News Item

### Web of Science Categories
- ONCOLOGY
- PUBLIC, ENVIRONMENTAL & OCCUPATIONAL HEALTH
- NUTRITION & DIETETICS
- ENDOCRINOLOGY & METABOLISM

---

## 5. SCOPUS

### Article Title, Abstract, Keywords Search
```
TITLE-ABS-KEY((epigenet* OR "DNA methylation" OR "histone modification" OR "histone methylation" OR "histone acetylation" OR miRNA OR microRNA) AND (cancer prevention OR neoplasm prevention OR "primary prevention" OR "risk reduction") AND (nutrition* OR diet* OR lifestyle OR behaviour* OR behavioral OR "environmental exposure" OR screening OR "early detection"))
```

### Scopus Limits
- Document Type: Article, Review, Conference Paper
- Source Type: Journal
- Language: English
- Publication Year: 2019-2025
- Subject Area: Medicine, Biochemistry, Genetics and Molecular Biology, Health Sciences

### Exclude Document Types
- Review
- Editorial
- Letter
- Note
- Short Survey

---

## 6. EMBASE (OVID)

### Emtree and Keyword Search
```
1. exp epigenetics/
2. epigenet*.tw.
3. DNA methylation.tw.
4. histone modification.tw.
5. histone methylation.tw.
6. histone acetylation.tw.
7. miRNA.tw.
8. microRNA.tw.
9. 1 or 2 or 3 or 4 or 5 or 6 or 7 or 8
10. exp neoplasms/
11. exp cancer prevention/
12. cancer prevention.tw.
13. neoplasm prevention.tw.
14. primary prevention.tw.
15. risk reduction.tw.
16. 10 or 11 or 12 or 13 or 14 or 15
17. exp risk factors/
18. nutrition*.tw.
19. diet*.tw.
20. lifestyle.tw.
21. behaviour*.tw.
22. behavioral.tw.
23. environmental exposure.tw.
24. screening.tw.
25. early detection.tw.
26. 17 or 18 or 19 or 20 or 21 or 22 or 23 or 24 or 25
27. 9 and 16 and 26
28. limit 27 to (english language and yr="2019 - 2025")
29. limit 28 to human
30. limit 29 to (article or clinical trial or cohort analysis)
```

### Embase Limits
- Publication Year: 2019-2025
- Language: English
- Species: Human
- Document Type: Article, Clinical Trial, Cohort Analysis

---

## 7. CINAHL (EBSCO)

### Search Query
```
S1 (MH "Epigenetics+") OR TI epigenet* OR AB epigenet* OR TI "DNA methylation" OR AB "DNA methylation" OR TI "histone modification" OR AB "histone modification" OR TI miRNA OR AB miRNA OR TI microRNA OR AB microRNA

S2 (MH "Neoplasms+") OR (MH "Cancer Prevention+") OR TI "cancer prevention" OR AB "cancer prevention" OR TI "neoplasm prevention" OR AB "neoplasm prevention" OR TI "primary prevention" OR AB "primary prevention"

S3 (MH "Risk Factors+") OR TI nutrition* OR AB nutrition* OR TI diet* OR AB diet* OR TI lifestyle OR AB lifestyle OR TI behaviour* OR AB behaviour* OR TI behavioral OR AB behavioral OR TI "environmental exposure" OR AB "environmental exposure" OR TI screening OR AB screening OR TI "early detection" OR AB "early detection"

S4 S1 AND S2 AND S3

S5 S4 AND LA English

S6 S5 AND PD 20190101-20251231

S7 S6 AND PT Academic Journal
```

### CINAHL Limits
- Publication Date: 2019-2025
- Language: English
- Source Types: Academic Journals
- Exclude: Reviews, Editorials, Letters

---

## 8. PSYCHINFO (APA)

### Search Strategy
```
1. epigenetics OR epigenetic* OR "DNA methylation" OR "histone modification" OR miRNA OR microRNA
2. cancer prevention OR neoplasm prevention OR primary prevention OR risk reduction
3. nutrition* OR diet* OR lifestyle OR behaviour* OR behavioral OR environmental exposure OR screening OR early detection
4. 1 AND 2 AND 3
5. Limit to: Publication Year: 2019-2025, English Language, Human, Peer Reviewed
```

### PsycINFO Limits
- Publication Year: 2019-2025
- Methodology: Empirical Study
- Population: Human
- Language: English
- Document Type: Journal Article

---

## 9. CLINICALTRIALS.GOV

### Search Terms
```
epigenetics AND cancer prevention AND (nutrition OR diet OR lifestyle OR behavior OR environmental OR screening)
```

### Filters Applied
- Study Type: Interventional Studies (Clinical Trials)
- Conditions: Neoplasms, Cancer
- Status: Completed, Recruiting, Active
- Date Range: 2019-2025
- Countries: All

---

## 10. PROSPERO

### Search for Ongoing/Completed Reviews
```
epigenetics AND cancer prevention
```

### Filters
- Status: Ongoing, Completed
- Date: 2019-2025

---

## 11. GREY LITERATURE SEARCHES

### 1. OpenGrey
```
epigenetics cancer prevention nutrition lifestyle environmental screening
```

### 2. Grey Literature Report (New York Academy of Medicine)
```
(epigenetics OR "DNA methylation") AND (cancer prevention OR "neoplasm prevention") AND (nutrition OR diet OR lifestyle OR behavior OR environmental OR screening)
```

### 3. National Technical Information Service (NTIS)
```
epigenetics AND cancer AND prevention AND (nutrition OR diet OR lifestyle OR behavior OR environmental OR screening)
```

---

## 12. SEARCH MANAGEMENT AND DEDUPLICATION

### Software Tools
- **Reference Management**: Zotero with deduplication plugins
- **Deduplication**: Automatic deduplication followed by manual verification
- **PRISMA Flow**: Complete documentation of screening process

### Search Documentation
- **Date of Search**: [To be recorded for each database]
- **Total Results**: [To be recorded for each database]
- **Database Interface**: [Web/OVID/API version used]
- **Search Filters**: Complete record of all applied limits

### Update Searches
- **Frequency**: Monthly searches until manuscript submission
- **Documentation**: All update searches logged with dates and yields
- **Integration**: New records integrated into existing workflow

---

## 13. QUALITY CONTROL

### Search Validation
- **Peer Review**: All search strategies reviewed by information specialist
- **Test Searches**: Validation against known relevant studies
- **Sensitivity**: Strategies designed for high sensitivity
- **Precision**: Balanced with practical screening workload

### Documentation Standards
- **Complete Recording**: All search strategies with dates and results
- **Reproducibility**: Exact strings and parameters recorded
- **Transparency**: All search decisions documented

---

## 14. SUPPLEMENTARY SEARCH METHODS

### Citation Searching
- **Key Papers**: Forward and backward citation searching for included studies
- **Software**: Web of Science Cited Reference Search
- **Scope**: First authors and recent high-impact papers

### Expert Consultation
- **Content Experts**: Consultation with epigenetic and cancer prevention specialists
- **Reference Lists**: Hand-searching of reference lists from included studies
- **Conference Abstracts**: Recent conference proceedings in relevant fields

---

## 15. SEARCH LOG TEMPLATE

| Database | Search Date | Search String | Total Results | Relevant After Screening | Notes |
|----------|-------------|---------------|---------------|--------------------------|-------|
| PubMed | YYYY-MM-DD | [Complete query] | XXX | XX | [Any issues/notes] |
| Cochrane | YYYY-MM-DD | [Complete query] | XXX | XX | [Any issues/notes] |
| Web of Science | YYYY-MM-DD | [Complete query] | XXX | XX | [Any issues/notes] |
| Scopus | YYYY-MM-DD | [Complete query] | XXX | XX | [Any issues/notes] |
| Embase | YYYY-MM-DD | [Complete query] | XXX | XX | [Any issues/notes] |

---

**Search Strategy Version**: 1.0
**Date Created**: November 2025
**Last Updated**: November 2025
**Protocol Reference**: PROSPERO [to be assigned]

This document provides comprehensive search strategies optimized for each database's unique syntax and functionality while maintaining consistent conceptual coverage across all sources.
