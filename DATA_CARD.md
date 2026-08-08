# Data Card

Source: Cainiao-AI LaDe-P, Apache-2.0, pinned research revision
`3d2d77a11f5fc960af4342076dc65e176584d99f`. Five pickup CSVs cover Jilin,
Shanghai, Hangzhou, Chongqing, and Yantai. Raw data is intentionally excluded from
this repository; file hashes live in `artifacts/manifest.json`.

The locked label is `pickup_time < promised_start OR pickup_time > promised_end`.
Rows with invalid timestamps/windows, acceptance after pickup, or acceptance after
the promised end are excluded. The research audit retained 6,135,893 of 6,136,147
rows. Modeling used a preregistered SHA-256 label-blind cap of 100,000 rows/city.

The bundled example is a future-free historical replay from Yantai at
2024-06-22 07:36:00: 134 newly accepted targets and 388 active tasks. Outcome
fields used to construct historical membership were removed before export. The
example may be used for demonstration and tests, not as evidence of Indonesia
performance or intervention impact.

