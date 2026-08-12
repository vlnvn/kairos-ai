# KAIROS V2 Reproducibility Closure

## Scope and evidence boundary

This is a fixed-recipe chronological characterization, not model selection. A fresh reproduction of the frozen KAIROS CatBoost recipe and 21-feature contract was compared with the fixed V2 logistic baseline. Neither reproduction is the production V1 binary, whose historical training membership prevents eligibility for this V2 test. No production artifact, feature, target, or ranking behavior changed.

The preregistration was frozen before validation or FINAL metrics with SHA-256 `4737d10d38c70c7a26a9e4692a0c63900513fa4f3ab39704fdaf216490b01f41`.

## Dataset and protocol

The source is Cainiao-AI LaDe-P at revision `f1ddd8dd163028dd5a8ab7d7c83b198ebd2f2167`. Independently verified raw-file hashes are recorded in `dataset_manifest.json`. The audit retained 6,135,893 of 6,136,147 rows after excluding 254 acceptance-after-promised-end records.

Decision groups are fixed 15-minute city batches. TRAIN spans 2022-05-01 through 2022-09-06 and uses the prior label-blind complete-group sample of 500,589 rows. VALIDATION spans 2022-09-07 through 2022-10-04. FINAL spans 2022-10-05 through 2022-10-31. Validation and FINAL use all actionable rows.

B0 is the frozen V2 logistic pipeline with `C=1`, balanced class weights, SAGA, 100 maximum iterations, tolerance 0.001, and seed 20260810. B1 is CatBoostClassifier with 300 iterations, depth 6, learning rate 0.05, balanced class weights, Logloss, and seed 20260810. No parameter, feature, calibration, threshold, or early-stopping decision was made from either result.

## Validation characterization

| Metric | Logistic | CatBoost reproduction |
|---|---:|---:|
| Recall@5 | 0.089559 | 0.113692 |
| Recall@10 | 0.159261 | 0.198406 |
| Recall@20 | 0.284840 | 0.348142 |
| PR-AUC | 0.381162 | 0.507786 |

CatBoost minus Logistic Recall@10 was +3.914477 percentage points. The validation set contained 1,003,555 tasks and 286,705 positives. The fixed logistic fit reached its preregistered iteration ceiling; it was not modified.

## One-shot FINAL characterization

Both unchanged recipes were trained on TRAIN plus VALIDATION (1,504,144 rows) before FINAL was loaded.

| Metric | Logistic | CatBoost reproduction |
|---|---:|---:|
| Recall@5 | 0.098017 | 0.124524 |
| Recall@10 | 0.171844 | 0.215867 |
| Recall@20 | 0.302408 | 0.375388 |
| PR-AUC | 0.378613 | 0.506363 |

CatBoost minus Logistic Recall@10 was +4.402272 percentage points. The paired 2,000-replicate source-date bootstrap 95% interval was [+4.058177, +4.733675] percentage points. FINAL contained 1,009,739 tasks, 265,363 positives, and 104,491 reviewed tasks at the grouped 10% capacity rule.

Per-city CatBoost minus Logistic Recall@10 was positive in Chongqing (+4.858560 pp), Hangzhou (+4.974294 pp), Jilin (+4.045186 pp), Shanghai (+4.335534 pp), and Yantai (+3.474853 pp).

The target remained early-heavy: 246,989 EARLY positives versus 18,374 LATE positives. CatBoost Recall@10 was 0.222893 for EARLY and 0.121422 for LATE; these are diagnostics under the same global top-10% group selections, not independently optimized models.

For final rows with entities absent from TRAIN plus VALIDATION, CatBoost Recall@10 was 0.213147 across 20,080 unseen-courier positives and 0.263736 across 455 unseen-AOI positives. These results characterize group generalization and do not prove fairness.

## Interpretation

The fixed CatBoost recipe reproduced material positive Recall@10 headroom over the fixed logistic baseline on the clean chronological V2 FINAL benchmark. This supports the model-family and feature-contract choice. It does not assign the V2 result to the existing V1 binary, establish Indonesian transfer, prove intervention impact, or reopen predictive-model research.

## Reproduction

`run_closure.py` verifies the preregistration hash, refuses to overwrite either one-shot result, fixes both recipes and seeds, and separates validation from FINAL access. Processed caches and temporary model state remain outside Git. Exact metrics are in `validation_results.json` and `final_results.json`.

The first validation command was terminated by a one-second command-wrapper timeout before any result artifact was created. Process and artifact checks confirmed no surviving run or metric output; the identical locked configuration was then executed successfully. FINAL was opened once without retry.
