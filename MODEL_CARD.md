# Model Card

## Intended use and prediction target

KAIROS ranks newly accepted pickup tasks for a finite human review queue at the
task-acceptance decision epoch. The target is pickup outside the promised pickup
window: `TOO_EARLY OR TOO_LATE`. Output is an ordered `review_score` plus
`WINDOW_REVIEW` or `KEEP_ASSIGNMENT`; a human dispatcher owns every intervention.

It is not an ETA, routing, automatic reassignment, worker-performance, or causal
intervention system.

## Frozen model

- CatBoost binary context model: 300 trees, depth 6, learning rate 0.05, balanced
  class weights, seed 20260808.
- Artifact: `artifacts/kairos_final.cbm`, 756,516 bytes.
- SHA-256: `b3d8f13e73d0faee1389b1a51d3db581403502d8ce85c6fca45bd6688505c315`.
- Fit once on 500,000 label-blind sampled actionable tasks from five LaDe-P
  cities. Raw courier, AOI, and task identities are excluded.

CatBoost is frozen because it outperformed the approved logistic baseline for
top-capacity ranking while handling the mixed numeric and categorical schema. A
neural model was not needed to establish the locked result. This is not
authorization to retrain, tune, calibrate, or replace the model.

## Information boundary

The exact 21-feature order is recorded in `artifacts/manifest.json` and enforced
in tests. Production inference uses only facts known at acceptance: promised
windows, target and acceptance-time location, prior acceptance counters, and
already-active context. Pickup outcomes, future GPS, completion state, labels,
and post-decision route realization fail closed.

## Evaluation design

Exact machine-readable frozen values are recorded in
`artifacts/final_lock_evidence.json`.

Recall@10 matches the competition product constraint: evaluate how many actual
off-window pickups appear in the top 10% available for review. Other operational
review fractions change only the cutoff and do not carry equivalent scientific
performance claims.

| New independent city | Logistic baseline | Frozen model | Delta |
| --- | ---: | ---: | ---: |
| Shanghai | 0.1261 | 0.1804 | +5.434 pp |
| Hangzhou | 0.1486 | 0.2056 | +5.701 pp |
| Chongqing | 0.1772 | 0.2281 | +5.090 pp |
| Yantai | 0.1357 | 0.1837 | +4.797 pp |

All four improved. Aggregate delta is +5.23 pp with 95% CI [+4.98, +5.47].
Jilin is diagnostic and non-independent: 0.165810 to 0.219275, approximately
+5.35 pp, and is not counted among the four holdouts.

Held-out-courier Recall@10 is 0.1587 to 0.2100 (+5.12 pp) across 1,783
couriers/83,840 tasks with zero overlap. Held-out-AOI Recall@10 is 0.1601 to
0.2128 (+5.27 pp) across 3,556 AOIs/75,995 tasks with zero overlap.

Adding raw identities on Yantai reduced Recall@10 by 0.88 pp. This challenges
identity memorization as the source of model headroom, but does not prove
fairness. Ten label permutations produced mean Recall@10 0.101157 (SD 0.012618,
range [0.081732, 0.120379]) versus real 0.18366; no formal p-value was computed.

Context-over-task-only deltas are modest and positive: Jilin +0.31 pp, Shanghai
+1.23 pp, Hangzhou +1.14 pp, Chongqing +0.70 pp, and Yantai +0.42 pp. This is
additional ranking value, not a causal workload effect.

## Score semantics and inference

`review_score` is an uncalibrated ordering score, not a probability, likelihood,
confidence, or worker score. Ranking is by model score descending with a stable
task-ID tie-break; capacity changes only the top-K decision cutoff.

For 10,050 targets, frozen inference measured p50 6.274 seconds, p95 6.667
seconds, and peak RAM 180.2 MiB. Production inference is future-free and rejects
forbidden outcome fields.

## Limitations

- China-to-Indonesia transfer is unvalidated.
- The combined target is early-heavy; independent late-only performance is not
  established.
- `review_score` is uncalibrated.
- Intervention impact is unmeasured; observational ranking performance is not
  proof that review improves outcomes.
- Production event-store integration has not been validated with a real operator.
