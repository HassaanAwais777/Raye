# AudienceLens Backend — Python FastAPI

Unified backend for the YouTube Audience & Campaign Intelligence platform. Composes
three independently-runnable projects plus a YouTube Data API v3 collection service
and Neon-ready PostgreSQL models.

## The three projects

| Project | Module | Origin | What it does |
|---|---|---|---|
| **A — Raye** | `backend/nlp` | Review-Lens | Multilingual sentiment (EN/Urdu/Roman Urdu/code-mixed) + configurable ABSA. 5 classes incl. `uncertain`. |
| **B — Hisaab** | `backend/optimizer` | AdPilot-AI | Water-fill budget optimization (saturation curves, largest-remainder rounding, scenario comparison). |
| **3 — Audience** | `backend/audience` | Project 3 assignment | K-Means/DBSCAN/Hierarchical clustering + Isolation Forest anomaly detection. |

Each works **standalone** via its CLI, and all three are **integrated** under one
FastAPI app.

## Run unified

```bash
pip install -r backend/requirements.txt
./start-backend.sh          # uvicorn on :8000
# Docs:  http://localhost:8000/docs
# Health: http://localhost:8000/api/v1/health
```

## Run each project individually (CLI)

```bash
# Project A — NLP / sentiment
python -m backend.nlp.cli "camera acha hai lekin battery kharab hai"
python -m backend.nlp.cli --catalog product "battery great but camera bad"
python -m backend.nlp.cli --batch comments.txt --catalog youtube

# Project B — optimizer
python -m backend.optimizer.cli --budget 100000 --objective sales --strategy balanced
python -m backend.optimizer.cli --budget 50000 --formats in_stream,shorts --objective views

# Project 3 — audience clustering + anomaly
python -m backend.audience.cli --texts comments.txt --method kmeans
python -m backend.audience.cli --texts comments.txt --method dbscan
python -m backend.audience.cli --anomaly --series "10,12,11,40,13,12,11,55,12"
```

## API (unified)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/nlp/analyze` | Analyze one comment `{text, aspect_catalog}` |
| `POST` | `/api/v1/nlp/analyze-batch` | Analyze many; returns distribution + topics |
| `GET`  | `/api/v1/nlp/aspects/{catalog}` | List aspects in a catalog |
| `POST` | `/api/v1/optimizer/optimize` | Budget optimization `{budget, formats, objective, strategy, real_curves?}` |
| `POST` | `/api/v1/audience/cluster` | Cluster comments `{texts, method, k}` |
| `POST` | `/api/v1/audience/anomaly` | Isolation Forest `{series:[{label, features}]}` |
| `GET`  | `/api/v1/youtube/search?q=&country=&limit=` | search.list (needs `YOUTUBE_API_KEY`) |
| `GET`  | `/api/v1/youtube/videos?ids=` | videos.list |
| `GET`  | `/api/v1/youtube/comments?video_id=` | commentThreads.list |
| `GET`  | `/api/v1/youtube/channel?handle_or_id=` | channels.list |
| `GET`  | `/api/v1/youtube/playlist?playlist_id=` | playlistItems.list |
| `GET`  | `/api/v1/health` | Status + integration flags |

## Environment variables (all optional — backend runs without them)

```
YOUTUBE_API_KEY=...              # YouTube Data API v3
DATABASE_URL=postgresql://...    # Neon pooled runtime
DIRECT_URL=postgresql://...      # Neon direct, for Alembic migrations
GOOGLE_ADS_DEVELOPER_TOKEN=...   # Google Ads API
GOOGLE_ADS_CUSTOMER_ID=...
GOOGLE_ADS_REFRESH_TOKEN=...
```

## Strict live-data policy

Every response carries a `provenance` label: `LIVE_DATA` (authorized API),
`MODEL_PREDICTION` (trained model output), `ESTIMATED_SCENARIO` (documented
assumptions), `INFERENCE` (analytical derivation), `USER_INPUT`, or
`INSUFFICIENT_DATA`. No synthetic data is ever returned as live. When a key is
missing, the endpoint returns a clear error, not fake data.

## Database

SQLAlchemy 2.x models in `backend/db/models.py` are Neon-ready (foreign keys,
unique constraints, JSONB, provenance columns). They activate only when
`DATABASE_URL` is set; otherwise the backend processes requests statelessly.
SQLite, MongoDB, and local Postgres are not used.
