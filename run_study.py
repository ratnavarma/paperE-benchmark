#!/usr/bin/env python
"""Thin CLI for the Track E study runner; all logic lives in ``papere.runner``.

  uv run python run_study.py --family F0R --mode tune --seeds 60000-60049 --out results/tuning
  uv run python run_study.py --family F0R --freeze --out results/tuning
  uv run python run_study.py --family F0R --seeds 61000-61019 --out results/f0r_pilot
  uv run python run_study.py --family KCOPY --seeds 61500-61599 --out results/kcopy
  uv run python run_study.py --family SCALE --seeds 63000-63019 --out results/scale
"""
import sys

from papere.runner import main

if __name__ == "__main__":
    sys.exit(main())
