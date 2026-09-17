# Screening runbook

Execution sequence for the registered screening procedure (OSF 3xtf2).
Each step's artefacts are committed before the next begins.

**Corpus:** `search/raw/combined_corpus_v3.json` — 9,786 records (PubMed 9,088
+ Europe PMC 890, 192 duplicates removed). Do not screen
`pubmed_corpus_with_abstracts.json`: it predates the Europe PMC merge and
would silently drop 698 records.

**Instrument:** `pipeline/prompts/screening_v3.md`, SHA-256
`03fc7b73d06362f994e3855cb6f28261b70b9f4552a5864a6cc88f78426bd58a`.
v1 (`dbf587fc…`) and v2 (`0b2565e2…`) are superseded — see
`protocol/amendments.md`, Amendments 3 and 4. Decisions made under a superseded
instrument are retained for audit and take no part in any reported statistic.

---

## Two ways to run the AI screening

The registered design does not specify how the model is reached, only that the
model, the prompt hash and the confidence are recorded with every decision.
Both paths below satisfy that and write the same schema to the same log.

| | Path A — API | Path B — subagents |
|---|---|---|
| Needs | `ANTHROPIC_API_KEY` in the environment | nothing beyond a Claude Code session |
| Driver | `pipeline/run_screening.py` | `pipeline/prepare_batches.py` + dispatched agents + `pipeline/collect_batches.py` |
| Cost visibility | per-call usage log | none — no token accounting |
| Throughput | sequential, resumable per record | parallel, resumable per batch |

**Path B is the one that was used** for the completed run, because no API key
is available. It is not a workaround for the integrity rules: `collect_batches` enforces
set-equality between a batch's records and its decisions, rejects a decision
whose `prompt_sha256` or `model_id` disagrees with the batch, refuses to
collect a batch twice, rejects a batch whose `reason` strings look templated
rather than written per record, and writes nothing at all if any check fails.

That last check exists because it nearly mattered: an agent given 200 records
at once wrote a keyword-matching script and had it emit the whole batch with
correct provenance stamps. Every other check would have passed it.

If a key becomes available, Path A can be used for later stages without
invalidating earlier ones, provided `model_id` and `prompt_sha256` are
unchanged — the log records which is which.

---

## 1. Draw the calibration sample

    cd egm
    python -m pipeline.draw_sample calibration \
      --corpus search/raw/combined_corpus_v3.json \
      --out screening/calibration_300.json

Records the seed. Commit the sample.

## 2. Screen it blind — this is the investigator's step

    python -m pipeline.screen_app \
      --sample screening/calibration_300.json \
      --out screening/human_calibration.jsonl \
      --stage calibration

Open http://127.0.0.1:8765/. Keys: `i` include, `e` exclude then `1`-`7`,
`u` unclear. Resumable — stop and restart freely. Roughly 1.5-2.5 hours.

**Do not run step 3 first.** Screening after seeing AI decisions is not blind,
and the registration commits to blind calibration. `screen_app` cannot display
an AI decision by construction, but the ordering is yours to keep.

**No substitute exists for this step.** The registered Stage 0 gate is Cohen's
kappa between the *investigator* and the model. A second AI run measures
instrument reliability, not calibration, and must never be reported as kappa.

## 3. Screen the same sample with the model

### Path A

    python -m pipeline.run_screening \
      --sample screening/calibration_300.json \
      --model claude-sonnet-5 \
      --out screening/ai_calibration_v4.jsonl \
      --usage screening/usage_calibration_opus5.jsonl \
      --stage calibration

Expected cost ~$1.83 on Opus 5. Check the usage log for actual spend — Opus 5
runs adaptive thinking and thinking bills as output.

### Path B

    python -c "from pipeline.prepare_batches import prepare; import json; \
      prepare('search/raw/combined_corpus_v3.json','screening/batches_calib_v4',50,\
      'calibration',json.load(open('screening/calibration_300_ids.json')),'v3')"

Dispatch one agent per batch. Each agent must: read
`pipeline/prompts/screening_v3.md` in full, read only its own batch, and write
`batch_NNNN_decisions.jsonl` with all twelve schema keys on every line,
`screener: "ai"`, the model id, and the v3 hash above. Then:

    python -c "from pipeline.collect_batches import collect_all; \
      print(collect_all('screening/batches_calib_v4',\
      'screening/ai_calibration_v4.jsonl','claude-sonnet-5'))"

