# Study Protocol: Factors Influencing Epigenetics in Cancer Prevention

## A Systematic Review and Network Meta-Analysis of Original Studies (2019-2025)

**Protocol Version**: 1.0
**Date**: November 2025
**Registration**: PROSPERO [to be assigned]
**DOI**: [to be assigned]

---

## 1. ADMINISTRATIVE INFORMATION

### 1.1 Title
Factors Influencing Epigenetics in Cancer Prevention: A Systematic Review and Network Meta-Analysis of Original Studies (2019-2025)

### 1.2 Protocol Registration
This protocol is registered with the International Prospective Register of Systematic Reviews (PROSPERO) under registration number [CRD420XXXXXXX].

### 1.3 Authors and Affiliations
- **Principal Investigator**: [Research Team Lead], Department of Epidemiology, [Institution]
- **Systematic Review Lead**: [Domain Expert], Center for Cancer Prevention Research
- **Statistical Lead**: [Meta-Analysis Expert], Department of Biostatistics
- **Technical Lead**: [Data Scientist], Computational Biology Unit
- **Content Experts**: [Clinical Oncologist], [Public Health Specialist]

### 1.4 Amendments
Any amendments to this protocol will be documented with date, rationale, and impact on the review process.

---

## 2. BACKGROUND

### 2.1 Rationale
Cancer remains a leading cause of global mortality, with prevention strategies traditionally focusing on modifiable risk factors. Recent evidence indicates that epigenetic modifications—DNA methylation, histone modifications, and non-coding RNA regulation—serve as key mechanisms through which environmental, nutritional, behavioral, and screening interventions influence cancer risk.

Understanding which modifiable factors most strongly influence epigenetic processes in cancer prevention is essential for developing targeted, evidence-based interventions. While individual studies have examined specific epigenetic-cancer prevention relationships, no comprehensive synthesis comparing different intervention types exists.

### 2.2 Objectives
**Primary Objective**: To identify and compare the effects of different modifiable factors (nutritional, behavioural, environmental, screening) on epigenetic markers relevant to cancer prevention.

**Secondary Objectives**:
1. To assess the strength of evidence for each factor type using GRADE methodology
2. To evaluate heterogeneity across studies and populations
3. To identify gaps in current research for future studies
4. To provide evidence-based recommendations for cancer prevention strategies

### 2.3 Research Question
In adults at risk for cancer, which modifiable factors (nutritional, behavioural, environmental, screening) most effectively influence epigenetic markers associated with cancer prevention, and what is the comparative effectiveness of these factors?

---

## 3. METHODS

### 3.1 Eligibility Criteria

#### 3.1.1 Study Designs
- Randomized controlled trials (RCTs)
- Quasi-experimental studies
- Cohort studies (prospective and retrospective)
- Case-control studies
- Cross-sectional studies with original data
- **Exclusion**: Reviews, meta-analyses, case reports, case series, animal studies, in vitro studies

#### 3.1.2 Participants
- Human studies examining cancer prevention contexts
- No restrictions on age, sex, ethnicity, or geographic location
- Studies must include populations at risk for or undergoing cancer prevention interventions

#### 3.1.3 Interventions
Modifiable factors categorized into four main types:
- **Nutritional**: Dietary interventions, supplements, micronutrient modifications
- **Behavioural**: Physical activity, smoking cessation, stress management, sleep interventions
- **Environmental**: Pollution exposure reduction, occupational hazard mitigation, lifestyle environment modifications
- **Screening**: Early detection programs using epigenetic markers, risk stratification tools

#### 3.1.4 Comparators
- No intervention/placebo
- Standard care
- Alternative interventions
- Different doses/intensities of same intervention type

#### 3.1.5 Outcomes
**Primary Outcomes**:
- DNA methylation levels (global or gene-specific)
- Histone modification patterns
- miRNA expression profiles
- Other quantifiable epigenetic markers

**Secondary Outcomes**:
- Cancer incidence rates
- Biomarker changes (tumor markers, inflammatory markers)
- Quality of life measures
- Adverse events

