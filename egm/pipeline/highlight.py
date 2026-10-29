"""Keyword highlighting for human screening.

The screening app shows the investigator which words in a record bear on each
eligibility criterion. This is a reading aid of the kind Rayyan and Covidence
offer, and it is deliberately dumb: fixed regular expressions, no model, no
scoring, no verdict. That is what keeps calibration blind. A model-written
summary would carry the screener's own reading of the abstract into the human
decision, and errors shared that way inflate kappa without anyone seeing it.
A keyword match shares nothing with the AI screener except the abstract.

A match is a place to look, never a judgement. "methylation" appears in
abstracts that only discuss it; "cohort" appears in reviews of cohorts. The
criteria in pipeline/prompts/screening_v3.md decide; this module only points.

Bump TERMS_VERSION whenever a term list changes, so a human log can be tied
to the highlighting that was on screen when it was written.
"""
import html
import re
from typing import NamedTuple

TERMS_VERSION = "1"


class Category(NamedTuple):
    key: str
    label: str
    criterion: str
    colour: str
    terms: tuple[str, ...]


# Order matters only for overlapping matches: the earlier category wins, so
# the specific cautions come before the general marker terms they overlap.
CATEGORIES: tuple[Category, ...] = (
    Category(
        "caution", "Rule-specific caution", "measured-marker rules", "#fde047",
        (
            r"sperm chromatin structure assay", r"SCSA", r"DNA fragmentation(?: index)?",
            r"DFI", r"(?:high )?DNA stainability", r"citrullinated histone(?: H3)?",
            r"H3Cit", r"CitH3", r"circulating (?:histones?|nucleosomes?)",
            r"Mendelian randomi[sz]ation", r"summary statistics", r"mQTL",
        ),
    ),
    Category(
        "ncrna", "ncRNA (excl. 3 if the only marker)", "3 ncrna_only", "#fdba74",
        (
            r"micro-?RNAs?", r"miRNAs?", r"miR-\d+[a-z]?(?:-[35]p)?", r"lncRNAs?",
            r"long non-?coding RNAs?", r"circRNAs?", r"circular RNAs?",
            r"non-?coding RNAs?", r"piRNAs?",
        ),
    ),
    Category(
        "marker", "Epigenetic marker", "incl. 3", "#86efac",
        (
            r"(?:hyper|hypo|de)?methylat\w*", r"CpGs?", r"EWAS", r"epigenome-wide",
            r"epigenetic (?:clocks?|age\w*)", r"DNAm ?(?:age|PhenoAge|GrimAge)?",
            r"GrimAge\d?", r"PhenoAge", r"Horvath", r"Hannum", r"DunedinPACE",
            r"DunedinPoAm", r"450[kK]", r"EPIC (?:array|BeadChip)", r"850[kK]",
            r"bisulfite\w*", r"pyrosequenc\w*", r"methylation-specific PCR", r"MSP",
            r"5-?h?mC", r"LINE-1", r"\bAlu\b", r"histones?", r"H[34]K\d+\w*",
            r"(?:de)?acetylat\w*", r"chromatin", r"ATAC-seq", r"ChIP(?:-seq)?",
            r"γ-?H2AX", r"gamma-?H2AX",
        ),
    ),
    Category(
        "nonhuman", "Non-human material", "excl. 1 / marker rule", "#fca5a5",
        (
            r"mice", r"mouse", r"murine", r"rats?", r"rodents?", r"zebrafish",
            r"porcine", r"bovine", r"canine", r"primates?", r"xenografts?",
            r"animal models?", r"in vitro", r"cell lines?", r"cultured cells",
            r"organoids?",
        ),
    ),
    Category(
        "notprimary", "Not primary / ineligible design", "excl. 2", "#d8b4fe",
        (
            r"systematic review", r"(?:narrative |scoping )?review", r"meta-analys[ie]s",
            r"case reports?", r"we (?:report|describe|present) (?:a|an|the) case",
            r"case series", r"editorial", r"commentary", r"study protocol",
            r"this protocol", r"in silico", r"position statement", r"consensus",
        ),
    ),
    Category(
        "design", "Eligible design / data source", "incl. 2", "#93c5fd",
        (
            r"randomi[sz]ed", r"controlled trial", r"RCTs?", r"(?:clinical )?trials?",
            r"cohorts?", r"case[- –]control", r"cross-sectional", r"prospective\w*",
            r"retrospective\w*", r"longitudinal\w*", r"nested", r"follow-?up",
            r"TCGA", r"GEO", r"GSE\d+", r"biobank", r"UK Biobank", r"controls",
        ),
    ),
    Category(
        "approach", "Exposure or clinical decision", "incl. 4", "#5eead4",
        (
            r"diagnos\w*", r"prognos\w*", r"screening", r"biomarkers?",
            r"risk stratification", r"predict\w*", r"survival", r"recurrence",
            r"treatment response", r"response to (?:treatment|therapy)", r"monitoring",
            r"sensitivity", r"specificity", r"AUC", r"ROC", r"exposure\w*",
            r"intervention\w*", r"smok\w*", r"alcohol", r"diet\w*",
            r"physical activity", r"exercise", r"supplement\w*", r"air pollution",
            r"PM2\.5", r"pesticides?", r"arsenic", r"prenatal", r"folate",
            r"socioeconomic", r"stress",
        ),
    ),
    Category(
        "material", "Sample material", "where measured", "#e5e7eb",
        (
            r"(?:whole |peripheral )?blood", r"plasma", r"serum", r"saliva",
            r"buccal", r"cord blood", r"placenta\w*", r"sperm\w*", r"urine",
            r"leukocytes?", r"PBMCs?", r"cfDNA", r"cell-free DNA", r"FFPE",
            r"biops(?:y|ies)", r"tumou?r tissues?", r"tissues?", r"stool",
        ),
    ),
)

