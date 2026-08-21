# AI Input Health and Monitoring Specification

This specification defines signals a future consumer should observe at the frozen KAIROS AI boundary. It does not implement telemetry or prescribe platform architecture.

## Data-quality monitoring

Record counts and rates by stable `SnapshotError` category without logging sensitive request bodies:

- total requests and rejected requests;
- top-level schema, task schema/state, timestamp/window, numeric/range, coordinate-pair, counter, duplicate/missing-target, and forbidden-future-data rejections;
- missing optional acceptance-GPS rate;
- unknown `region_id` and `aoi_type` frequency relative to an approved deployment baseline;
- target-count and pending-context-count distributions;
- review-budget-fraction distribution;
- request task count and serialized request size.

No universal alert threshold is justified before operator traffic exists. Initial thresholds are `BASELINE_REQUIRED`; establish them from an approved shadow or pilot period and document any later threshold change.

## Runtime and integrity monitoring

Record model integrity failure count, scoring latency distributions, successful scoring count, and output task count. Any model integrity failure must prevent scoring and should be treated as immediately actionable. Latency thresholds are `BASELINE_REQUIRED`; repository synthetic measurements are engineering characterization, not a production SLA.

## Score-distribution monitoring

For successful requests, record descriptive statistics only: count, minimum, median, upper quantiles, maximum, and non-finite count for raw `review_score`. Never render or relabel the score as a probability, likelihood, confidence, chance, or risk percentage. Distribution shifts indicate investigation needs, not automatic model degradation.

## Model-performance monitoring

Online predictive performance cannot be measured until correctly joined post-decision outcomes become available after their natural observation delay. When labels exist, evaluate the frozen target and grouped capacity metrics with strict event-time and leakage controls. Keep performance reporting separate from input health. Do not infer Recall@10, calibration, intervention impact, or causality from unlabeled traffic.

## Ownership and response

The consumer owns collection, retention, privacy, dashboards, and alert transport. The AI owner defines field meaning and investigates model/schema integrity. Human operators retain intervention ownership. Retraining requires a new scientific protocol; monitoring alone does not authorize model changes.