#### 3.1.6 Study Characteristics
- **Publication Date**: January 1, 2019 to December 31, 2025
- **Language**: English only
- **Publication Status**: Peer-reviewed journal articles
- **Study Size**: No minimum sample size requirement
- **Follow-up Duration**: No minimum duration requirement

### 3.2 Information Sources

#### 3.2.1 Primary Database
- PubMed (MEDLINE) - comprehensive biomedical literature database

#### 3.2.2 Supplementary Sources
- Cochrane Central Register of Controlled Trials (CENTRAL)
- Web of Science Core Collection
- Scopus
- ClinicalTrials.gov (for ongoing/unpublished studies)

#### 3.2.3 Grey Literature
- Conference abstracts (if full data available)
- Government reports
- Dissertation databases

### 3.3 Search Strategy

#### 3.3.1 Primary Database: PubMed (MEDLINE)
```
("epigenetics"[MeSH Terms] OR "DNA methylation"[All Fields] OR "histone modification"[All Fields] OR "epigenetic"[All Fields]) AND ("cancer prevention"[All Fields] OR "neoplasms/prevention"[MeSH Terms]) AND ("risk factors"[MeSH Terms] OR "environmental exposure"[All Fields] OR "lifestyle"[All Fields] OR "nutrition"[All Fields] OR "diet"[All Fields]) AND ("2019:2025"[DP]) AND ("humans"[MeSH Terms]) AND ("english"[lang]) AND ("journal article"[Publication Type] OR "clinical trial"[Publication Type] OR "cohort studies"[MeSH Terms]) NOT ("review"[Publication Type] OR "meta-analysis"[Publication Type])
```

#### 3.3.2 Supplementary Databases
Complete search strategies for all databases are documented in `search_strategies.md`, including:
- Cochrane Central Register of Controlled Trials (CENTRAL)
- Web of Science Core Collection
- Scopus
- Embase (Ovid)
- CINAHL (EBSCO)
- PsycINFO
- ClinicalTrials.gov
- Grey literature sources

#### 3.3.2 Search Updates
- Monthly automated searches from protocol finalization to manuscript submission
- Final search: [Date of final search]
- All search results documented with date and yield

#### 3.3.3 Study Records

**Data Management**:
- All records imported into Zotero reference management software
- Automated deduplication using Zotero plugins
- Full-text articles stored in institutional repository

**Selection Process**:
- **Stage 1**: Title/abstract screening by two independent reviewers
- **Stage 2**: Full-text screening by two independent reviewers
- **Disagreements**: Resolved by third reviewer or consensus discussion
- **Documentation**: PRISMA flow diagram with exclusion reasons

### 3.4 Data Collection Process

#### 3.4.1 Data Extraction
**Automated Extraction**:
- MCP server tools for initial data harvesting
- Natural language processing for abstract analysis
- Structured data extraction from methods/results sections

**Manual Verification**:
- Two independent reviewers verify all automated extractions
- Third reviewer arbitrates discrepancies

#### 3.4.2 Data Items
**Study Characteristics**:
- Author, year, journal, PMID, DOI
- Study design, sample size, follow-up duration
- Population demographics (age, sex, ethnicity, country)
- Funding source, conflict of interest declarations

**Intervention Details**:
- Intervention type and categorization
- Duration, intensity, frequency
- Delivery method, setting
- Fidelity measures, adherence rates

**Outcome Data**:
- Epigenetic marker type and measurement method
- Pre/post intervention values
- Effect sizes with confidence intervals
- Statistical significance levels
- Adjustment variables

**Risk of Bias Data**:
- Assessment tool used
- Domain-specific ratings
- Overall risk of bias judgment

### 3.5 Risk of Bias Assessment

#### 3.5.1 Tools
- **RCTs**: Cochrane Risk of Bias 2 (RoB 2) tool
- **Non-randomized studies**: ROBINS-I tool
- **Diagnostic accuracy studies**: QUADAS-2 tool

#### 3.5.2 Process
- Two independent reviewers assess each study
- Training session prior to assessment
- Pilot testing on 10% of studies
- Consensus discussion for disagreements

#### 3.5.3 Domains Assessed
- Selection bias
- Performance bias
- Detection bias
- Attrition bias
- Reporting bias
- Other biases (funding, conflict of interest)

