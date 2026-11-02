"""Central settings, loaded from environment variables (see .env.example)."""
import os

_APP_DIR = os.path.dirname(os.path.abspath(__file__))


class Settings:
    def __init__(self) -> None:
        self.app_name = "Raye API"
        self.version = "1.0.0"
        self.db_path = os.getenv("RAYE_DB_PATH", os.path.join(_APP_DIR, "..", "..", "raye.db"))
        self.cors_origins = [o.strip() for o in os.getenv("RAYE_CORS_ORIGINS", "*").split(",") if o.strip()]

        # Scale controls
        self.max_total_comments = int(os.getenv("RAYE_MAX_TOTAL_COMMENTS", "200000"))
        self.default_max_comments = int(os.getenv("RAYE_DEFAULT_MAX_COMMENTS", "3000"))
        self.min_reliable_n = int(os.getenv("RAYE_MIN_RELIABLE_N", "150"))
        self.ideal_n = int(os.getenv("RAYE_IDEAL_N", "2000"))
        self.min_aspect_mentions = int(os.getenv("RAYE_MIN_ASPECT_MENTIONS", "30"))

        # Crawling behaviour
        self.request_timeout = float(os.getenv("RAYE_REQUEST_TIMEOUT", "20"))
        self.user_agent = os.getenv(
            "RAYE_USER_AGENT",
            "Mozilla/5.0 (compatible; RayeBot/1.0; +https://github.com/HassaanAwais777/Raye)",
        )
        self.yt_videos_per_query = int(os.getenv("RAYE_YT_VIDEOS_PER_QUERY", "10"))
        self.yt_comments_per_video = int(os.getenv("RAYE_YT_COMMENTS_PER_VIDEO", "150"))
        self.reddit_posts_per_query = int(os.getenv("RAYE_REDDIT_POSTS_PER_QUERY", "15"))
        self.reddit_comments_per_post = int(os.getenv("RAYE_REDDIT_COMMENTS_PER_POST", "100"))

        # NLP batching
        self.analyze_batch_size = int(os.getenv("RAYE_ANALYZE_BATCH_SIZE", "256"))


settings = Settings()
