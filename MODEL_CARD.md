# Model Card

## Intended use

KAIROS ranks newly accepted pickup tasks at the task-acceptance decision epoch for
a finite human review queue. The production adapter validates an Operational
Review Request, constructs the frozen causal feature schema, scores it with the
bundled model, and deterministically orders tasks for `WINDOW_REVIEW` or
`KEEP_ASSIGNMENT`. A human dispatcher owns every intervention decision.

It is not an ETA or routing system, an automatic reassignment mechanism, a worker
performance score, or evidence that an operational intervention improves outcomes.

## Frozen model

- Family: CatBoost binary context model, 300 trees (depth 6, learning rate 0.05,
  balanced class weights, seed 20260808).
- Artifact: `artifacts/kairos_final.cbm` (756,516 bytes).
- SHA-256: `b3d8f13e73d0faee1389b1a51d3db581403502d8ce85c6fca45bd6688505c315`.
- Fit: one frozen fit on 500,000 label-blind sampled actionable tasks from five
  LaDe-P cities. Raw courier, AOI, and task identities are excluded.

CatBoost is retained because the locked evaluation found stronger top-capacity
ranking than the approved logistic baseline while handling the mixed numeric and
categorical context schema. This is a description of the frozen selection, not
authorization to retrain, tune, or replace it.

## Target and information boundary

The target is pickup outside the promised window: `TOO_EARLY OR TOO_LATE`.
Production inference uses only facts known at acceptance: the newly accepted
targets, already-active context, promised windows, acceptance-time location, and
prior acceptance counters. Pickup outcomes, future GPS, completion state, labels,
and post-decision route realization fail closed. The exact 21-feature order is
recorded in `artifacts/manifest.json` and enforced in tests.

## Frozen evaluation evidence

Across four new-city holdouts, Recall@10 improved over the logistic baseline by
+4.80 to +5.70 percentage points. The aggregate paired-date bootstrap delta is
+5.23 pp with 95% CI [+4.98, +5.47]. Unseen-courier and unseen-AOI deltas are
+5.12 pp and +5.27 pp. Ten exact-pipeline label permutations have mean Recall@10
0.1012 versus 0.1837 for the real Yantai evaluation. These observational ranking
results do not establish causal intervention benefit.

Recall@10 is the frozen competition evaluation headline. Production may apply a
different dispatcher-supplied review fraction to the same deterministic ranking,
but no equivalent performance claim is made for arbitrary capacities.

## Limitations

Evidence is retrospective and Chinese; China-to-Indonesia transfer is not
established. The combined target is early-heavy. The deployment `review_score`
is an uncalibrated ordering score, not a failure probability. Dispatcher-review
impact has not been measured. Monitor target mix, score drift, review load, and
relevant group performance before any operational pilot.
