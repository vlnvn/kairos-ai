# Model Card

## Intended use

KAIROS ranks newly accepted pickup tasks for a finite human review queue at the task-acceptance decision epoch. The historical target is pickup outside the promised window: `TOO_EARLY OR TOO_LATE`. Output is an ordered `review_score` plus `WINDOW_REVIEW` or `KEEP_ASSIGNMENT`; a human dispatcher owns every intervention.

KAIROS is not an ETA, routing, automatic-reassignment, worker-performance, probability, or causal-intervention system.

## Frozen production model

- CatBoostClassifier: 300 trees, depth 6, learning rate 0.05, balanced class weights, seed 20260808.
- Artifact: `artifacts/kairos_final.cbm`, 756,516 bytes.
- SHA-256: `b3d8f13e73d0faee1389b1a51d3db581403502d8ce85c6fca45bd6688505c315`.
- Exact 21-feature schema and categorical indices `[19, 20]` are enforced at load and scoring time.
- Raw courier, AOI, and task identities are excluded from predictive features.

The production model is frozen. Retraining, tuning, calibration, replacement, or feature changes require a new scientific protocol and evidence lock.

## Information boundary and determinism

Production inference uses facts known at acceptance: promised windows, task and acceptance-time location, prior acceptance counters, and already-active context. Pickup outcomes, future GPS, completion state, labels, and post-decision route realization fail closed. Ranking is model score descending with task ID as the deterministic tie-break. Capacity changes only the review cutoff.

`review_score` is an uncalibrated ordering score, not a probability, likelihood, confidence, chance, risk percentage, or worker score. The canonical replay is byte-stable with SHA-256 `f3bd4de96ff3b282bd01671c700fa29f72191840a0a48045c682802af6df88d8`.

## Why Recall@10

Recall@10 measures how many actual off-window tasks appear within the top 10% available for review, matching the competition demo's finite-capacity constraint. Recall@5, Recall@20, and PR-AUC are diagnostics. Other operational capacities change only the cutoff and do not inherit equivalent scientific claims.

## V1 historical frozen evidence

Exact V1 values are in `artifacts/final_lock_evidence.json`. Across four independent new-city holdouts, the frozen production model improved Recall@10 over the approved logistic baseline by +5.434 pp (Shanghai), +5.701 pp (Hangzhou), +5.090 pp (Chongqing), and +4.797 pp (Yantai). Aggregate delta was +5.23 pp with 95% CI [+4.98, +5.47]. Jilin was diagnostic and non-independent.

Zero-overlap V1 evaluations were also positive for held-out couriers (+5.12 pp) and AOIs (+5.27 pp). These are generalization results, not fairness proof. Identity sensitivity and label-permutation controls are documented in the frozen evidence artifact and Claims Register.

## V2 fixed-recipe reproducibility evidence

V2 is a separate chronological benchmark. It does not retroactively establish performance of the production V1 binary. A fresh reproduction of the fixed 21-feature CatBoost recipe was compared with the fixed logistic recipe under preregistration `research/v2_closure/PREREGISTRATION.json`.

On one-shot V2 FINAL (2022-10-05 through 2022-10-31), Logistic Recall@10 was 0.171844 and the CatBoost reproduction was 0.215867: +4.402272 pp with paired date-bootstrap 95% CI [+4.058177, +4.733675]. All five city deltas were positive. This corroborates the selected family/feature contract without changing production V1 or reopening model research.

## Inference envelope

The frozen deployable benchmark recorded 10,050 targets at p50 6.274 seconds, p95 6.667 seconds, and 180.2 MiB peak RAM. A later simplified synthetic request-structure robustness benchmark recorded approximately 0.60 seconds p50 and 0.64 seconds p95 for 10,000 independent-context targets. These are different engineering workloads, not logistics SLAs.

## Limitations

- China-to-Indonesia transfer is unvalidated.
- The combined target is early-heavy; independent late-only performance is not established.
- `review_score` is uncalibrated.
- Intervention impact is unmeasured; observational ranking does not prove review improves outcomes.
- Production event-store integration and live input baselines are unvalidated.
