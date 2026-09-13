"""PubMed query construction (spec section 5.2).

Counts validated against live PubMed on 2026-09-13:
  core + human + (exposure OR clinical) + design + not-secondary = 11,965
  ... restricted to 2015-2026                                    =  9,089
  ... including ncRNA                                            = 21,528
"""
from pipeline.config import DATE_END, DATE_START

METHYLATION = (
    '("DNA methylation"[MeSH] OR "DNA Methylation"[tiab] OR methylome[tiab] '
    'OR EWAS[tiab] OR "epigenome-wide"[tiab] OR "CpG"[tiab] '
    'OR "5-methylcytosine"[tiab] OR "hydroxymethylation"[tiab])'
)
HISTONE = (
    '("Histone Code"[MeSH] OR "Histones"[MeSH] OR histone*[tiab] '
    'OR "chromatin"[tiab] OR "H3K4"[tiab] OR "H3K27"[tiab] OR "HDAC"[tiab] '
    'OR "histone deacetylase"[tiab])'
)
CLOCK = (
    '("epigenetic clock"[tiab] OR "epigenetic age"[tiab] OR "DNAm age"[tiab] '
    'OR "GrimAge"[tiab] OR "PhenoAge"[tiab] OR "Horvath clock"[tiab] '
    'OR "biological age"[tiab])'
)
NCRNA = (
    '("MicroRNAs"[MeSH] OR microRNA*[tiab] OR miRNA*[tiab] '
    'OR "long non-coding RNA"[tiab] OR lncRNA*[tiab])'
)
EXPOSURE = (
    '("Diet"[MeSH] OR diet*[tiab] OR nutrition*[tiab] OR supplement*[tiab] '
    'OR "Exercise"[MeSH] OR exercise[tiab] OR "physical activity"[tiab] '
    'OR "Smoking"[MeSH] OR smoking[tiab] OR tobacco[tiab] OR alcohol[tiab] '
    'OR "Environmental Exposure"[MeSH] OR "air pollution"[tiab] '
    'OR "particulate matter"[tiab] OR pesticide*[tiab] OR "heavy metal*"[tiab] '
    'OR "Stress, Psychological"[MeSH] OR "psychosocial"[tiab] OR sleep[tiab] '
    'OR "weight loss"[tiab] OR intervention*[tiab])'
)
CLINICAL_USE = (
    '(screening[tiab] OR "early detection"[tiab] OR diagnos*[tiab] '
    'OR prognos*[tiab] OR "risk prediction"[tiab] OR "risk stratification"[tiab] '
    'OR triage[tiab] OR biomarker*[tiab] OR "treatment response"[tiab] '
    'OR monitoring[tiab])'
)
HUMAN = "(humans[MeSH])"
DESIGN = (
    '("Randomized Controlled Trial"[pt] OR "Controlled Clinical Trial"[pt] '
    'OR "Clinical Trial"[pt] OR "Cohort Studies"[MeSH] '
    'OR "Case-Control Studies"[MeSH] OR "Cross-Sectional Studies"[MeSH] '
    'OR randomi*[tiab] OR cohort[tiab] OR "case-control"[tiab] OR trial[tiab])'
)
NOT_SECONDARY = (
    'NOT (review[pt] OR "systematic review"[pt] OR meta-analysis[pt] '
    "OR editorial[pt] OR comment[pt] OR letter[pt])"
)


def epigenetic_core(include_ncrna: bool = False) -> str:
    """Eligible marker concepts. ncRNA excluded by default (spec section 4.4)."""
    blocks = [METHYLATION, HISTONE, CLOCK]
    if include_ncrna:
        blocks.append(NCRNA)
    return "(" + " OR ".join(blocks) + ")"


def build_pubmed_query(include_ncrna: bool, date_limited: bool) -> str:
    """Compose the full PubMed strategy. Both flags are explicit by design."""
    parts = [
        epigenetic_core(include_ncrna),
        "AND",
        HUMAN,
        "AND",
        f"({EXPOSURE} OR {CLINICAL_USE})",
        "AND",
        DESIGN,
        NOT_SECONDARY,
    ]
    if date_limited:
        parts.append(f"AND {DATE_START}:{DATE_END}[dp]")
    return " ".join(parts)
