# Factors Influencing Epigenetics in Cancer Prevention: Systematic Review & Meta-Analysis Automation
[![Living Review Pipeline](https://github.com/hssling/Factors-Influencing-Epigenetics-in-Cancer-Prevention-Comprehensive-Findings-2019-2025-/actions/workflows/living-review.yml/badge.svg)](https://github.com/hssling/Factors-Influencing-Epigenetics-in-Cancer-Prevention-Comprehensive-Findings-2019-2025-/actions/workflows/living-review.yml)

## Project Overview

This project implements a fully automated, verifiable pipeline for systematic review, network meta-analysis (NMA), and manuscript generation focused on **identifying factors that influence epigenetics in cancer prevention**. The system targets original studies from 2019-2025 and provides comprehensive evidence synthesis for public health decision-making.

## Research Focus

**Primary Objective**: Identify and compare modifiable factors (nutritional, behavioural, environmental, screening) that influence epigenetic markers relevant to cancer prevention.

**Key Features**:
- **Systematic Literature Search**: Advanced PubMed queries targeting original studies only
- **Network Meta-Analysis**: Comparative effectiveness of different exposure types on epigenetic outcomes
- **Data Extraction**: Automated extraction of exposure types, epigenetic markers, and quantitative outcomes
- **MCP Integration**: Model Context Protocol server for enhanced PubMed API access
- **PRISMA 2020 Compliance**: Transparent reporting and methodology

## Study Protocol

### Protocol Title
**Factors Influencing Epigenetics in Cancer Prevention: A Systematic Review and Network Meta-Analysis of Original Studies (2019-2025)**

### Protocol Registration
This protocol follows PRISMA-P 2015 guidelines and is registered with the International Prospective Register of Systematic Reviews (PROSPERO) under registration number: [To be assigned upon submission].

### Protocol Version
Version 1.0 (November 2025)

### Authors
- Principal Investigator: [Research Team Lead]
- Systematic Review Experts: [Domain Specialists]
- Statistical Analysts: [Meta-Analysis Experts]
- Technical Implementation: Automated Research Pipeline

### Background
Epigenetic modifications play a critical role in cancer development and prevention. Modifiable factors such as nutrition, behavior, environment, and screening interventions can influence epigenetic markers, potentially reducing cancer risk. However, the comparative effectiveness of these factors remains unclear. This systematic review and network meta-analysis will synthesize evidence from recent original studies to identify the most influential factors affecting epigenetics in cancer prevention.

### Objectives
**Primary Objective**: To identify and compare the effects of different modifiable factors (nutritional, behavioural, environmental, screening) on epigenetic markers relevant to cancer prevention.

**Secondary Objectives**:
1. To assess the strength of evidence for each factor type
2. To evaluate heterogeneity across studies and populations
3. To identify gaps in current research for future studies
4. To provide evidence-based recommendations for cancer prevention strategies

### Methods

#### Eligibility Criteria
**Study Designs**: Original research studies including randomized controlled trials, cohort studies, case-control studies, and cross-sectional studies with original data.

**Participants**: Human studies examining cancer prevention contexts. No restrictions on age, sex, or ethnicity.

**Interventions/Exposures**: Modifiable factors categorized as:
- Nutritional (dietary interventions, supplements)
- Behavioural (physical activity, smoking cessation, stress management)
- Environmental (pollution exposure, occupational hazards)
- Screening (early detection programs with epigenetic markers)

**Comparators**: No intervention, placebo, or alternative interventions.

**Outcomes**: Epigenetic markers including DNA methylation, histone modifications, miRNA expression, and other epigenetic changes measured quantitatively.

**Study Characteristics**:
- Publication date: January 1, 2019 to December 31, 2025
- Language: English only
- Publication type: Original research articles (excluding reviews, meta-analyses, editorials)

#### Exclusion Criteria
- Animal studies
- In vitro studies
- Reviews, meta-analyses, and systematic reviews
- Studies not focused on cancer prevention
- Non-English publications
- Studies without quantifiable epigenetic outcomes

#### Information Sources
**Primary Database**: PubMed (MEDLINE)
**Supplementary Sources**: Cochrane Library, Web of Science (for cross-referencing)
**Grey Literature**: ClinicalTrials.gov for ongoing studies

#### Search Strategy
**PubMed Query**:
```
("epigenetics"[MeSH Terms] OR "DNA methylation"[All Fields] OR "histone modification"[All Fields] OR "epigenetic"[All Fields]) AND ("cancer prevention"[All Fields] OR "neoplasms/prevention"[MeSH Terms]) AND ("risk factors"[MeSH Terms] OR "environmental exposure"[All Fields] OR "lifestyle"[All Fields] OR "nutrition"[All Fields] OR "diet"[All Fields]) AND ("2019:2025"[DP]) AND ("humans"[MeSH Terms]) AND ("english"[lang]) AND ("journal article"[Publication Type] OR "clinical trial"[Publication Type] OR "cohort studies"[MeSH Terms]) NOT ("review"[Publication Type] OR "meta-analysis"[Publication Type])
```

**Search Updates**: Monthly automated searches until manuscript submission.

#### Study Records
**Data Management**: All records imported into reference management software (Zotero) with automated deduplication.

**Selection Process**: Two independent reviewers will screen titles/abstracts, then full texts. Disagreements resolved by third reviewer.

**PRISMA Flow**: Complete documentation of screening process with exclusion reasons.

#### Data Collection Process
**Data Extraction**: Automated extraction using MCP server tools, followed by manual verification by two independent reviewers.

**Data Items**:
- Study characteristics (design, sample size, population)
- Participant demographics (age, sex, ethnicity)
- Intervention details (type, duration, intensity)
- Epigenetic outcomes (marker type, measurement method, effect size)
- Statistical measures (mean difference, odds ratio, correlation coefficient)

#### Risk of Bias Assessment
**Tool**: Cochrane ROBINS-I for non-randomized studies, Cochrane RoB 2 for RCTs.

**Assessment**: Two independent reviewers with consensus resolution.

**Domains**: Selection bias, performance bias, detection bias, attrition bias, reporting bias.

#### Effect Measures
**Primary**: Standardized mean difference (SMD) for continuous outcomes, odds ratio (OR) for binary outcomes.

**Secondary**: Correlation coefficients, regression coefficients, and other quantitative measures.

#### Synthesis Methods
**Meta-Analysis**: Random-effects model for traditional pairwise comparisons.

**Network Meta-Analysis**: Frequentist NMA using multivariate meta-analysis methods to compare all interventions simultaneously.

**Heterogeneity**: Assessed using I² statistic (>75% = substantial heterogeneity).

**Subgroup Analysis**: By cancer type, epigenetic marker, and study quality.

**Sensitivity Analysis**: Excluding low-quality studies and influential outliers.

#### Statistical Software
- R (version 4.2+) with meta, netmeta, and ggplot2 packages
- Python (version 3.8+) for MCP server implementation
- Comprehensive session logging for reproducibility

#### Confidence in Cumulative Evidence
**GRADE Approach**: Applied to NMA results to assess confidence in effect estimates.

**Factors Considered**: Risk of bias, inconsistency, indirectness, imprecision, publication bias.

### Analysis Plan
1. **Descriptive Analysis**: Study characteristics and PRISMA flow diagram
2. **Pairwise Meta-Analysis**: Direct comparisons between interventions
3. **Network Meta-Analysis**: Simultaneous comparison of all interventions
4. **Heterogeneity Assessment**: I² statistics and meta-regression
5. **Publication Bias**: Funnel plots and Egger's test
6. **Subgroup Analyses**: By cancer type, marker type, and population characteristics
7. **Sensitivity Analyses**: Impact of study quality and outliers

### Amendments
Any protocol amendments will be documented with rationale and dated. Major changes will be reflected in updated PROSPERO registration.

### Timeline
- Protocol finalization: November 2025
- Literature search: November-December 2025
- Data extraction: January 2026
- Analysis: February 2026
- Manuscript preparation: March 2026
- Submission: April 2026

### Dissemination Plan
- Publication in high-impact journal
- Conference presentations
- Policy brief for public health stakeholders
- Open access data repository

### Ethics and Dissemination
This systematic review does not require ethical approval as it synthesizes published data. All findings will be disseminated through peer-reviewed publication and made available as open access.

## Directory Structure

```
/Epigenetics_Research
├── data/
│   ├── pubmed_results.csv
│   ├── epigenetic_master_dataset.csv
│   └── prisma_counts.csv
├── scripts/
│   ├── search_pubmed.R
│   ├── meta_analysis.R
│   └── manuscript_build.R
├── figures/
│   ├── Figure1_PRISMA_Flow.png
│   ├── Figure2_ForestPlot_mSEPT9.png
│   └── Figure3_Conceptual_Model.png
├── output/
│   ├── Table1_Environmental_Signatures.csv
│   ├── Table2_Nutritional_Behavioural.csv
│   └── Epigenetics_PublicHealth_Manuscript.md
├── mcp_pubmed_server.py
├── mcp_config.json
└── README.md
```

## Technical Requirements

### R Environment
- **Core Packages**: tidyverse, meta, ggplot2, DiagrammeR, readr, dplyr, stringr
- **Analysis**: Network meta-analysis capabilities, forest plots, heterogeneity assessment

### Python Environment (for MCP Server)
- **MCP Framework**: mcp server library
- **API Integration**: urllib for PubMed E-Utilities API
- **Data Processing**: json, re for text processing

### MCP Server Configuration
```json
{
  "mcpServers": {
    "pubmed-server": {
      "command": "python",
      "args": ["mcp_pubmed_server.py"]
    }
  }
}
```

## Search Strategy

**PubMed Query** (2019-2025, original studies only):
```
("epigenetics"[MeSH Terms] OR "DNA methylation"[All Fields] OR "histone modification"[All Fields] OR "epigenetic"[All Fields]) AND ("cancer prevention"[All Fields] OR "neoplasms/prevention"[MeSH Terms]) AND ("risk factors"[MeSH Terms] OR "environmental exposure"[All Fields] OR "lifestyle"[All Fields] OR "nutrition"[All Fields] OR "diet"[All Fields]) AND ("2019:2025"[DP]) AND ("humans"[MeSH Terms]) AND ("english"[lang]) AND ("journal article"[Publication Type] OR "clinical trial"[Publication Type] OR "cohort studies"[MeSH Terms]) NOT ("review"[Publication Type] OR "meta-analysis"[Publication Type])
```

## MCP Server Tools

### 1. `pubmed_systematic_search`
- Advanced systematic search with date filtering
- Study type restrictions (original research only)
- Returns structured results with PMIDs and metadata

### 2. `extract_epigenetic_factors`
- Automated extraction of epigenetic factors from abstracts
- Categorizes exposure types and markers
- Extracts quantitative outcomes

### 3. `pubmed_meta_analysis_data`
- Structures data for meta-analysis
- Extracts effect sizes and confidence intervals
- Prepares datasets for NMA

## Usage Workflow

### 1. Literature Search
```bash
Rscript scripts/search_pubmed.R
```
- Searches PubMed with optimized query
- Applies PRISMA screening
- Extracts structured data

### 2. Meta-Analysis
```bash
Rscript scripts/meta_analysis.R
```
- Performs network meta-analysis
- Compares exposure types
- Generates figures and tables

### 3. Manuscript Generation
```bash
Rscript scripts/manuscript_build.R
```
- Compiles systematic review manuscript
- Includes NMA results
- Generates PRISMA-compliant report

## Data Integrity & Reproducibility

- **Source Verification**: All data from verified PubMed articles
- **Temporal Focus**: Latest evidence (2019-2025) from original studies
- **Traceability**: Complete PMIDs, DOIs, and extraction logs
- **PRISMA Compliance**: Transparent methodology and reporting
- **Session Logs**: Complete R/Python environment documentation

## Expected Outcomes

### Primary Findings
- **Nutritional factors**: Strongest influence on epigenetic markers
- **Behavioural interventions**: Moderate but consistent effects
- **Environmental exposures**: Variable impact by exposure type
- **Screening approaches**: Context-dependent effectiveness

### Statistical Rigor
- **Network Meta-Analysis**: Comparative effectiveness across interventions
- **Heterogeneity Assessment**: I² statistics and τ² for consistency
- **Publication Bias**: Funnel plots and Egger's test
- **Subgroup Analysis**: Effects by cancer type and marker

## Applications

- **Public Health Policy**: Evidence-based prevention strategies
- **Clinical Practice**: Targeted interventions based on epigenetic profiling
- **Research Prioritization**: Identification of high-impact modifiable factors
- **Personalized Medicine**: Epigenetic-based risk stratification

## Limitations & Future Directions

- **Current Scope**: Limited by available studies meeting criteria
- **Network Connectivity**: MCP server requires stable internet for PubMed API
- **Expansion Potential**: Framework extensible to other databases and outcomes
- **Real-time Updates**: System designed for continuous evidence synthesis

## Next Steps

- **Quantitative Extraction Audit**: Replace placeholder effect sizes, sensitivities, and specificities with manual or NLP-assisted pulls for priority studies (e.g., SEPT9 screening cohorts and high-impact environmental exposures).
- **Exposure Label Validation**: Spot-check newly classified nutritional/behavioural records to confirm regex mappings and adjust term lists where misclassified.
- **Figure & Table Integration**: Incorporate the regenerated PRISMA, forest, and conceptual figures plus updated tables into manuscript assets and dissemination materials.
- **Manuscript Refresh**: Re-run `Rscript scripts/manuscript_build.R` once quantitative refinements are complete to propagate revised results.
- **Iterative Updates**: Schedule periodic reruns of `scripts/fetch_pubmed_data.py`, `scripts/prepare_master_dataset.py`, and `scripts/meta_analysis.R` to capture new PubMed records through 2025.

## Living Review Automation

This repository is engineered as a **living** systematic review that can be re-executed end-to-end on demand or on a schedule.

- `scripts/run_pipeline.py` orchestrates the entire workflow:
  1. Pull the most recent PubMed data
  2. Harmonise datasets for analysis
  3. Execute descriptive statistics and figure generation
  4. Export formatted references
  5. Build the Markdown manuscript and render a DOCX via pandoc
- `scripts/install_r_packages.R` and `requirements.txt` describe the minimal R and Python dependencies.

To refresh the full evidence synthesis locally:

```bash
python -m pip install -r requirements.txt
Rscript scripts/install_r_packages.R
python scripts/run_pipeline.py
```

Artifacts are produced in `output/` (manuscripts, tables) and `figures/`.

## Continuous Integration / Continuous Delivery

The GitHub Actions workflow at `.github/workflows/living-review.yml` runs on every push, pull request, and a weekly cron. It:

1. Sets up Python 3.11, R, and pandoc
2. Installs system and language dependencies
3. Executes the living review pipeline
4. Publishes the refreshed manuscript, tables, and figures as build artifacts

Developers can retrieve the latest automated outputs directly from the Actions artifacts dashboard.

### Scheduled Updates

The weekly cron (`0 6 * * 1`) ensures new PubMed records through 2025 are ingested automatically, keeping the review continuously updated without manual intervention.

## Contributing & Reuse

- Fork the repository, create a feature branch, and open a pull request (the CI workflow validates builds automatically).
- Declare any additions to R/Python dependencies by updating `scripts/install_r_packages.R` or `requirements.txt`.
- For transparency, all regenerated outputs are traceable via the pipeline logs (`output/session_log.txt`).

> **Note:** Publishing the outputs to external profiles (e.g., LinkedIn/Zonedo) requires personal account access and cannot be automated within this repository. Refer to the generated `output/Epigenetics_PublicHealth_Manuscript.docx` for manual dissemination.
