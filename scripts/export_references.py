#!/usr/bin/env python3

"""
Export formatted references for all unique studies in the master dataset.
"""

from __future__ import annotations

import csv
from collections import OrderedDict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MASTER_DATASET = PROJECT_ROOT / "data" / "epigenetic_master_dataset.csv"
OUTPUT_PATH = PROJECT_ROOT / "output" / "references_formatted.txt"


def main() -> None:
    if not MASTER_DATASET.exists():
        raise FileNotFoundError(f"Dataset not found: {MASTER_DATASET}")

    unique_refs: "OrderedDict[str, tuple[str, str, str, str, str]]" = OrderedDict()

    with MASTER_DATASET.open(encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            pmid = row.get("pmid", "").strip()
            if not pmid or pmid in unique_refs:
                continue

            authors = row.get("authors", "").replace(";", ",").strip()
            year = row.get("year", "").strip() or "2024"
            title = row.get("title", "").strip()
            journal = row.get("journal", "").strip() or "Journal not specified"
            doi = row.get("doi", "").strip()

            unique_refs[pmid] = (authors, year, title, journal, doi)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as outfile:
        for index, (pmid, (authors, year, title, journal, doi)) in enumerate(unique_refs.items(), start=1):
            doi_text = doi if doi else "N/A"
            citation = (
                f"{index}. {authors} ({year}). {title}. {journal}. "
                f"DOI: {doi_text}. PMID: {pmid}."
            )
            outfile.write(citation + "\n")

    print(f"Wrote {len(unique_refs)} formatted references to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
