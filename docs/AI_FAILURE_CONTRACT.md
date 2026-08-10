# AI Failure Contract

The KAIROS AI boundary accepts an Operational Review Request and either returns a deterministic Promise Protection Queue or fails closed. A failed request must not produce a partial ranking.

## Valid request

A valid request has the exact top-level schema, a nonempty target list, a nonempty task array, valid pending-task records, finite operational numbers, valid coordinates, and timestamps consistent with the decision epoch. It produces one ranked item per target. `WINDOW_REVIEW` is the capacity-limited prefix; all remaining targets are `KEEP_ASSIGNMENT`.

## Invalid request

Malformed request structure, missing or unknown fields, invalid identifiers, invalid timestamps, invalid task state, invalid windows, duplicate tasks or targets, and missing targets fail closed with `SnapshotError`.

## Forbidden future data

Pickup outcomes, actual timestamps or GPS, completion outcomes, violation fields, post-decision route information, and context accepted after the decision timestamp are rejected with `SnapshotError`. They are never silently ignored.

## Invalid numeric or geospatial data

Boolean, textual, non-finite, or out-of-range numeric values are rejected. Longitude must be within -180 to 180 and latitude within -90 to 90. Coordinate pairs must be jointly present or jointly null where null is supported. Prior-acceptance counters must be finite nonnegative integers.

## Model integrity failure

A missing or modified model, feature-schema drift, categorical-schema drift, or invalid model output fails closed with `ModelArtifactError`. The service must not score until the frozen artifact and schema are restored.

## Stable boundary

`SnapshotError` identifies invalid request data. `ModelArtifactError` identifies an unavailable or untrusted frozen scoring boundary. API layers may map these categories to their existing error response contract, but must not expose internal paths, model details, stack traces, or partial results.
