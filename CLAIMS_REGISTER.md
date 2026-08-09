# AI Evidence and Claims Register

This is the canonical product-repository evidence sheet for the frozen AI
artifact. Values below are copied only from approved, already-tracked frozen
documentation and the artifact manifest; no metric was recomputed in product
code.

## Frozen evidence

| Evidence | Approved result |
| --- | --- |
| Dataset scope | 6,135,893 actionable records across five audited cities |
| Four new-city holdouts | CatBoost Recall@10 improvement over logistic: +4.80 to +5.70 pp |
| Aggregate paired-date bootstrap | +5.23 pp; 95% CI [+4.98, +5.47] |
| Unseen courier | +5.12 pp |
| Unseen AOI | +5.27 pp |
| Permutation control | 10 exact-pipeline permutations: mean Recall@10 0.1012; real Yantai 0.1837 |
| Frozen model | 300-tree CatBoost; SHA-256 `b3d8f13e73d0faee1389b1a51d3db581403502d8ce85c6fca45bd6688505c315` |

The locally available approved files do not contain the four individual
baseline-to-model Recall@10 pairs, the unseen-courier and unseen-AOI baseline/model
pairs, or the frozen inference resource measurement. Those values must be copied
verbatim from the missing final-lock source pack before this sheet can be treated
as release-complete evidence.

## Product regression anchor

The approved future-free replay contains 134 targets and deterministically emits
14 `WINDOW_REVIEW` decisions. Its post-lock canonical product output uses UTF-8
JSON with sorted keys and compact separators and has SHA-256
`f3bd4de96ff3b282bd01671c700fa29f72191840a0a48045c682802af6df88d8`.
This is a product regression anchor, not new scientific evidence. The historical
ranked artifact for the previously recorded hash was unavailable after a bounded
search.

## May claim

- KAIROS ranks accepted pickup tasks associated with higher early-or-late
  promised-window risk on held-out public LaDe-P cities.
- It prioritizes a finite human review queue and deterministically emits
  `WINDOW_REVIEW` or `KEEP_ASSIGNMENT`.
- The frozen context model outperformed the approved logistic baseline in four
  new-city holdouts and passed the recorded permutation controls.
- Production inference does not require pickup outcomes or future events.

`review_score` is an uncalibrated ordering score, not a failure probability.
Observational ranking performance is not proof that dispatcher intervention
improves real-world outcomes; the human owns the operational decision.

## Must not claim

- Guaranteed SLA improvement or causal intervention benefit.
- Cost, emissions, safety, income, or failed-delivery reductions.
- Validated Indonesian or national performance.
- Accurate independent late-only prediction.
- Automatic routing, reassignment, or worker performance scoring.
- Causal explanations, "world first", or absolute novelty.

## Known limitations

- China-to-Indonesia transfer is unvalidated.
- The combined target is early-heavy.
- The deployment score is uncalibrated.
- Intervention impact is unmeasured.
