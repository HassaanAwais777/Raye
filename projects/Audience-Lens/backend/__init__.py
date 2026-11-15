"""AudienceLens backend — YouTube Audience & Campaign Intelligence.

A modular monolith composing three independently-runnable projects:
  * nlp        — Project A (Raye): multilingual sentiment + ABSA
  * optimizer  — Project B (Hisaab): water-fill budget optimization
  * audience   — Project 3: clustering + anomaly detection
plus a YouTube Data API v3 collection service and Neon-ready DB models.

Run unified:   uvicorn backend.main:app --port 8000
Run individual CLIs:
  python -m backend.nlp.cli        "camera acha hai lekin battery kharab hai"
  python -m backend.optimizer.cli  --budget 100000 --objective sales
  python -m backend.audience.cli   --texts file.txt --method kmeans --k 3
"""

__version__ = "0.2.0"
