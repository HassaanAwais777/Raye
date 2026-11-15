# AudienceLens — YouTube Audience & Campaign Intelligence Platform

An AI-powered platform that turns real YouTube data into audience intelligence,
multilingual sentiment insight, audience segmentation, anomaly detection,
competitor analysis, evidence-based findings, downloadable reports, and
campaign budget optimization — with a tool-using AI research agent as the
central entry point.

Built by composing three independently-runnable projects into one unified
FastAPI + Next.js platform:

| Project | Backend module | Origin | Purpose |
|---|---|---|---|
| **A — Raye** | `backend/nlp` | Review-Lens | Multilingual sentiment (EN / Urdu / Roman Urdu / code-mixed) + configurable ABSA + purchase-intent |
| **B — Hisaab** | `backend/optimizer` | AdPilot-AI | Water-fill budget optimization (saturation curves, largest-remainder rounding) |
| **3 — Audience** | `backend/audience` | Project 3 | K-Means / DBSCAN / Hierarchical clustering + Isolation Forest anomaly detection |

Plus: YouTube Data API v3 collection, Google Ads GAQL module, a findings
capstone engine, PDF/DOCX report generation, Neon PostgreSQL persistence,
and a tool-using AI research agent.

---

## Architecture

```
Next.js 16 frontend (port 3000)
   │  AI Research Agent (chatbot) + 10 dashboard views
   │  calls backend via the gateway (?XTransformPort=8000) or directly
   ▼
Python FastAPI backend (port 8000) — modular monolith, 8 modules:
   ├─ nlp        — multilingual sentiment + ABSA + purchase-intent (Project A)
   ├─ optimizer  — water-fill budget allocation (Project B)
   ├─ audience   — clustering + Isolation Forest anomaly (Project 3)
   ├─ youtube    — official YouTube Data API v3 collection
   ├─ findings   — evidence-based finding cards (capstone)
   ├─ google_ads — GAQL YouTube video campaign metrics
   ├─ reports    — structured reports + PDF/DOCX export (reportlab + python-docx)
   └─ repository — Neon persistence (sessions, messages, results)
   ▼
Neon PostgreSQL (DATABASE_URL + DIRECT_URL, Alembic migrations)
```

## Stack
- **Frontend**: Next.js 16, TypeScript, Tailwind CSS 4, shadcn/ui, Recharts, Zustand, z-ai-web-dev-sdk (for the agent LLM)
- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, Psycopg 3
- **ML/NLP**: scikit-learn (clustering, Isolation Forest, TF-IDF), numpy, pandas
- **Reports**: reportlab (PDF), python-docx (DOCX)
- **DB**: Neon PostgreSQL only (SQLite/Mongo/local-Postgres refused)

## Project structure

```
.
├── src/                       # Next.js frontend
│   ├── app/                    #   page.tsx (app shell), layout, api/agent/route.ts
│   ├── components/platform/    #   sidebar, primitives, views/ (10 module views)
│   └── lib/                    #   api.ts, types.ts, platform-store.ts, agent-prompt.ts
├── backend/                    # Python FastAPI backend
│   ├── main.py                 #   unified app mounting all routers
│   ├── config.py               #   settings (loads .env via python-dotenv)
│   ├── nlp/                    #   Project A: lexicons, pipeline, router, cli
│   ├── optimizer/              #   Project B: engine (curves/allocate/baselines), router, cli
│   ├── audience/               #   Project 3: engine (features/clustering/anomaly), router, cli
│   ├── youtube/                #   Data API v3 client + router (configure, research, search…)
│   ├── findings/               #   capstone engine + router
│   ├── google_ads/             #   GAQL client + router
│   ├── reports/                #   engine + generator (PDF/DOCX) + router
│   ├── repository/             #   Neon persistence (sessions/messages/results)
│   ├── db/                     #   SQLAlchemy 2.x models + session (guarded)
│   ├── alembic/                #   env.py + versions/0001_initial_schema.py
│   └── requirements.txt
├── alembic.ini
├── start-backend.sh            # uvicorn launcher
├── .env.example                # template — copy to .env
└── package.json
```