### 3.6 Effect Measures

#### 3.6.1 Primary Effect Measures
- **Continuous outcomes**: Standardized mean difference (SMD) with 95% CI
- **Binary outcomes**: Odds ratio (OR) with 95% CI
- **Correlation measures**: Pearson/Spearman correlation coefficients

#### 3.6.2 Secondary Effect Measures
- Mean difference (MD)
- Risk ratio (RR)
- Hazard ratio (HR)
- Area under curve (AUC) for diagnostic studies

### 3.7 Synthesis Methods

#### 3.7.1 Meta-Analysis Approach
- **Traditional pairwise**: Random-effects model (DerSimonian-Laird)
- **Network meta-analysis**: Frequentist multivariate meta-analysis
- **Software**: R (netmeta, meta packages), Stata (network suite)

#### 3.7.2 Statistical Methods
**Heterogeneity Assessment**:
- I² statistic (>75% = substantial heterogeneity)
- τ² (between-study variance)
- Prediction intervals for future studies

**Network Meta-Analysis**:
- Consistency assumption testing (node-splitting, design-by-treatment)
- Ranking probabilities (SUCRA values)
- Surface under the cumulative ranking curve

**Subgroup Analysis**:
- By cancer type (colorectal, breast, lung, prostate, etc.)
- By epigenetic marker type
- By study quality
- By population characteristics

**Sensitivity Analysis**:
- Exclusion of high-risk bias studies
- Different effect measure assumptions
- Different correlation structures in NMA

#### 3.7.3 Publication Bias Assessment
- Funnel plots (standard and contour-enhanced)
- Egger's regression test
- Begg's rank correlation test
- Trim-and-fill method
- Duval and Tweedie's trim-and-fill

### 3.8 Confidence in Cumulative Evidence
- **GRADE Approach**: Applied to all outcomes and comparisons
- **Factors Considered**:
  - Risk of bias
  - Inconsistency (heterogeneity)
  - Indirectness
  - Imprecision
  - Publication bias
- **Evidence Profiles**: Created for each outcome/comparison

### 3.9 Criteria for Quantitative Synthesis
- **Minimum Studies**: 3 studies per comparison for pairwise meta-analysis
- **Network Requirements**: Connected network with at least 4 interventions
- **Clinical Homogeneity**: Similar populations, interventions, outcomes
- **Statistical Homogeneity**: I² < 75% for fixed-effect models

---

## 4. ANALYSIS PLAN

### 4.1 Descriptive Analysis
- Study characteristics summary
- PRISMA flow diagram
- Network plots for NMA
- Risk of bias summary figures

### 4.2 Primary Analysis
1. **Pairwise Meta-Analyses**: Direct comparisons between interventions
2. **Network Meta-Analysis**: Simultaneous comparison of all interventions
3. **Ranking Analysis**: Probability rankings and SUCRA values

### 4.3 Secondary Analyses
1. **Subgroup Analyses**: By cancer type, marker type, study design
2. **Meta-Regression**: Explore sources of heterogeneity
3. **Sensitivity Analyses**: Impact of study quality exclusions

### 4.4 Publication Bias
1. **Visual Inspection**: Funnel plots
2. **Statistical Tests**: Egger's, Begg's tests
3. **Adjustment Methods**: Trim-and-fill, PET-PEESE

### 4.5 Software and Reproducibility
- **Primary Software**: R version 4.2+ with netmeta, meta, ggplot2 packages
- **Secondary Software**: Stata 17+ for sensitivity analyses
- **Code Repository**: GitHub with version control
- **Data Repository**: Figshare/Dryad with DOI
- **Session Logs**: Complete R/Python environment documentation

---

## 5. KNOWLEDGE USER INVOLVEMENT

### 5.1 Stakeholder Engagement
- **Public Health Agencies**: Input on research priorities and implementation
- **Clinical Oncologists**: Guidance on clinical relevance
- **Patient Advocates**: Input on patient-centered outcomes
- **Policy Makers**: Translation to public health policy

