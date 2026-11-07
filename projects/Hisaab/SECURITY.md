# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 1.0.x | ✅ |
| < 1.0 | — |

## Reporting a vulnerability

Email **hassaan.awais777@gmail.com** (or open a GitHub **security advisory** via
*Security → Report a vulnerability*) rather than a public issue. Include a minimal
reproduction and affected commit. You'll get an acknowledgement within 7 days and a
fix-or-mitigation plan within 30.

## Scope notes

Hisaab is an analytics/research tool; the threat model is conventional for a FastAPI +
Vite web app:

- The API performs **no authentication by default** — it is designed for local/lab use
  and trusted networks. If you deploy it publicly, put it behind an authenticating proxy
  and set `HISAAB_CORS_ORIGINS` to explicit origins.
- The sentiment bridge reads **local SQLite/CSV files** produced by `scripts/export_raye.py`;
  point `HISAAB_RAYE_DIR` only at directories you control.
- Uploaded/generated datasets land in `HISAAB_DATA_DIR` — treat that directory as
  execution-adjacent (Parquet/CSV parsing is not a security boundary).
- No secrets, keys or credentials belong in datasets or Raye exports.
