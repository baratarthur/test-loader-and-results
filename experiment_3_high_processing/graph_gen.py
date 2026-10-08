#!/usr/bin/env python3
"""
Generate comparison plots for the monolithic application under different cache sizes.

Expected files:
    dana_metrics_100.csv
    dana_metrics_200.csv
    ...
    dana_metrics_500.csv

    dana_monolith_100_stats.csv
    dana_monolith_200_stats.csv
    ...
    dana_monolith_500_stats.csv

    dana_monolith_100_stats_history.csv
    dana_monolith_200_stats_history.csv
    ...
    dana_monolith_500_stats_history.csv

Optional:
    dana_monolith_<size>_failures.csv
    dana_monolith_<size>_exceptions.csv

The script is deliberately tolerant of missing files. It plots every cache size
for which the corresponding data exists.
"""

from pathlib import Path
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
DATA_DIR = Path("./results_csv")
OUTPUT_DIR = DATA_DIR / "monolith_selected_cache_plots"
CACHE_SIZES = [300, 400, 500]

# If True, response-time plots use the Locust history.
# If False, they use the final *_stats.csv percentile values.
USE_HISTORY = True

# Ignore the first N seconds of each history file to remove warm-up effects.
# Set to 0 if you want the complete experiment.
WARMUP_SECONDS = 10

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def existing(path):
    return path.exists()


def parse_cpu(value):
    """Kubernetes CPU values such as 65m -> 0.065 CPU cores."""
    if pd.isna(value):
        return np.nan

    s = str(value).strip().lower()

    try:
        if s.endswith("n"):
            return float(s[:-1]) / 1e9
        if s.endswith("u"):
            return float(s[:-1]) / 1e6
        if s.endswith("m"):
            return float(s[:-1]) / 1000
        return float(s)
    except ValueError:
        return np.nan


def parse_memory_mib(value):
    """Convert Kubernetes memory strings to MiB."""
    if pd.isna(value):
        return np.nan

    s = str(value).strip()

    units = {
        "Ki": 1 / 1024,
        "Mi": 1,
        "Gi": 1024,
        "Ti": 1024 * 1024,
        "K": 1 / 1024,
        "M": 1,
        "G": 1024,
        "T": 1024 * 1024,
    }

    for unit, multiplier in units.items():
        if s.endswith(unit):
            try:
                return float(s[:-len(unit)]) * multiplier
            except ValueError:
                return np.nan

    try:
        # Assume bytes when no unit is supplied.
        return float(s) / (1024 ** 2)
    except ValueError:
        return np.nan


def cache_size_from_name(path):
    match = re.search(r"_(100|200|300|400|500)(?:_|\.|$)", path.name)
    return int(match.group(1)) if match else None


def load_metrics(cache_size):
    path = DATA_DIR / f"dana_metrics_{cache_size}.csv"
    if not existing(path):
        return None

    df = pd.read_csv(path)

    required = {"timestamp", "CPU", "Memory"}
    missing = required - set(df.columns)
    if missing:
        print(f"[WARN] {path.name}: missing columns {sorted(missing)}")
        return None

    df["cache_size"] = cache_size
    df["cpu_cores"] = df["CPU"].apply(parse_cpu)
    df["memory_mib"] = df["Memory"].apply(parse_memory_mib)

    df["elapsed_s"] = df["timestamp"] - df["timestamp"].iloc[0]

    return df


def load_history(cache_size):
    path = DATA_DIR / f"dana_monolith_{cache_size}_stats_history.csv"
    if not existing(path):
        return None

    df = pd.read_csv(path)

    if "Timestamp" not in df.columns:
        print(f"[WARN] {path.name}: no Timestamp column")
        return None

    # Prefer the aggregated Locust row.
    if "Name" in df.columns:
        aggregated = df[df["Name"].astype(str).str.lower() == "aggregated"]
        if not aggregated.empty:
            df = aggregated.copy()

    df = df.copy()
    df["cache_size"] = cache_size

    df["elapsed_s"] = df["Timestamp"] - df["Timestamp"].iloc[0]

    if WARMUP_SECONDS > 0:
        df = df[df["elapsed_s"] >= WARMUP_SECONDS].copy()

    return df


