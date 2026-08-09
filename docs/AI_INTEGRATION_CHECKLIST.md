# AI Integration Checklist

Use this checklist when integrating the frozen KAIROS AI boundary. It is a handoff
contract, not backend or frontend implementation guidance.

## Backend may rely on

- `KairosRanker.score` as the frozen synchronous ranking boundary.
- A validated Operational Review Request containing the decision timestamp,
  newly accepted targets, already-known active context, and
  `review_budget_fraction`.
- Deterministic ordering by model score descending with task ID as tie-breaker.
- `WINDOW_REVIEW` as the top-K prefix and `KEEP_ASSIGNMENT` otherwise.
- `review_score` as an uncalibrated ordering score only.

## Backend must preserve

- The exact 21-feature builder inside the AI adapter; do not reconstruct features
  in API code.
- Fail-closed rejection of future/outcome fields and post-decision context.
- Rank, priority, decision, raw `review_score`, evidence signals, and the engine’s
  human-ownership notice.
- Request fraction and response metadata: `review_budget_fraction`,
  `review_budget_count`, and `total_targets`.

## UI must preserve

- Promise Protection Queue rank and decision as primary information.
- `review_score` hidden or secondary and never rendered as a percentage,
  probability, likelihood, or confidence.
- Evidence-signal wording from `docs/AI_SIGNAL_SEMANTICS.md`.
- Task-not-worker framing and human ownership of intervention.
- Configurable human review capacity with a 10% competition-demo default.

## Regression gate

- Frozen model SHA-256:
  `b3d8f13e73d0faee1389b1a51d3db581403502d8ce85c6fca45bd6688505c315`.
- Canonical fixture at 10%: 134 targets -> 14 `WINDOW_REVIEW`.
- Canonical product output SHA-256:
  `f3bd4de96ff3b282bd01671c700fa29f72191840a0a48045c682802af6df88d8`.
- Run the full unit suite before accepting integration changes.
