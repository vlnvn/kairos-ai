# KAIROS AI Technical Q&A

## A. Problem formulation

### 1. Why AI rather than a simple rule?

The task is to rank many accepted pickups under finite review capacity using
interacting time-window, location, prior-acceptance, and active-context signals.
The frozen CatBoost model outperformed the approved logistic baseline on all four
independent new-city holdouts. Simple operational rules remain useful controls,
but they did not provide the locked ranking result.

### 2. Why not optimize ETA?

KAIROS does not predict travel time or plan routes. It ranks newly accepted tasks
for human promise-protection review at acceptance time. ETA optimization would be
a different target, data contract, and product.

## B. Data and target

### 3. What exactly is predicted?

The historical target is pickup outside the promised pickup window:
`TOO_EARLY OR TOO_LATE`. In production, the model emits an uncalibrated ordering
score for that combined target.

### 4. Why do you include too-early violations?

The promise defines both a start and an end. Pickup before the start and after the
end both violate the frozen promise-window target. The resulting target is
early-heavy, so no independent late-only performance claim is made.

## C. Leakage and causal information boundary

### 5. How do you know you did not leak pickup outcomes?

The 21-feature production schema contains only decision-time fields. Pickup
timestamps/GPS, labels, completion outcomes, and post-decision route realization
are rejected explicitly; temporal tests also reject targets or context accepted
after the decision timestamp.

### 6. What is the decision epoch?

The decision epoch is target-task acceptance time. Targets are newly accepted
tasks; active context must already be known at that timestamp.

## D. Model choice

### 7. Why CatBoost rather than a neural network?

The data is mixed tabular context with numeric and categorical fields. The locked
CatBoost model delivered stronger top-capacity ranking than the approved baseline
with a compact 756,516-byte artifact. A neural model was not needed to establish
the result and would add complexity without approved evidence.

### 8. Why not retrain or calibrate it now?

The scientific family, artifact, features, and results are frozen. Retraining or
probability calibration would create a different model requiring a new evidence
lock. The current task is product evidence readiness, not model optimization.

## E. Baselines

### 9. What is the approved baseline?

The approved comparison is logistic ranking under the same Recall@10 evaluation.
For example, Shanghai is 0.1261 baseline versus 0.1804 model, and Yantai is
0.1357 versus 0.1837.

### 10. How consistent is the gain over baseline?

All four new independent city holdouts improved: Shanghai +5.434 pp, Hangzhou
+5.701 pp, Chongqing +5.090 pp, and Yantai +4.797 pp. Aggregate delta is +5.23 pp
with 95% CI [+4.98, +5.47].

## F. Evaluation design

### 11. Why Recall@10?

The product allocates a finite human review budget. Recall@10 measures how many
actual off-window tasks are captured in the top 10% of the ranking, matching the
competition demo’s review capacity. It evaluates ranking quality, not probability
calibration.

### 12. What happens when review capacity changes?

The model scores and ranking stay identical. The supplied fraction changes only
the top-K `WINDOW_REVIEW` cutoff. Scientific evidence remains Recall@10; other
fractions do not inherit validated performance claims.

## G. Generalization

### 13. What generalization evidence is strongest?

The primary evidence is four independent new-city holdouts, all positive. Separate
zero-overlap splits are also positive: unseen couriers 0.1587 to 0.2100 across
1,783 couriers/83,840 tasks, and unseen AOIs 0.1601 to 0.2128 across 3,556
AOIs/75,995 tasks.

### 14. Why is Jilin not counted as an independent holdout?

Jilin is diagnostic and non-independent in the frozen design. Its result—0.165810
to 0.219275, approximately +5.35 pp—may be reported as diagnostic evidence but
not added to the four independent holdouts.

## H. Negative controls

### 15. What did permutation testing establish?

Ten exact-pipeline Yantai permutations produced mean Recall@10 0.101157, SD
0.012618, and range [0.081732, 0.120379], below the real 0.18366. This shows the
real pipeline is substantially above the near-random control. No formal p-value
was computed.

### 16. Does the negative control prove causality?

No. It challenges a chance-label explanation for ranking performance. It does not
show that dispatcher intervention causes better outcomes.

## I. Identity and worker-scoring concern

### 17. How do you know the model is not memorizing couriers?

Raw courier, AOI, and task identities are absent from the production schema. The
unseen-courier split has zero group overlap and remains positive. Adding raw
identities on Yantai reduced Recall@10 by 0.88 pp. This challenges memorization;
it is not a fairness proof.

### 18. Are you evaluating workers?

No. KAIROS ranks tasks at acceptance time, never workers. Context counts describe
current commitments and must not be presented as overload, quality, blame, or a
performance score.

## J. Inference and deployment

### 19. Is `review_score` a probability?