def load_final_stats(cache_size):
    path = DATA_DIR / f"dana_monolith_{cache_size}_stats.csv"
    if not existing(path):
        return None

    df = pd.read_csv(path)
    df["cache_size"] = cache_size
    return df


# ---------------------------------------------------------------------
# Load all data
# ---------------------------------------------------------------------
metrics = {}
history = {}
final_stats = {}

for size in CACHE_SIZES:
    m = load_metrics(size)
    h = load_history(size)
    s = load_final_stats(size)

    if m is not None:
        metrics[size] = m
    if h is not None:
        history[size] = h
    if s is not None:
        final_stats[size] = s

print("Loaded:")
print("  Metrics:", sorted(metrics))
print("  History:", sorted(history))
print("  Final stats:", sorted(final_stats))

if not metrics and not history and not final_stats:
    raise SystemExit(
        "No input data found. Put the CSV files in DATA_DIR "
        "or change DATA_DIR at the top of the script."
    )

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LINE_STYLES = ["-", "--", "-.", ":", (0, (6, 2, 1, 2)), (0, (3, 1, 1, 1))]
plt.rcParams.update({
    "font.size": 18,
    "axes.titlesize": 24,
    "axes.labelsize": 20,
    "xtick.labelsize": 18,
    "ytick.labelsize": 18,
    "legend.fontsize": 19,
    "legend.title_fontsize": 19,
})

# ---------------------------------------------------------------------
# Plot 1: CPU utilization over time
# ---------------------------------------------------------------------
if metrics:
    fig, ax = plt.subplots(figsize=(16, 8))

    for index, size in enumerate(sorted(metrics)):
        df = metrics[size]
        ax.plot(
            df["elapsed_s"],
            df["cpu_cores"],
            color="black",
            linestyle=LINE_STYLES[index % len(LINE_STYLES)],
            linewidth=2.4,
            label=f"{size} entries",
        )

    ax.set_xlabel("Elapsed time (s)")
    ax.set_ylabel("CPU utilization (cores)")
    ax.set_title("Monolithic Application CPU Utilization by Cache Size")
    ax.tick_params(axis="both", labelsize=18)
    ax.grid(True, linestyle=":", linewidth=0.8, alpha=0.7)
    ax.legend(title="Cache size", title_fontsize=19)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "01_cpu_utilization.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------
# Plot 2: Throughput over time
# ---------------------------------------------------------------------
if history:
    fig, ax = plt.subplots(figsize=(16, 8))

    for index, size in enumerate(sorted(history)):
        df = history[size]
        if "Requests/s" not in df.columns:
            continue

        ax.plot(
            df["elapsed_s"],
            df["Requests/s"],
            color="black",
            linestyle=LINE_STYLES[index % len(LINE_STYLES)],
            linewidth=2.4,
            label=f"{size} entries",
        )

    ax.set_xlabel("Elapsed time (s)")
    ax.set_ylabel("Throughput (requests/s)")
    ax.set_title("Monolithic Application Throughput by Cache Size")
    ax.tick_params(axis="both", labelsize=18)
    ax.grid(True, linestyle=":", linewidth=0.8, alpha=0.7)
    ax.legend(title="Cache size", title_fontsize=19)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "02_throughput.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------
