"""Central settings (12-factor: everything overridable by env, see .env.example)."""
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]        # …/Hisaab/backend — where scripts run


class Settings:
    def __init__(self) -> None:
        self.app_name = "Hisaab API"
        self.version = "1.0.0"
        self.data_dir = Path(os.getenv("HISAAB_DATA_DIR", _ROOT / "data"))
        self.results_dir = Path(os.getenv("HISAAB_RESULTS_DIR", _ROOT / "results"))
        self.db_path = Path(os.getenv("HISAAB_DB_PATH", _ROOT / "hisaab.db"))
        # Raye sentiment-bridge artefacts (exported by scripts/export_raye.py)
        self.raye_dir = Path(os.getenv("HISAAB_RAYE_DIR", _ROOT / "data" / "raye"))
        self.cors_origins = [o.strip() for o in os.getenv("HISAAB_CORS_ORIGINS", "*").split(",") if o.strip()]

        # Generation / analysis limits
        self.max_rows_per_request = int(os.getenv("HISAAB_MAX_ROWS_PER_REQUEST", "1000000"))
        self.default_budget = float(os.getenv("HISAAB_DEFAULT_BUDGET", "1000000"))
        self.bootstrap_resamples = int(os.getenv("HISAAB_BOOTSTRAP_RESAMPLES", "200"))

        # Benchmark defaults
        self.benchmark_scales = [int(s) for s in os.getenv(
            "HISAAB_BENCHMARK_SCALES", "10000,100000,1000000,10000000").split(",")]
        self.benchmark_repeat = int(os.getenv("HISAAB_BENCHMARK_REPEAT", "3"))


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.results_dir.mkdir(parents=True, exist_ok=True)
