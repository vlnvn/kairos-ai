# Architecture

```text
future-free dispatcher snapshot JSON
  ├─ newly accepted target_task_ids
  ├─ current active tasks and known promised windows
  └─ outcome-free daily acceptance counters
             │
             ▼
fail-closed schema + causal feature builder
             │
             ▼
frozen CatBoost artifact
             │
             ▼
stable score sort + ceil(10% budget)
             │
             ▼
WINDOW_REVIEW / KEEP_ASSIGNMENT + non-causal risk signals
             │
             ▼
human dispatcher decision
```

`kairos_ai.engine` is shared by the CLI and HTTP server, preventing training/UI
feature drift. The server uses Python's standard-library threaded HTTP server:
`GET /health`, `GET /`, and `POST /score`. There is no database, authentication,
external map, telemetry, or background mutation in this MVP.