# Plot 3: Percentile latency comparison
# ---------------------------------------------------------------------
if final_stats:
    rows = []

    for size in sorted(final_stats):
        df = final_stats[size]

        # Prefer the aggregated row if it exists.
        if "Name" in df.columns:
            aggregated = df[
                df["Name"].astype(str).str.lower() == "aggregated"
            ]
            if not aggregated.empty:
                row = aggregated.iloc[0]
            else:
                # Otherwise calculate a request-weighted aggregate below.
                row = None
        else:
            row = None

        if row is None:
            # Build a simple request-count-weighted summary for the two
            # endpoints. This is only a fallback; Locust's aggregated row
            # should be preferred when available.
            if "Request Count" not in df.columns:
                continue

            total_requests = df["Request Count"].sum()
            if total_requests <= 0:
                continue

            percentiles = ["50%", "75%", "90%", "95%", "99%", "100%"]
            values = {"cache_size": size}

            for p in percentiles:
                values[p] = np.average(
                    pd.to_numeric(df[p], errors="coerce"),
                    weights=df["Request Count"],
                )

            rows.append(values)
        else:
            values = {"cache_size": size}
            for p in ["50%", "75%", "90%", "95%", "99%", "100%"]:
                values[p] = pd.to_numeric(row[p], errors="coerce")
            rows.append(values)

    percentile_df = pd.DataFrame(rows)

    if not percentile_df.empty:
        fig, ax = plt.subplots(figsize=(16, 8))

        percentiles = ["50%", "75%", "90%", "95%", "99%", "100%"]
        for index, p in enumerate(percentiles):
            if p in percentile_df:
                ax.plot(
                    percentile_df["cache_size"],
                    percentile_df[p],
                    color="black",
                    linestyle=LINE_STYLES[index % len(LINE_STYLES)],
                    marker="o",
                    linewidth=2.4,
                    label=p,
                )

        ax.set_xlabel("Cache size (entries)")
        ax.set_ylabel("Response time (ms)")
        ax.set_title("Response Time Percentiles by Cache Size")
        ax.set_xticks(CACHE_SIZES)
        ax.tick_params(axis="both", labelsize=18)
        ax.grid(True, linestyle=":", linewidth=0.8, alpha=0.7)
        ax.legend(title="Percentile", title_fontsize=19)
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / "03_latency_percentiles.png", dpi=300, bbox_inches="tight")
        plt.close(fig)


# ---------------------------------------------------------------------
# Build a compact summary CSV
# ---------------------------------------------------------------------
summary_rows = []

for size in CACHE_SIZES:
    row = {"cache_size": size}

    # Resource summary
    if size in metrics:
        m = metrics[size]
        row["cpu_mean_cores"] = m["cpu_cores"].mean()
        row["cpu_max_cores"] = m["cpu_cores"].max()
        row["memory_mean_mib"] = m["memory_mib"].mean()
        row["memory_max_mib"] = m["memory_mib"].max()

    # Locust final/aggregated summary
    if size in final_stats:
        s = final_stats[size]

        if "Request Count" in s.columns:
            row["request_count"] = s["Request Count"].sum()

        if "Failure Count" in s.columns:
            row["failure_count"] = s["Failure Count"].sum()

        if "Requests/s" in s.columns:
            row["requests_per_sec"] = s["Requests/s"].sum()

        # Feed endpoint
        if "Name" in s.columns:
            feed = s[s["Name"].astype(str).str.contains(
                r"/feed", case=False, regex=True, na=False
            )]

            if not feed.empty:
                f = feed.iloc[0]
                row["feed_avg_ms"] = f.get("Average Response Time", np.nan)
                row["feed_median_ms"] = f.get("Median Response Time", np.nan)
                row["feed_p95_ms"] = f.get("95%", np.nan)
                row["feed_p99_ms"] = f.get("99%", np.nan)
                row["feed_max_ms"] = f.get("Max Response Time", np.nan)

    summary_rows.append(row)

summary = pd.DataFrame(summary_rows)
summary.to_csv(OUTPUT_DIR / "cache_size_summary.csv", index=False)

print(f"\nPlots written to: {OUTPUT_DIR.resolve()}")
print(f"Summary written to: {(OUTPUT_DIR / 'cache_size_summary.csv').resolve()}")
print("\nGenerated files:")
for path in sorted(OUTPUT_DIR.glob("*")):
    print(" ", path.name)
