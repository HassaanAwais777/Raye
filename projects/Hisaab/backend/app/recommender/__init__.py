"""Budget Recommendation Engine — L3 saturation curves + water-filling, with L1/L2 baselines."""
from .curves import CurveFit, fit_curve, fit_all, bootstrap_curves
from .allocate import water_fill, expected_outcomes
from .baselines import roas_proportional, bayes_shrunk_proportional, eb_shrunk_roas

__all__ = ["CurveFit", "fit_curve", "fit_all", "bootstrap_curves", "water_fill",
           "expected_outcomes", "roas_proportional", "bayes_shrunk_proportional",
           "eb_shrunk_roas"]
