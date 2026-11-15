"""Project B — Hisaab budget optimization.

Standalone CLI:
  python -m backend.optimizer.cli --budget 100000 --objective sales --strategy balanced
  python -m backend.optimizer.cli --budget 50000 --formats in_stream,shorts --objective views
"""
from .engine import optimize, fit_curve, water_fill, CurveFit

__all__ = ["optimize", "fit_curve", "water_fill", "CurveFit"]
