"""Synthetic data generation: locale packs + vectorised row generator."""
from .locales import LOCALES, PLATFORMS, CAMPAIGNS, get_locale, LocalePack
from .synth import COLUMNS, iter_generated, write_parquet, write_csv

__all__ = ["LOCALES", "PLATFORMS", "CAMPAIGNS", "get_locale", "LocalePack",
           "COLUMNS", "iter_generated", "write_parquet", "write_csv"]
