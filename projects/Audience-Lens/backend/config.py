"""Centralized settings. All secrets come from environment variables — never
hardcoded. The DB and YouTube/Google-Ads integrations are optional at runtime:
the NLP, optimizer, and audience modules work fully without them.

The .env file (gitignored) is loaded so credentials persist across restarts
without being committed to Git.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Load /home/z/my-project/.env into os.environ. override=True so a Neon URL in
# .env replaces any stale file: URL inherited from the Next.js scaffold.
load_dotenv(override=True)


@dataclass
class Settings:
    # --- Database (Neon PostgreSQL) — optional ---
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    direct_url: str = field(default_factory=lambda: os.getenv("DIRECT_URL", ""))
    # Neon PostgreSQL only. SQLite/file URLs (e.g. from the Next.js scaffold's
    # .env) are explicitly ignored — never used as a production substitute.
    db_enabled: bool = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "").startswith("postgresql")
    )

    # --- YouTube Data API v3 — optional ---
    youtube_api_key: str = field(default_factory=lambda: os.getenv("YOUTUBE_API_KEY", ""))
    youtube_quota_daily: int = 10000

    # --- Google Ads — optional ---
    google_ads_developer_token: str = field(default_factory=lambda: os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", ""))
    google_ads_customer_id: str = field(default_factory=lambda: os.getenv("GOOGLE_ADS_CUSTOMER_ID", ""))
    google_ads_refresh_token: str = field(default_factory=lambda: os.getenv("GOOGLE_ADS_REFRESH_TOKEN", ""))

    # --- LLM (used by the agent router if wired) ---
    llm_base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", ""))

    @property
    def youtube_connected(self) -> bool:
        return bool(self.youtube_api_key)

    @property
    def google_ads_connected(self) -> bool:
        return bool(
            self.google_ads_developer_token
            and self.google_ads_customer_id
            and self.google_ads_refresh_token
        )


settings = Settings()