### 5.2 Knowledge Translation
- **Plain Language Summary**: For public and patients
- **Policy Brief**: For decision-makers
- **Clinical Practice Guidelines**: Integration with existing guidelines
- **Research Agenda**: Identification of future research priorities

---

## 6. TIMELINE

| Milestone | Target Date | Responsible Party |
|-----------|-------------|-------------------|
| Protocol finalization | November 2025 | Review Team |
| PROSPERO registration | November 2025 | PI |
| Literature search | November-December 2025 | Information Specialist |
| Study selection | January 2026 | Reviewers |
| Data extraction | January-February 2026 | Data Extractors |
| Risk of bias assessment | February 2026 | Quality Assessors |
| Analysis | March 2026 | Statisticians |
| Manuscript preparation | March-April 2026 | Writing Team |
| Submission | April 2026 | PI |

---

## 7. DISSEMINATION PLAN

### 7.1 Academic Dissemination
- **Primary Publication**: High-impact peer-reviewed journal
- **Conference Presentations**: Major cancer prevention conferences
- **Research Seminars**: Academic institutions

### 7.2 Knowledge Translation
- **Policy Briefs**: For public health agencies
- **Clinical Guidelines**: Integration with cancer prevention guidelines
- **Patient Resources**: Plain language summaries

### 7.3 Data Sharing
- **Open Access**: All data and code on GitHub
- **Repository**: Figshare/Dryad with DOI
- **Meta-Analysis Dataset**: Structured dataset for future research

### 7.4 Media and Public Engagement
- **Press Release**: Through institutional communications
- **Social Media**: Research highlights for public engagement
- **Stakeholder Briefings**: For policy makers and practitioners

---

## 8. ETHICS AND SAFETY

### 8.1 Research Ethics
This systematic review synthesizes published data and does not require ethical approval. All included studies must have received appropriate ethical approval.

### 8.2 Data Privacy
No individual patient data will be collected or analyzed. Only aggregate data from published studies will be used.

### 8.3 Conflict of Interest
All team members will declare potential conflicts of interest. Funding sources will be transparent.

---

## 9. MONITORING AND QUALITY ASSURANCE

### 9.1 Quality Control
- **Double Review**: All screening and extraction steps
- **Calibration Exercises**: Regular reviewer training
- **Audit Trail**: Complete documentation of decisions
- **External Review**: Methodological expert consultation

### 9.2 Progress Monitoring
- **Weekly Meetings**: Review team progress
- **Monthly Reports**: To funding agency
- **Milestone Tracking**: Gantt chart monitoring

### 9.3 Protocol Deviations
Any deviations from protocol will be documented with rationale and impact assessment.

---

## 10. REFERENCES

1. Page MJ, McKenzie JE, Bossuyt PM, et al. The PRISMA 2020 statement: an updated guideline for reporting systematic reviews. BMJ 2021;372:n71.

2. Higgins JPT, Thomas J, Chandler J, et al. Cochrane Handbook for Systematic Reviews of Interventions version 6.3 (updated February 2022). Cochrane, 2022.

3. Schünemann H, Brożek J, Guyatt G, Oxman A (eds). GRADE Handbook for Grading the Quality of Evidence and Strength of Recommendations. Updated October 2013.

4. Salanti G, Higgins JP, Ades AE, Ioannidis JP. Evaluation of networks of randomized trials. Stat Methods Med Res 2008;17:279-301.

---

## 11. FUNDING

**Funding Source**: [To be determined]
**Grant Number**: [To be assigned]
**Funding Period**: 2025-2026

---

## 12. SUPPORTING INFORMATION

### 12.1 Data Extraction Form
[Link to standardized extraction form]

### 12.2 Risk of Bias Assessment Form
[Link to assessment tools]

### 12.3 Search Strategies
[Complete search strings for all databases]

### 12.4 Code Repository
[GitHub repository with analysis code]

### 12.5 PRISMA Checklist
[Completed PRISMA 2020 checklist]

---

**Protocol Approval Date**: November 2025
**Last Updated**: November 2025
**Next Review Date**: December 2025

This protocol follows PRISMA-P 2015 guidelines and will be updated as needed throughout the review process.
