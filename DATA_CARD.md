# Data Card

## Source, license, and revisions

The approved source is Cainiao-AI LaDe-P under Apache-2.0. Five pickup files cover Jilin, Shanghai, Hangzhou, Chongqing, and Yantai. Raw data is intentionally excluded from this repository.

Two evidence contexts must remain distinct:

- V1 historical frozen production evidence records its approved source revision `3d2d77a11f5fc960af4342076dc65e176584d99f` and hashes in existing frozen artifacts.
- V2 reproducibility uses revision `f1ddd8dd163028dd5a8ab7d7c83b198ebd2f2167`; exact Parquet names, sizes, and SHA-256 values are in `research/v2_closure/dataset_manifest.json`.

## V2 audit and chronology

The V2 audit retained 6,135,893 of 6,136,147 rows. The 254 exclusive exclusions were acceptance after the promised window end; critical parse failure, invalid-window, and acceptance-after-pickup exclusion counts were zero.

V2 spans 2022-05-01 through 2022-10-31. TRAIN ends 2022-09-06, VALIDATION spans 2022-09-07 through 2022-10-04, and FINAL spans 2022-10-05 through 2022-10-31. Decision groups are fixed 15-minute city batches. TRAIN uses the preregistered label-blind complete-group SHA-256 sample to at least 100,000 rows per city; validation and final use all actionable rows.

## Target and historical outcomes

The binary target is `pickup_time < promised_start OR pickup_time > promised_end`. Historical pickup timestamps and GPS are used only to construct offline ground truth and reconstruct which context tasks were active at the decision epoch. They are forbidden at production inference.

## Production information boundary

The 21 production features use the target acceptance epoch, promised window, task and acceptance-time location, prior acceptance counters, and already-known active context. Raw courier, AOI, and task identities do not enter the model. Context accepted after the decision timestamp is rejected.

The bundled Yantai replay at `2024-06-22 07:36:00` contains 134 targets and 388 active tasks. Outcome fields used for historical fixture construction were removed before export; the fixture is a deterministic product regression anchor, not fresh scientific evidence.

## Limitations

- The data represents Chinese delivery operations; Indonesian transfer is unvalidated.
- The combined target is early-heavy and may not match a future deployment mix.
- Temporal and entity generalization do not establish fairness or intervention impact.
- Raw and processed research data remain outside Git; reproducibility depends on the pinned source revision, hashes, and recorded builder methodology.
