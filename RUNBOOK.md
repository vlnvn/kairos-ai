# KAIROS demo runbook

## Install and start

Use Python 3.12 from the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install .
python -m kairos_ai.server --host 127.0.0.1 --port 8080
```

Or use the single-service container:

```powershell
docker compose up --build
```

Do not add a database, runtime model download, or external API key. The local release is self-contained.

## Health and scoring

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/health
```

Score the bundled snapshot:

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8080/score `
  -Method Post `
  -ContentType application/json `
  -InFile examples/input_snapshot.json
```

The canonical response contains 134 ranked targets and 14 `WINDOW_REVIEW` decisions at 10% capacity.

## Operational contract

- `snapshot_time` is the decision epoch and equals every target task's acceptance time.
- `target_task_ids` identifies newly accepted focal tasks.
- `tasks` contains relevant current active tasks only.
- Daily acceptance counters come from acceptance events, never pickup outcomes.
- `review_budget_fraction` is configurable from greater than zero through 1.0.
- 10% is the competition demo default and frozen evidence anchor.
- Changing capacity changes only the review cutoff; rank order and ordering values stay fixed.
- Arbitrary capacity settings do not imply separately validated scientific performance.
- Never add an outcome, completion, pickup timestamp/GPS, or realized route field to make inference work.

## Release verification

Run every check before a demo or release handoff:

```powershell
python -m unittest discover -s tests -v
python scripts/verify_ai_release.py
python scripts/verify_fullstack_release.py
python -m compileall -q src scripts tests
git diff --check
```

If Docker is available:

```powershell
docker compose up --build --detach
Invoke-RestMethod http://127.0.0.1:8080/health
docker compose down
```

The release verifier is the source of truth for the frozen model hash, 21-feature schema, dependency versions, and canonical output. Do not replace it with a visual check.

## Common failure modes

| Symptom | Meaning | Response |
| --- | --- | --- |
| HTTP 400 `invalid_json` | Body is not valid JSON | Correct the file; do not reuse stale results |
| HTTP 400 `invalid_snapshot` | Schema, time, location, duplicate, category, or future-field validation failed | Rebuild the decision-time snapshot from approved fields |
| HTTP 413 `request_too_large` | Snapshot exceeds the 8 MiB local-demo cap | Narrow the operational snapshot; never disable the cap silently |
| HTTP 415 | Media type is not `application/json` | Set the correct content type |
| HTTP 503 `model_unavailable` | Frozen model missing, modified, or incompatible | Restore the pinned artifact and rerun release verification |
| Health works but browser does not load | Static asset missing or wrong working copy | Restore tracked `static/` files and restart |
| Rank or golden hash drift | Predictive release invariant changed | Stop the release; do not demo or auto-retrain |

Generic API errors intentionally exclude filesystem paths, model hashes, and tracebacks. Consult local test output for diagnosis; do not weaken the transport boundary.

## Rollback

KAIROS is stateless:

1. Stop the process or container.
2. Restore the last reviewed release commit and its tracked artifact/manifest as one unit.
3. Rerun unit, AI-release, and full-stack verification.
4. Confirm the canonical 134/14 result and health endpoint.
5. Restart the service and repeat the operator demo path.

Treat artifact mismatch, feature-schema drift, missing active-status data, acceptance-counter unavailability, or final-evidence contamination as stop conditions requiring model-owner review. Never silently fall back to outcome-derived data or a different model.