`collect_all` reports any batch whose decisions file is missing as `pending`
rather than skipping it silently. Re-dispatch those and collect again.

## 4. Compute agreement and inspect disagreements

    python -m pipeline.report_agreement \
      --human screening/human_calibration.jsonl \
      --ai screening/screening_decisions_sonnet.jsonl \
      --sample screening/calibration_300.json \
      --out screening/agreement_sonnet.json

`--sample` is not optional here. The human log covers the 300 calibration
records; the AI log covers all 9,786. Without it the command raises
"decision logs cover different records" — which is what this step did
until an audit tried to run it as written. The sample file names the
records the kappa is about, so the comparison population is a committed
artefact rather than whatever the two logs happen to share.

Read every disagreement. Where one reveals genuine ambiguity, revise — and
note which kind of revision it is:

- **Prompt wording only:** the AI re-screens the same 300. Your decisions stand.
- **Criteria changed:** draw a FRESH 300 with a new seed and screen it blind
  again. Your earlier decisions were made under criteria that no longer apply,
  and you have now seen the disagreements, so a re-screen would not be blind.

Record every round — seed, kappa, what was revised — in
`protocol/amendments.md`, and bump the instrument to a new version file so the
hash changes with it.

## 5. Gate  — **CURRENTLY CLOSED**

Proceed only when kappa >= 0.75. If the gate cannot be met after revision, the
registered contingency applies: narrow to the exposure arm (4,029 records) as a
recorded amendment.

## 6. Screen the corpus — **DONE**

Completed 2026-09-17: all 9,786 records, `screening_v3.md` (`03fc7b73…`),
claude-sonnet-5, in `screening/screening_decisions_sonnet.jsonl`. 98 batches of
100; every batch verified set-equal to its input before collection. Re-running
is only necessary if the Stage 0 gate fails and the instrument changes.

The commands below are kept for that case, and for the record.

### Path A

    python -m pipeline.run_screening \
      --sample search/raw/combined_corpus_v3.json \
      --model <selected> \
      --out screening/screening_decisions_api.jsonl \
      --usage screening/usage_screening.jsonl \
      --stage screening

### Path B

    python -m pipeline.prepare_batches \
      --corpus search/raw/combined_corpus_v3.json \
      --out-dir screening/batches_rerun \
      --batch-size 100 \
      --stage screening \
      --prompt-version v3

98 batches of 100. Dispatch agents as in step 3, then:

    python -c "from pipeline.collect_batches import collect_all; \
      print(collect_all('screening/batches_rerun',\
      'screening/screening_decisions_rerun.jsonl','claude-sonnet-5'))"

Both paths are resumable; interrupt freely. Route every `unclear` to yourself
before proceeding.

## 7. Draw and screen the validation sample

    python -m pipeline.draw_sample validation \
      --corpus search/raw/combined_corpus_v3.json \
      --decisions screening/screening_decisions_sonnet.jsonl \
      --batches screening/batches_screening \
      --out screening/validation_1000.json

`--batches` points at the batch files the model was actually given. The
drawn text is checked against them and the draw is refused if it has
drifted. Pointing `--corpus` at `combined_corpus.json` or `_v2.json` — the
pre-dedup corpora — reproduces the same 1,000 record_ids, but 82 of them
carry a title or abstract the model never saw. The check catches exactly
that, and refuses before writing anything.

**Already drawn** (2026-09-17): 1,000 AI-excluded records, 500 low / 300 mid /
200 high, seed 20260913. The confidence strata were reset before drawing —
`protocol/amendments.md`, Amendment 5. Redrawing needs a new seed and a new
amendment entry.

    python -m pipeline.screen_app \
      --sample screening/validation_1000.json \
      --out screening/human_validation.jsonl \
      --stage validation

Roughly 5-8 hours. This is the step that produces the published recall figure,
and like step 2 it is the investigator's own work — an AI re-screen of records
the same model already excluded measures nothing.

## 8. Compute recall

    python -m pipeline.report_recall \
      --human screening/human_validation.jsonl \
      --ai screening/screening_decisions_sonnet.jsonl \
      --sample screening/validation_1000.json \
      --out screening/recall.json

Report whatever it says. The registration commits to publishing a poor recall
estimate rather than re-running until it improves; `recall.py` has no parameter
that would allow otherwise.