## Quickstart

### 1. Backend
```bash
pip install -r backend/requirements.txt
pip install "psycopg[binary]"        # Neon driver
cp .env.example .env                 # fill in DATABASE_URL, DIRECT_URL, YOUTUBE_API_KEY
./start-backend.sh                   # uvicorn on :8000
# Apply the DB schema to Neon:
DIRECT_URL="postgresql://..." alembic upgrade head
```

### 2. Frontend
```bash
npm install        # or: bun install
npm run dev        # Next.js on :3000
```
Open http://localhost:3000 — the Research Agent is the default view.

### 3. Run each project individually (CLI)
```bash
# Project A — multilingual sentiment + ABSA
python -m backend.nlp.cli "camera acha hai lekin battery kharab hai"
python -m backend.nlp.cli --catalog fashion "Price bohat zyada hai."

# Project B — budget optimizer
python -m backend.optimizer.cli --budget 100000 --objective sales

# Project 3 — clustering + anomaly
python -m backend.audience.cli --texts comments.txt --method kmeans
python -m backend.audience.cli --anomaly --series "10,12,11,40,13,55,12"
```

## Environment variables
All optional — the backend runs without them; each activates a capability.
See `.env.example`.

| Var | Activates |
|---|---|
| `DATABASE_URL` (postgresql) | Neon persistence |
| `DIRECT_URL` (postgresql) | Alembic migrations |
| `YOUTUBE_API_KEY` | live YouTube collection |
| `GOOGLE_ADS_*` (5 vars) + `pip install google-ads` | real paid campaign metrics |

## The AI Research Agent (chatbot)
A tool-using agent (Next.js `/api/agent` route + z-ai SDK) that calls a
validated set of backend tools and grounds answers in real data:
- `analyze_sentiment` — multilingual NLP + ABSA on pasted comments
- `cluster_comments` — audience segmentation
- `generate_findings` — evidence-based finding cards
- `youtube_research` — collect videos + comments + sentiment
- `generate_report` — full report with in-chat PDF/DOCX download

Capped at one tool call per turn; synthesizes a grounded answer from the
result. Never executes arbitrary SQL or unrestricted API requests.

## Strict live-data policy
Every result carries a provenance label: `LIVE_DATA`, `MODEL_PREDICTION`,
`ESTIMATED_SCENARIO`, `INFERENCE`, `USER_INPUT`, or `INSUFFICIENT_DATA`. No
synthetic data, demo seeding, or fabricated metrics are ever shown as live.
Organic YouTube statistics are never blended with paid Google Ads metrics.
Audience segments are analytical clusters, not verified demographics.

## Aspect catalogs (configurable ABSA)
- `general` — overall
- `product` — battery, camera, price, display, performance, software, audio, build, delivery
- `youtube` — content quality, presentation, creator credibility, entertainment, educational, accuracy, audience experience, ad relevance, brand perception
- `fashion` — price, fabric quality, sizing, delivery, discounts, availability, purchase intent, design (Project 3 / Pakistani e-commerce)

## API reference
Backend docs at `http://localhost:8000/docs` once running. Key endpoints:
- `POST /api/v1/nlp/analyze`, `/analyze-batch`
- `POST /api/v1/audience/cluster`, `/anomaly`
- `POST /api/v1/optimizer/optimize`
- `POST /api/v1/findings/generate`
- `POST /api/v1/youtube/{configure,research,search,videos,comments,channel,playlist}`
- `GET /api/v1/google-ads/{status,metrics}`
- `POST /api/v1/reports/{generate,export}` (export → PDF/DOCX download)
- `POST /api/v1/sessions` + `/sessions/messages` + `/sessions/sentiment` (persistence)
- `GET /api/v1/health`

## License
MIT
