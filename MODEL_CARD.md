# Model Card

## Intended use

Rank newly accepted pickup tasks at their acceptance timestamp for a fixed 10%
dispatcher review budget. Output is a non-causal risk score and one review/keep
decision. It must not autonomously reassign, reroute, penalize, or evaluate a
courier.

## Model

CatBoost binary classifier, 300 iterations, depth 6, learning rate 0.05, balanced
class weights, random seed 20260808. The 756,516-byte artifact was fitted once on
500,000 label-blind sampled actionable tasks from five LaDe-P cities. Raw courier,
AOI, and task identities are excluded.

## Evaluation

New city-held-out Recall@10 improves over logistic by +4.80 to +5.70 percentage
points in Shanghai, Hangzhou, Chongqing, and Yantai. Aggregate paired date
bootstrap delta is +5.23 pp, 95% CI [+4.98,+5.47]. Unseen-courier and unseen-AOI
deltas are +5.12 and +5.27 pp. Ten exact-pipeline permutations have mean
Recall@10 0.1012 versus real Yantai 0.1837.

## Limitations

Evidence is retrospective and Chinese; Indonesian transfer is not established.
The combined target is early-heavy, probabilities are not deployment-calibrated,
and impact of dispatcher review was not measured. Evidence summaries are
associations, not causes. Monitor label mix, score drift, review load, and group
performance before any operational pilot.

