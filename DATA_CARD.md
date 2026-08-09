# Data Card

## Provenance and license

The approved source is Cainiao-AI LaDe-P at pinned research revision
`3d2d77a11f5fc960af4342076dc65e176584d99f`. The approved source records the
license as Apache-2.0. Five pickup files cover Jilin, Shanghai, Hangzhou,
Chongqing, and Yantai. Raw data is intentionally excluded; source-file hashes are
recorded in `artifacts/manifest.json`.

## Scope and target construction

The audit retained 6,135,893 actionable records across the five cities from
6,136,147 input rows. An actionable record has valid acceptance, pickup, and
promised-window timestamps, with acceptance no later than pickup and no later
than the promised-window end. Invalid timestamps/windows and records failing
those temporal rules are excluded.

The frozen binary target combines both sides of the promise:
`pickup_time < promised_start OR pickup_time > promised_end`. Modeling used the
preregistered SHA-256 label-blind cap of 100,000 rows per city.

## Production information boundary

Outcome timestamps construct the historical target only; they are forbidden at
production inference. The 21 production features use the target acceptance epoch,
promised window, task/acceptance-time location, prior acceptance counters, and
already-known active context. Raw courier, AOI, and task identities do not enter
the model. Context accepted after the decision timestamp is rejected.

The bundled Yantai replay at `2024-06-22 07:36:00` contains 134 newly accepted
targets and 388 current active tasks. Outcome fields used for historical fixture
membership were removed before export.

## Limitations

The dataset represents Chinese delivery operations. Transfer to Indonesian
operations is unvalidated, and the early-heavy combined target may not match a
future deployment mix. The fixture supports deterministic product verification;
it is not evidence of Indonesian performance or intervention impact.
