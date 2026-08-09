# KAIROS

KAIROS is a minimal decision-support vertical slice for **capacity-constrained
prospective pickup-window compliance triage**. At a target task's acceptance
time, the dispatcher supplies the current operational snapshot and available
review capacity. KAIROS ranks the new targets and uses that capacity only to set
the `WINDOW_REVIEW` cutoff; all remaining tasks receive `KEEP_ASSIGNMENT`. A human
dispatcher owns the decision.

The competition demo defaults to a 10% review budget, aligned with the frozen
Recall@10 evidence. Other operational budgets do not imply validated scientific
performance at those capacities.

The response includes `review_score` solely as an uncalibrated ordering score.
It is not a probability, percentage, likelihood, confidence, or intervention
recommendation. Product surfaces should lead with queue rank and decision and may
omit the raw score.

This repository contains one screen, one JSON scoring endpoint, one CLI, the
frozen CatBoost artifact, a real public LaDe-P replay snapshot, and standard-library
tests. It is not an ETA, route optimizer, automatic reassignment system, or claims
dashboard.

Quick start with any Python 3.11+ environment:

```powershell
python -m pip install -e .
python -m kairos_ai.server --port 8080
```

Open `http://127.0.0.1:8080`, load `examples/input_snapshot.json`, and run KAIROS.

CLI:

```powershell
python -m kairos_ai.cli examples/input_snapshot.json --output examples/output.json
```

Tests:

```powershell
python -m unittest discover -s tests -v
```

The model requires no future/outcome field. Supplying `pickup_time`, labels,
completion timestamps, or pickup GPS fields fails closed.
