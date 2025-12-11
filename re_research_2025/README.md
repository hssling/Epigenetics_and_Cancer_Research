# Factors Influencing Epigenetics in Cancer Prevention (2024-2025 Re-Research)

**Author**: Research Team (Lead: hssling)  
**Date**: December 2025  
**Version**: 2.0

## Project Overview

This module represents a targeted, high-quality "re-research" initiative focusing on the most recent evidence (2024-2025) regarding the influence of nutritional, behavioural, and environmental factors on epigenetic mechanisms in cancer prevention. Unlike previous automated pipelines, this iteration employs a refined custom extraction algorithm and rigorous manual verification to ensure data authenticity and high relevance.

## Key Outcomes

- **Systematic Analysis**: Analyzed 29 high-relevance studies from 2024-2025.
- **Nutri-Epigenetics Dominance**: Identified that 48% of recent research focuses on nutritional interventions (epi-nutrients).
- **Publication-Ready Manuscript**: Generated a full highly-detailed manuscript with tables, figures, and Vancouver-style references.
- **DAG Visualization**: Developed a Conceptual Directed Acyclic Graph (DAG) visualizing the pathway from "Exposome" to "Gene Reactivation".

## Repository Structure

```
re_research_2025/
├── assets/                 # Generated Figures (PNGs)
│   ├── Figure_1_Interventions.png
│   ├── Figure_2_Cancer_Types.png
│   └── Figure_3_DAG.png
├── data/                   # Data Store
│   ├── raw_data.xml        # Raw PubMed XML responses
│   ├── extracted_data.csv  # structured dataset
│   └── analysis_results.md # Interim analysis summary
├── scripts/                # Python processing pipeline
│   ├── fetch_data.py       # PubMed E-utilities fetcher
│   ├── analyze_data.py     # Data Parser & Classifier
│   ├── plot_data.py        # Visualization generator
│   ├── draw_dag.py         # DAG generator using Matplotlib
│   └── generate_manuscript_docx.py # Final Docx Builder
├── submission_files/       # ICMR/IJMR Submission Documents
│   ├── ijmr_first_page.docx
│   ├── Undertaking by Authors.docx
│   └── ...
├── manuscript_v2.md        # The master markdown manuscript
└── manuscript_v2_final.docx # The final submission-ready document
```

## How to Reproduce

1.  **Environment Setup**: Ensure Python 3.x is installed with `matplotlib` and `python-docx`.
2.  **Fetch Data**: Run `scripts/fetch_data.py` to get the latest xml.
3.  **Analyze**: Run `scripts/analyze_data.py` to generate the CSV.
4.  **Visualize**: Run `scripts/plot_data.py` and `scripts/draw_dag.py`.
5.  **Build Manuscript**: Run `scripts/generate_manuscript_docx.py`.

## Attribution
This research was conducted by the Research Team under the guidance of hssling. All data is sourced from NCBI PubMed and processed using custom developed algorithms.
