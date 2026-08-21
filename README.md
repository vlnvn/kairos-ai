# KAIROS

KAIROS is a dispatcher decision-support tool for capacity-constrained pickup-promise review. At the moment newly accepted tasks enter the operation, it ranks those promises using only then-known context and marks the few inside the available human review cutoff. The dispatcher—not the model—owns every review and operational action.

## Problem

Busy pickup operations cannot inspect every accepted promise at once. A uniform queue spends scarce attention without distinguishing which promises should be reviewed first. KAIROS turns one operational snapshot into a deterministic, rank-ordered Promise Protection Queue.

KAIROS is not an ETA, route optimizer, automatic reassignment system, worker rating, or causal diagnosis tool.

## Product workflow

1. Load a JSON snapshot of active and newly accepted pickup tasks.
2. Select available review capacity; 10% is the evidence-aligned competition demo default.
3. Choose **Protect Promises**.
4. Review `WINDOW_REVIEW` tasks in rank order and inspect approved operational context.
5. The human dispatcher decides whether any intervention is appropriate.

Changing capacity changes only the decision cutoff. It does not change task ordering or imply independently validated performance at arbitrary capacities.

## Architecture

The browser and JSON API share one standard-library HTTP adapter. The adapter validates request transport and delegates exactly once to `KairosRanker`, which verifies and loads the frozen CatBoost artifact. No database, external runtime API, or secret is required. See [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md).

## Quick start

Python 3.12 is the release runtime.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install .
python -m kairos_ai.server --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080`.

On macOS or Linux, activate with `source .venv/bin/activate`; the remaining commands are unchanged.

## Docker start

```powershell
docker compose up --build
```

The one-service Compose definition builds the image, runs it as an unprivileged user with a read-only filesystem, and exposes the local application on port 8080. Stop it with `docker compose down`.

## Demo snapshot

Load `examples/input_snapshot.json` in the product. It contains 134 target tasks; the 10% demo capacity produces 14 `WINDOW_REVIEW` decisions. The snapshot is a real public LaDe replay fixture described in [DATA_CARD.md](DATA_CARD.md), not private operational data.

## API

`POST /score` accepts `application/json` up to 8 MiB. A minimal request has this shape:

```json
{
  "snapshot_time": "2024-06-22T07:36:00",
  "review_budget_fraction": 0.1,
  "target_task_ids": ["4471808"],
  "tasks": [
    {
      "task_id": "4471808",
      "accepted_at": "2024-06-22T07:36:00",
      "window_start": "2024-06-23T17:00:00",
      "window_end": "2024-06-23T19:00:00"
    }
  ]
}
```

The complete task schema is represented by the bundled snapshot. A successful response is ordered by rank:

```json
{
  "metadata": {
    "review_budget_count": 14,
    "review_budget_fraction": 0.1,
    "total_targets": 134
  },
  "results": [
    {
      "task_id": "4471808",
      "decision": "WINDOW_REVIEW",
      "rank": 1,
      "priority": 1,
      "review_score": 0.9148441199,
      "evidence_signals": [
        {"signal": "slack_to_end_h", "value": 35.4},
        {"signal": "pending_other_count", "value": 4},
        {"signal": "pending_overlap_count", "value": 0}
      ],
      "explanation_notice": "Uncalibrated ordering score with non-causal signals; dispatcher owns the decision."
    }
  ]
}
```

The response excerpt above is from the canonical fixture. `review_score` is an uncalibrated ordering value: it is not a probability, percentage, confidence, causal explanation, or intervention recommendation. The product intentionally does not render it.

Health check: `GET /health`. Requests with future/outcome fields, invalid task data, malformed JSON, or unsupported media types fail closed with a generic error code.

## AI evidence

- Model: frozen CatBoost classifier, 756,516 bytes.
- Model SHA-256: `b3d8f13e73d0faee1389b1a51d3db581403502d8ce85c6fca45bd6688505c315`.
- Feature schema: 21 decision-time features; categorical indices 19 and 20.
- Canonical output SHA-256: `f3bd4de96ff3b282bd01671c700fa29f72191840a0a48045c682802af6df88d8`.
- Production V1 and the fixed-recipe V2 reproduction evidence remain explicitly separated.

Machine-readable release evidence lives in `artifacts/ai_release_manifest.json`; scientific claims and boundaries are in [MODEL_CARD.md](MODEL_CARD.md), [DATA_CARD.md](DATA_CARD.md), and [CLAIMS_REGISTER.md](CLAIMS_REGISTER.md).

## Reproducibility

```powershell
python scripts/verify_ai_release.py
python scripts/verify_fullstack_release.py
```

The first command verifies the frozen artifact, feature schema, dependency versions, and golden output. The second starts the real server on an available port, checks the HTTP capacity matrix, compares exact ranking with direct engine output, tests malformed input, measures canonical latency, and shuts the server down.

## Tests

```powershell
python -m unittest discover -s tests -v
python -m compileall -q src scripts tests
```

The test suite covers engine invariants, artifact corruption, schema and future-field rejection, HTTP boundaries, capacity metadata, static product semantics, safe DOM construction, and responsive/accessibility contracts. CI repeats these checks and builds the Docker image without deployment or secrets.

## Governance and limitations

- Same-origin browser/API operation; no permissive CORS header.
- 8 MiB request cap, fail-closed schema validation, strict CSP, and generic transport errors.
- Frozen model hash and loaded-schema verification before scoring.
- No external runtime API, secret, private data, or automatic action.
- This is a local competition MVP, not an internet-production-hardened service.
- Real operator workflow integration, live traffic behavior, and intervention impact have not been validated.
- Performance evidence belongs to the frozen evaluation protocol; changing capacity is an operational control, not a new scientific claim.

Operational procedures and rollback are in [RUNBOOK.md](RUNBOOK.md). Failure and input-health contracts are in [docs/AI_FAILURE_CONTRACT.md](docs/AI_FAILURE_CONTRACT.md) and [docs/AI_INPUT_HEALTH_SPEC.md](docs/AI_INPUT_HEALTH_SPEC.md).

## Repository structure

```text
artifacts/       Frozen model and machine-readable release evidence
docs/            Architecture, integration, failure, and release contracts
examples/        Public-data demo snapshot
research/        Reproducible evaluation evidence; not required at runtime
scripts/         AI and full-stack release verifiers
src/kairos_ai/   Deterministic engine, CLI, and HTTP adapter
static/          One-page dispatcher product
tests/           Engine, transport, and product contract tests
```
