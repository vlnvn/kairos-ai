# Runbook

## Install and run

```powershell
python -m pip install -e .
python -m kairos_ai.server --host 127.0.0.1 --port 8080
```

Health check: `GET http://127.0.0.1:8080/health`. Score by posting the exact
snapshot JSON to `/score`. A 400 response means the request failed closed; inspect
`detail` and do not strip validation.

## Operational contract

- `snapshot_time` equals every target's acceptance time.
- `target_task_ids` are newly accepted focal tasks.
- `tasks` contains the relevant current active tasks only.
- Daily acceptance counters come from acceptance events, never pickup outcomes.
- Review budget is fixed at 0.1.
- Never add an outcome field to make inference “work”.

## Verification

Run `python -m unittest discover -s tests -v`. Verify the artifact SHA-256 against
`artifacts/manifest.json`. The expected demo has 134 results and 14 reviews.

## Rollback and incident response

The service is stateless. Stop it, restore the pinned artifact/manifest, rerun the
tests, then restart. Treat schema drift, missing active status, acceptance-counter
unavailability, score drift, or materially changed early/late prevalence as a
stop condition requiring model-owner review. Never silently fall back to an
outcome-derived field.
