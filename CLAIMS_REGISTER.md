# AI Evidence and Claims Register

## Supported

### V1 historical frozen production evidence

- The frozen production context model improved Recall@10 over the approved logistic baseline on all four independent new-city holdouts: Shanghai +5.434 pp, Hangzhou +5.701 pp, Chongqing +5.090 pp, and Yantai +4.797 pp.
- The four-city aggregate delta was +5.23 pp with 95% CI [+4.98, +5.47].
- Recorded zero-overlap V1 splits were positive for held-out couriers (+5.12 pp) and held-out AOIs (+5.27 pp).
- The production artifact SHA-256, 21-feature schema, categorical indices, and canonical output are enforced and deterministic.

Canonical V1 values are in `artifacts/final_lock_evidence.json`.

### V2 fixed-recipe reproduction evidence

- A fresh CatBoost reproduction using the fixed KAIROS 21-feature recipe achieved V2 FINAL Recall@10 0.215867 versus 0.171844 for the fixed logistic reproduction.
- The V2 FINAL difference was +4.402272 pp with paired source-date bootstrap 95% CI [+4.058177, +4.733675].
- CatBoost minus Logistic Recall@10 was positive in all five V2 FINAL cities.
- V2 validation independently reproduced the prior fixed-control values: 0.198406 CatBoost versus 0.159261 Logistic.

Canonical V2 values are in `research/v2_closure/validation_results.json` and `final_results.json`.

### Reliability and software evidence

- Canonical inference is byte-deterministic and future-free under the tested contract.
- Malformed structures, invalid numeric/geospatial inputs, future fields, and model/schema corruption fail closed under the reliability suite.
- Capacity changes preserve ordering and scores and alter only the review cutoff.
- Synthetic 10,000-target request-structure characterization measured approximately 0.60 seconds p50 and 0.64 seconds p95 in its recorded local environment.

## Supported with qualifier

- V1 unseen-entity and V2 unseen-entity results support generalization to the recorded zero-overlap or absent-entity subsets; they do not prove fairness.
- Label-permutation and identity-sensitivity controls challenge chance-label and identity-memorization explanations; they are not causal or fairness proofs.
- Operational context added modest ranking value in V1 ablations; it is not a causal explanation of violations or worker behavior.
- V2 reproduction supports the selected CatBoost family and feature contract. It does not establish that the existing production V1 binary achieved V2 metrics because that artifact was not scientifically eligible for the V2 test.
- Synthetic and offline inference measurements characterize software execution only; they are not logistics SLAs or real-operator throughput guarantees.

## Not supported

- KAIROS causally improves SLA, guarantees outcomes, reduces workload/cost/emissions/safety risk/failed deliveries, or increases income.
- Performance has been validated in Indonesia.
- `review_score` is a probability, likelihood, confidence, chance, calibrated risk, or percentage.
- KAIROS evaluates, identifies, or disciplines workers.
- Generalization or identity tests prove fairness.
- Independent late-only performance is established.
- Dispatcher intervention impact is established.
- V2 reproduction metrics belong to the production V1 artifact.
- Synthetic software timings are production SLAs.
- KAIROS, CatBoost, delivery prediction, or task ranking is world-first or absolutely novel.

## Frozen semantics and limitations

KAIROS ranks tasks at acceptance for finite human review. `WINDOW_REVIEW` is a queue decision, not automatic reassignment. The dispatcher owns intervention. China-to-Indonesia transfer, independent late-only performance, intervention impact, and real-operator event-store integration remain unvalidated.
