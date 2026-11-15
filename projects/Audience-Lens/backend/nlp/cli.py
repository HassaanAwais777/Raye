"""Standalone CLI for the NLP module (Project A — Raye).

Usage:
  python -m backend.nlp.cli "camera acha hai lekin battery kharab hai"
  python -m backend.nlp.cli --catalog youtube "great explanation but the mic is bad"
  python -m backend.nlp.cli --batch comments.txt --catalog product
"""
from __future__ import annotations

import argparse
import json
import sys

from .pipeline import ASPECT_CATALOGS, analyze_text, analyze_batch


def main() -> None:
    p = argparse.ArgumentParser(
        prog="backend.nlp.cli",
        description="Multilingual sentiment + ABSA (Project A / Raye)",
    )
    p.add_argument("text", nargs="?", help="Single comment to analyze")
    p.add_argument("--catalog", default="general", choices=list(ASPECT_CATALOGS.keys()))
    p.add_argument("--batch", help="Path to a file with one comment per line")
    args = p.parse_args()

    if args.batch:
        with open(args.batch, encoding="utf-8") as fh:
            texts = [ln.strip() for ln in fh if ln.strip()]
        if not texts:
            print("No comments found in file.", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(analyze_batch(texts, args.catalog), indent=2, ensure_ascii=False))
        return

    if not args.text:
        p.error("Provide a comment or --batch FILE")

    print(json.dumps(analyze_text(args.text, args.catalog), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
