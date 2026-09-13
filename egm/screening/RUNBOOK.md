# Screening runbook

Execution sequence for the registered screening procedure (OSF 3xtf2).
Each step's artefacts are committed before the next begins.

**Prerequisite:** `ANTHROPIC_API_KEY` exported, or `ant auth login` completed.
The key is read from the environment and never written to the repository.

## 1. Draw the calibration sample

    cd egm
    python -m pipeline.draw_sample calibration \
      --corpus search/raw/pubmed_corpus_with_abstracts.json \
      --out screening/calibration_300.json

Records the seed. Commit the sample.

## 2. Screen it blind

    python -m pipeline.screen_app \
      --sample screening/calibration_300.json \
      --out screening/human_calibration.jsonl \
      --stage calibration

Open http://127.0.0.1:8765/. Keys: `i` include, `e` exclude then `1`-`7`,
`u` unclear. Resumable — stop and restart freely. Roughly 1.5-2.5 hours.

**Do not run step 3 first.** Screening after seeing AI decisions is not blind,
and the registration commits to blind calibration.

## 3. Screen the same sample with each candidate model

    python -m pipeline.run_screening \
      --sample screening/calibration_300.json \
      --model claude-opus-5 \
      --out screening/ai_calibration_opus5.jsonl \
      --usage screening/usage_calibration_opus5.jsonl \
      --stage calibration

Repeat with `claude-haiku-4-5`. Expected cost: ~$1.83 and ~$0.37.
Check the usage log for actual token spend — Opus 5 runs adaptive thinking
and thinking bills as output, so the full-run projection comes from here, not
from an estimate.

## 4. Compute agreement and inspect disagreements

    python -m pipeline.report_agreement \
      --human screening/human_calibration.jsonl \
      --ai screening/ai_calibration_opus5.jsonl \
      --out screening/agreement_opus5.json

Read every disagreement. Where one reveals genuine ambiguity, revise — and
note which kind of revision it is:

- **Prompt wording only:** the AI re-screens the same 300. Your decisions stand.
- **Criteria changed:** draw a FRESH 300 with a new seed and screen it blind
  again. Your earlier decisions were made under criteria that no longer apply,
  and you have now seen the disagreements, so a re-screen would not be blind.

Record every round — seed, kappa, what was revised — in
`egm/protocol/amendments.md`.

## 5. Gate

Proceed only when kappa >= 0.75. Screen the full corpus with whichever model
has the better kappa. If the gate cannot be met after revision, the registered
contingency applies: narrow to the exposure arm (4,029 records) as a recorded
amendment.

## 6. Screen the corpus

    python -m pipeline.run_screening \
      --sample search/raw/pubmed_corpus_with_abstracts.json \
      --model <selected> \
      --out screening/screening_decisions.jsonl \
      --usage screening/usage_screening.jsonl \
      --stage screening

Resumable; interrupt freely. Route every `unclear` to yourself before
proceeding.

## 7. Draw and screen the validation sample

    python -m pipeline.draw_sample validation \
      --corpus search/raw/pubmed_corpus_with_abstracts.json \
      --decisions screening/screening_decisions.jsonl \
      --out screening/validation_1000.json

    python -m pipeline.screen_app \
      --sample screening/validation_1000.json \
      --out screening/human_validation.jsonl \
      --stage validation

Roughly 5-8 hours. This is the step that produces the published recall figure.

## 8. Compute recall

    python -m pipeline.report_recall \
      --human screening/human_validation.jsonl \
      --ai screening/screening_decisions.jsonl \
      --out screening/recall.json

Report whatever it says. The registration commits to publishing a poor recall
estimate rather than re-running until it improves; `recall.py` has no parameter
that would allow otherwise.
