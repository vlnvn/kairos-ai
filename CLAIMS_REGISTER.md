# AI Evidence and Claims Register

The canonical values in this register are transcribed in
`artifacts/final_lock_evidence.json`. They are frozen scientific results and were
not recomputed by the product repository.

## Frozen evidence

| Evaluation | Approved baseline Recall@10 | Frozen model Recall@10 | Delta |
| --- | ---: | ---: | ---: |
| Shanghai new-city holdout | 0.1261 | 0.1804 | +5.434 pp |
| Hangzhou new-city holdout | 0.1486 | 0.2056 | +5.701 pp |
| Chongqing new-city holdout | 0.1772 | 0.2281 | +5.090 pp |
| Yantai new-city holdout | 0.1357 | 0.1837 | +4.797 pp |
| Unseen couriers | 0.1587 | 0.2100 | +5.12 pp |
| Unseen AOIs | 0.1601 | 0.2128 | +5.27 pp |

The frozen model improved on all four independent new-city holdouts. The
four-city aggregate delta is +5.23 pp with 95% CI [+4.98, +5.47]; median delta is
+5.26 pp and median relative improvement is +36.86%. Jilin is diagnostic and
non-independent: 0.165810 to 0.219275, approximately +5.35 pp.

The unseen-courier split contains 1,783 held-out couriers and 83,840 tasks with
zero group overlap. The unseen-AOI split contains 3,556 held-out AOIs and 75,995
tasks with zero group overlap. Adding raw identity features on Yantai reduced
Recall@10 by 0.88 pp; this challenges an identity-memorization explanation but is
not a fairness proof.

Ten Yantai label-permutation runs produced mean Recall@10 0.101157, SD 0.012618,
and range [0.081732, 0.120379], versus real evaluation 0.18366. No formal p-value
was computed.

The deployable-inference benchmark used 10,050 targets: p50 6.274 seconds, p95
6.667 seconds, and peak RAM 180.2 MiB. The model artifact is 756,516 bytes. The
future-free product replay remains 134 targets, 388 active context tasks, and 14
reviews at 10%; its canonical product-regression SHA-256 is
`f3bd4de96ff3b282bd01671c700fa29f72191840a0a48045c682802af6df88d8`.

Recall@10 is the frozen competition headline. Configurable operational capacity
changes only the queue cutoff and does not establish validated scientific
performance at arbitrary capacities.

## May claim

- The frozen context model outperformed the approved baseline across all four new
  independent city holdouts.
- The aggregate Recall@10 improvement is +5.23 pp with positive 95% CI
  [+4.98, +5.47].
- Generalization remained positive for held-out couriers and AOIs with zero group
  overlap in the recorded splits.
- Permutation controls were near random and below the real Yantai evaluation.
- Production inference is deterministic, future-free, and fails closed on
  forbidden outcome fields.
- The model does not require raw courier, AOI, or task identity features.
- `review_score` is used only to order tasks for finite human review capacity.

## Must not claim

- KAIROS causally improves SLA or guarantees any operational outcome.
- KAIROS reduces courier workload, cost, emissions, safety risk, or failed
  deliveries, or increases UMKM income.
- Performance has been validated in Indonesia.
- `review_score` is a calibrated probability, likelihood, confidence, or chance.
- KAIROS identifies bad couriers or evaluates worker performance.
- The identity-sensitivity result proves fairness.
- Independent late-only performance has been validated.
- KAIROS is world-first or absolutely novel.

## Limitations

- China-to-Indonesia transfer is unvalidated.
- The combined target is early-heavy; no independent late-only claim is supported.
- `review_score` is uncalibrated.
- Intervention impact is unmeasured; observational ranking evidence is not proof
  that dispatcher review improves outcomes.
- Production event-store integration has not been validated in a real logistics
  operator.

## Product regression anchor

The canonical replay was byte-identical across three approved runs. Its hash is a
product regression anchor, not historical scientific evidence.
