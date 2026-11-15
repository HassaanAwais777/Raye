"""Project A — Raye multilingual sentiment & ABSA.

Standalone CLI:
  python -m backend.nlp.cli "camera acha hai lekin battery kharab hai"
  python -m backend.nlp.cli --catalog youtube --batch texts.txt
"""
from .pipeline import analyze_text, analyze_batch, ASPECT_CATALOGS

__all__ = ["analyze_text", "analyze_batch", "ASPECT_CATALOGS"]
