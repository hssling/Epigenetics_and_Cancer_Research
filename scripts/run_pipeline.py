#!/usr/bin/env python3

"""
Convenience runner for the full living systematic review pipeline.

The script executes the following steps in sequence from the project root:
1. Fetch latest PubMed data
2. Prepare harmonised master dataset
3. Run R-based descriptive statistics and figure generation
4. Export formatted references
5. Build the comprehensive manuscript (Markdown + embedded figures)
6. Render a DOCX manuscript via pandoc
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


RUN_STEPS = [
    ["python", "scripts/fetch_pubmed_data.py"],
    ["python", "scripts/prepare_master_dataset.py"],
    ["Rscript", "scripts/meta_analysis.R"],
    ["python", "scripts/export_references.py"],
    ["python", "scripts/build_comprehensive_manuscript.py"],
    ["pandoc", "output/Epigenetics_PublicHealth_Manuscript.md", "-o", "output/Epigenetics_PublicHealth_Manuscript.docx"],
]


def run_step(command: list[str]) -> None:
    """Execute a single pipeline command with streaming output."""
    print(f"\n>>> Running: {' '.join(command)}")
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def main() -> None:
    for step in RUN_STEPS:
        run_step(step)
    print("\nPipeline completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
