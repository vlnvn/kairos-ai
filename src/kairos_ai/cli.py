from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import KairosRanker


def main():
    parser = argparse.ArgumentParser(description="KAIROS pickup-window review triage")
    parser.add_argument("snapshot")
    parser.add_argument("--model", default=str(Path(__file__).resolve().parents[2] / "artifacts" / "kairos_final.cbm"))
    parser.add_argument("--output")
    args = parser.parse_args()
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    result = KairosRanker(args.model).score(snapshot)
    text = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()

