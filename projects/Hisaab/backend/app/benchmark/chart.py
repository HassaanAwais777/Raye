"""Runtime chart: log-log scaling lines per engine (matplotlib)."""
from pathlib import Path
from typing import Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm           # noqa: E402
import matplotlib.pyplot as plt                # noqa: E402

from ..config import settings                  # noqa: E402

# Chinese-capable font registration (defensive; labels here are English but rules are rules)
for fp in ("/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf",):
    try:
        fm.fontManager.addfont(fp)
    except Exception:                          # noqa: BLE001
        pass
plt.rcParams["font.sans-serif"] = ["Noto Sans SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

STYLE = {
    "pandas": dict(color="#3776ab", marker="o"),
    "mapreduce": dict(color="#e97627", marker="s"),
    "mapreduce-parallel": dict(color="#f2a25c", marker="s", linestyle="--"),
    "spark": dict(color="#e25a1c", marker="^"),
    "polars": dict(color="#0f9d58", marker="D"),
}
LABEL = {"pandas": "Pandas", "mapreduce": "MapReduce (1 proc)",
         "mapreduce-parallel": "MapReduce (parallel splits)",
         "spark": "PySpark (local)", "polars": "Polars"}


def plot_runtimes(payload: dict, out_path: Path = None) -> Path:
    results: Dict[str, Dict[str, dict]] = payload["results"]
    scales = payload["scales"]
    fig, ax = plt.subplots(figsize=(8.5, 5.2), constrained_layout=True)

    plotted = 0
    for engine, by_scale in results.items():
        xs, ys = [], []
        for s in scales:
            r = by_scale.get(str(s), {})
            if r.get("seconds") is not None:
                xs.append(s)
                ys.append(r["seconds"])
        if not xs:
            continue
        ax.plot(xs, ys, label=LABEL.get(engine, engine), linewidth=2.2,
                markersize=6, **{k: v for k, v in STYLE.get(engine, {}).items()})
        plotted += 1

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Dataset size (rows)")
    ax.set_ylabel("Median wall time (seconds)")
    ax.set_title("Hisaab scaling benchmark — same aggregation, four architectures")
    ax.grid(True, which="both", alpha=0.25)
    if plotted:
        ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    ax.set_xticks(scales)
    ax.set_xticklabels([f"{s:,}" for s in scales])

    out = Path(out_path or (settings.results_dir / "runtime_chart.png"))
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return out