_GROUP = {f"g{i}": c for i, c in enumerate(CATEGORIES)}
_PATTERN = re.compile(
    "|".join(
        f"(?P<g{i}>" + r"\b(?:" + "|".join(c.terms) + r")(?!\w)" + ")"
        for i, c in enumerate(CATEGORIES)
    ),
    re.IGNORECASE,
)

# Structured abstracts lose their line breaks in PubMed's plain text. Restoring
# them lets the eye go straight to METHODS, which is where design and material
# are stated.
_SECTION = re.compile(r"(?<!^)\s+(?=\b[A-Z][A-Z /&-]{2,40}:\s)")
_LABEL = re.compile(r"^([A-Z][A-Z /&-]{2,40}:)", re.MULTILINE)


def find(text: str) -> dict[str, list[str]]:
    """Distinct matched terms per category key, in order of first appearance."""
    found: dict[str, list[str]] = {c.key: [] for c in CATEGORIES}
    seen: dict[str, set[str]] = {c.key: set() for c in CATEGORIES}
    for m in _PATTERN.finditer(text or ""):
        key = _GROUP[m.lastgroup].key
        term = m.group(0)
        if term.lower() not in seen[key]:
            seen[key].add(term.lower())
            found[key].append(term)
    return found


def mark(text: str) -> str:
    """HTML-escaped text with each match wrapped in a coloured <mark>."""
    text = _SECTION.sub("\n", text or "")
    out: list[str] = []
    last = 0
    for m in _PATTERN.finditer(text):
        c = _GROUP[m.lastgroup]
        out.append(html.escape(text[last:m.start()]))
        out.append(
            f'<mark class="{c.key}" title="{html.escape(c.label)}">'
            f"{html.escape(m.group(0))}</mark>"
        )
        last = m.end()
    out.append(html.escape(text[last:]))
    return _LABEL.sub(r"<b>\1</b>", "".join(out))


def year_flag(year: object) -> str | None:
    """A warning when the year is outside the registered 2015-2026 window."""
    try:
        y = int(str(year))
    except (TypeError, ValueError):
        return "year not stated"
    return None if 2015 <= y <= 2026 else f"{y} is outside 2015-2026 (excl. 6)"


def styles() -> str:
    return "\n".join(
        f" mark.{c.key} {{ background:{c.colour}; border-radius:2px; padding:0 1px; }}"
        for c in CATEGORIES
    )


def signal_strip(title: str, abstract: str) -> str:
    """One row per category that matched anything, listing the matched terms."""
    found = find(f"{title}\n{abstract}")
    rows = [
        f'<tr><td><mark class="{c.key}">{html.escape(c.label)}</mark></td>'
        f"<td class=c>{html.escape(c.criterion)}</td>"
        f"<td>{html.escape(', '.join(found[c.key][:8]))}"
        f"{' …' if len(found[c.key]) > 8 else ''}</td></tr>"
        for c in CATEGORIES if found[c.key]
    ]
    if not rows:
        return '<p class="sig">No criterion keywords found — read the abstract in full.</p>'
    return f'<table class="sig">{"".join(rows)}</table>'
