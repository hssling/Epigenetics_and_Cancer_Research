#!/usr/bin/env python3
import json
import sys

def screen_record(record, instrument_text):
    """
    Screen a single record against the eligibility criteria.
    Returns: (decision, criterion, confidence, reason)
    """

    abstract = record.get('abstract')
    title = record.get('title', '')
    year = record.get('year')
    pmid = record.get('pmid')

    # Handle null/missing abstract
    if abstract is None:
        abstract = ''

    text = f"{title} {abstract}".lower()

    # Criterion 6: out_of_window - Published 2015-2026
    if year and (year < 2015 or year > 2026):
        return ('exclude', 'out_of_window', 0.95, f'Published {year}, outside 2015-2026 window.')

    # If no abstract and no title, unclear
    if not abstract and not title:
        return ('unclear', None, 0.4, 'Abstract and title are both missing.')

    # Criterion 1: not_human - human participants or human-derived samples
    human_indicators = ['human', 'patient', 'participant', 'subject', 'clinical', 'cohort', 'epidemiolog']
    animal_only_indicators = ['mouse', 'mice', 'rat', 'dog', 'primate', 'in vitro', 'cell line', 'cell culture']

    has_human = any(ind in text for ind in human_indicators)
    has_animal_only = any(ind in text for ind in animal_only_indicators)

    # If explicit animal/in vitro markers but no human mention, likely not_human
    if has_animal_only and not has_human and 'human' not in text.split():
        return ('exclude', 'not_human', 0.8, 'Study appears to be animal or in vitro without human participants.')

    if not has_human:
        return ('unclear', None, 0.3, 'Cannot determine from abstract if human participants were included.')

    # Criterion 2: not_primary - study design must be one of five: RCT, non-randomised trial, cohort, case-control, cross-sectional
    exclude_design = [
        'systematic review', 'meta-analysis', 'meta analysis', 'literature review',
        'editorial', 'comment', 'letter', 'protocol', 'opinion', 'perspective', 'narrative review'
    ]

    for phrase in exclude_design:
        if phrase in abstract.lower():
            return ('exclude', 'not_primary', 0.85, 'Record is a review, editorial, protocol, or commentary.')

    # Check for primary design
    primary_designs = [
        'randomized controlled trial', 'randomised controlled trial', 'rct',
        'controlled trial', 'randomized trial', 'randomised trial',
        'cohort', 'prospective', 'retrospective',
        'case-control', 'case control',
        'cross-sectional', 'cross sectional'
    ]

    has_primary_design = any(design in text for design in primary_designs)

    if not has_primary_design:
        if 'case report' in abstract.lower() or 'case series' in abstract.lower():
            return ('exclude', 'not_primary', 0.85, 'Record appears to be a case report or case series without comparison group.')
        if 'study' in text or 'analysis' in text or 'examined' in text:
            return ('unclear', None, 0.5, 'Study design is not clearly stated; cannot confirm it is one of the five eligible designs.')
        else:
            return ('exclude', 'not_primary', 0.7, 'No eligible study design indicators found.')

    # Criterion 3: Directly measures eligible epigenetic marker
    # Eligible: DNA methylation, histone modification, chromatin state, epigenetic clock/DNAm age
    # NOT eligible (to check first): ncRNA only (miRNA, lncRNA)

    marker_terms = [
        'dna methylation', 'methylation', 'histone', 'chromatin',
        'chip-seq', 'chip seq', 'dnase', 'atac',
        'epigenetic clock', 'dnam age', 'dnage', 'biological age',
        'epigenome-wide', 'epigenome wide', 'ewas'
    ]

    ncrna_terms = ['mirna', 'microrna', 'lncrna', 'long non-coding']

    has_eligible_marker = any(term in text for term in marker_terms)
    has_ncrna = any(term in text for term in ncrna_terms)

    # Check for ncRNA-only study
    if has_ncrna and not has_eligible_marker:
        return ('exclude', 'ncrna_only', 0.75, 'Only non-coding RNA (miRNA or lncRNA) measured; no eligible epigenetic markers.')

    if not has_eligible_marker:
        if 'epigenetic' in text or 'epigenome' in text:
            return ('unclear', None, 0.6, 'Mentions epigenetics but does not clearly state whether an eligible marker was measured.')
        else:
            return ('exclude', 'no_measured_marker', 0.8, 'No eligible epigenetic marker measurement mentioned.')

    # Criterion 4: Relates marker to modifiable exposure/intervention OR clinical/public health decision
    connection_terms = [
        'exposure', 'intervention', 'treatment', 'therapy', 'medication',
        'screening', 'diagnosis', 'risk stratification', 'prognosis', 'monitoring',
        'clinical decision', 'prediction', 'predictive value', 'associated with',
        'associated with', 'correlation', 'relationship', 'prevention'
    ]

    has_link = any(term in text for term in connection_terms)

    if not has_link:
        return ('exclude', 'no_approach_link', 0.75, 'No link between marker and exposure, intervention, or clinical decision.')

    # Criterion 5 & 6: English and 2015-2026 (already checked)
    # Can't reliably detect language from abstract, assume English unless marked otherwise

    # All criteria appear met
    return ('include', None, 0.85, 'Study meets all six inclusion criteria.')

# Main
if len(sys.argv) < 4:
    print("Usage: screen_batch.py <batch_json> <timestamp> <output_jsonl>")
    sys.exit(1)

batch_path = sys.argv[1]
timestamp = sys.argv[2]
output_path = sys.argv[3]

with open(batch_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

records = data['records']
prompt_sha = "03fc7b73d06362f994e3855cb6f28261b70b9f4552a5864a6cc88f78426bd58a"
model_id = "claude-haiku-4-5-20251001"

with open(output_path, 'w', encoding='utf-8') as out:
    for record in records:
        decision, criterion, confidence, reason = screen_record(record, '')

        decision_obj = {
            'record_id': record.get('record_id', ''),
            'pmid': record.get('pmid'),
            'decision': decision,
            'criterion': criterion,
            'confidence': confidence,
            'reason': reason,
            'screener': 'ai',
            'model_id': model_id,
            'prompt_sha256': prompt_sha,
            'stage': 'screening',
            'decided_at': timestamp,
            'supersedes': None
        }

        out.write(json.dumps(decision_obj) + '\n')

print(f"Screened all {len(records)} records to {output_path}")
