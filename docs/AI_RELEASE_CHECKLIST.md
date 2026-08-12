# AI Release Checklist

Run from a clean checkout with project dependencies installed. Every required item is PASS only when the stated observation matches exactly.

## Frozen artifact and schema

- [ ] `python scripts/verify_ai_release.py` returns `"result": "PASS"`.
- [ ] Model SHA-256 is `b3d8f13e73d0faee1389b1a51d3db581403502d8ce85c6fca45bd6688505c315`.
- [ ] `FEATURES` contains exactly 21 names in the order recorded in `artifacts/manifest.json`.
- [ ] Feature-schema canonical JSON SHA-256 is `b36985270b8ff9659fb5750c56eebefb58cb54bbcb6279e7346c2e3895deb7df`.
- [ ] Model categorical indices are exactly `[19, 20]`.
- [ ] Missing, modified, or schema-incompatible model artifacts fail before scoring.

## Inference contract

- [ ] Canonical output SHA-256 is `f3bd4de96ff3b282bd01671c700fa29f72191840a0a48045c682802af6df88d8`.
- [ ] Repeated canonical inference is byte-identical.
- [ ] Future/outcome fields are rejected with `SnapshotError`.
- [ ] Malformed structures and invalid numeric/geospatial values fail closed.
- [ ] Changing capacity preserves task order and scores and changes only the decision cutoff.
- [ ] Output remains task-ranked, human-owned, and limited to `WINDOW_REVIEW` / `KEEP_ASSIGNMENT`.
- [ ] `review_score` is described only as an uncalibrated ordering score.

## Executable verification

- [ ] `python -c "import kairos_ai"` succeeds.
- [ ] `python -m unittest discover -s tests -v` passes at least 29 tests.
- [ ] `python -m py_compile src/kairos_ai/*.py scripts/*.py` succeeds.
- [ ] CLI inference on `examples/input_snapshot.json` succeeds and matches the canonical golden hash.
- [ ] `PRODUCT_API_CONTRACT.json` and every tracked AI JSON artifact parse successfully.

## Evidence consistency

- [ ] V1 values match `artifacts/final_lock_evidence.json` and are labeled historical frozen production evidence.
- [ ] V2 values match `research/v2_closure/*_results.json` and are labeled fresh fixed-recipe reproduction evidence.
- [ ] No statement assigns V2 metrics to the production V1 binary.
- [ ] Model Card, Data Card, Claims Register, release manifest, and technical Q&A use consistent target, epoch, score, and ownership semantics.
- [ ] Synthetic software measurements are not presented as a logistics SLA or scientific model result.

## Repository hygiene

- [ ] No raw LaDe data, processed caches, model intermediates, logs, secrets, local absolute paths, prompts, transcripts, or generated junk are tracked.
- [ ] `git diff --check` passes and the intended release diff is understood.
- [ ] No unsupported Indonesia, causality, fairness, worker-scoring, late-only, or intervention-impact claim exists.

Any failure blocks release review until corrected. This checklist does not authorize merging, deployment, retraining, or changes to the predictive core.