No. It is an uncalibrated ordering score. It must not be rendered as a percentage,
likelihood, confidence, or chance. Rank and queue decision are primary.

### 20. How fast is inference?

For 10,050 targets, the frozen benchmark measured p50 6.274 seconds, p95 6.667
seconds, and peak RAM 180.2 MiB. The artifact is 756,516 bytes. The benchmark does
not include unvalidated real-operator event-store integration.

## K. Limitations

### 21. Does your model prove intervention works?

No. The evidence is observational ranking performance. Dispatcher-review impact
is unmeasured, and the human owns the action.

### 22. Will these results transfer to Indonesia?

That is unvalidated. The evidence comes from five Chinese LaDe-P cities. An
Indonesian pilot would require transfer monitoring and outcome evaluation before
deployment-performance claims.

### 23. What are the largest scientific weaknesses left?

China-to-Indonesia transfer is unknown; the target is early-heavy; `review_score`
is uncalibrated; intervention impact and independent late-only performance are
unmeasured; and real-operator event-store integration is unvalidated.

## L. Context value and originality boundary

### 24. What is the contribution of workload/context features?

Context-over-task-only Recall@10 deltas are modest but positive: Jilin +0.31 pp,
Shanghai +1.23 pp, Hangzhou +1.14 pp, Chongqing +0.70 pp, and Yantai +0.42 pp.
This supports added ranking value, not a causal claim that workload causes failure.

### 25. What is genuinely original here?

The defensible contribution is the integration of a future-free, capacity-aware
ranking contract with human-owned promise-protection review and its frozen
evaluation. KAIROS does not claim CatBoost, delivery prediction, or task ranking
is world-first or absolutely novel.

## M. Research closure and release governance

### 26. Why did model-family research stop?

The bounded V2 search found no challenger that cleared its preregistered development gate over the CatBoost classifier control. Later safe-feature and HPO searches also failed their promotion gates. Continuing would increase adaptive-search risk without material approved headroom.

### 27. What challengers were tested in V2?

The bounded archive includes logistic controls, CatBoost direct rankers using YetiRankPairwise and LambdaMart-style ranking, and CPU DeepSets fallbacks. A PairLogitPairwise attempt failed technically before producing a metric; full set attention was not run without CUDA.

### 28. Why was LambdaMart rejected?

It was the strongest V2 challenger but reached validation Recall@10 0.192089 versus 0.198406 for the CatBoost classifier control, a -0.632 pp delta. It therefore failed the mandatory +1.50 pp development gate.

### 29. Why was DeepSets rejected?

The stronger DeepSets fallback reached 0.175337 Recall@10, 2.307 pp below the CatBoost control. It added complexity without improved evidence.

### 30. Why were richer safe features rejected?

V2.1's best safe feature set improved INNER_DEV by only +0.325 pp. That was below the preregistered material-headroom gate, so promotion validation and final remained closed.

### 31. Why was HPO candidate C23 not promoted despite improving every fold and city?

C23 improved aggregate rolling-development Recall@10 by +0.495269 pp, but the preregistered requirement was at least +0.75 pp. Consistency cannot replace the mandatory magnitude gate.

### 32. What is the difference between V1 and V2 evidence?

V1 is historical frozen evidence attached to the production binary. V2 is a later clean chronological benchmark for fresh reproductions of fixed recipes. Their numbers come from different experimental designs and must not be mixed.

### 33. Why is V2 not claimed as production-artifact performance?

The existing V1 binary has historical training-membership uncertainty relative to V2. Evaluating it on V2 FINAL could violate independence. V2 therefore trains fresh fixed-recipe reproductions and makes only recipe/contract claims.

### 34. Why is `review_score` intentionally uncalibrated?

The product needs stable ordering under finite capacity, which Recall@10 evaluates directly. Calibration was not required or validated; representing the score as probability would add an unsupported semantic claim.

### 35. What would require future retraining?

Retraining would require a separately approved protocol based on evidence such as sustained labeled performance degradation, a changed target or decision epoch, a necessary feature-contract change, or validated domain transfer. Input drift alone triggers investigation, not automatic retraining.

### 36. What should be monitored after deployment?

Monitor input rejection categories, optional-GPS missingness, categorical novelty, request/context/capacity distributions, integrity failures, latency, and descriptive score statistics. Predictive performance requires delayed outcome labels and strict event-time joins.

### 37. How would input drift be detected?

Compare monitored input and score distributions with an approved operator baseline. Thresholds are `BASELINE_REQUIRED` until real shadow or pilot traffic exists; synthetic repository data cannot define deployment alerts.

### 38. What happens if the model binary is corrupted?

SHA-256 verification fails before loading or scoring and raises `ModelArtifactError`. The consumer must fail closed and restore the approved artifact rather than bypassing integrity checks.
