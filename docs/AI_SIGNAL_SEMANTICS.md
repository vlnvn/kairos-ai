# AI Signal Semantics

KAIROS exposes a small set of observable decision-time context signals alongside
each ranked task. They help a human understand which operational facts are present
in the request. They are **not causal explanations and not SHAP attribution**.
They must never be presented as probabilities, blame, or worker assessments.

## Signal contract

### `slack_to_end_h`

- Human-readable label: **Remaining promise-window buffer**
- Unit: hours
- Literal measure: time between target-task acceptance and the promised pickup
  window end.
- Safe wording: “Time remaining between task acceptance and the promised window
  end.”
- Prohibited interpretation: “Probability the task will be late,” guaranteed time
  available, route feasibility, or an ETA.

### `pending_other_count`

- Human-readable label: **Other active pickup commitments**
- Unit: task count
- Literal measure: number of other active pickup tasks already present in the same
  operational context at the decision timestamp.
- Safe wording: “Other active pickup tasks already known in this task’s current
  operational context.”
- Prohibited interpretation: “Courier overload,” “courier performance problem,”
  worker quality, blame, or a causal reason for an off-window pickup.

### `pending_overlap_count`

- Human-readable label: **Overlapping pickup windows**
- Unit: task count
- Literal measure: number of current active commitments whose promised pickup
  windows overlap the target task’s promised window.
- Safe wording: “Current active commitments with overlapping promised pickup
  windows.”
- Prohibited interpretation: “This causes a violation,” route conflict proof,
  worker fault, or a probability of failure.

## Presentation rules

- Lead with queue rank and `WINDOW_REVIEW` / `KEEP_ASSIGNMENT`.
- Treat signals as secondary factual context known at acceptance time.
- Do not combine signals into an invented probability or severity label.
- Do not use signals to score, compare, or discipline workers.
- Preserve the engine’s human-ownership and non-causality notice.
