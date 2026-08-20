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
OUTPUT_DIR = DATA_DIR / "monolith_cache_plots"
CACHE_SIZES = [100, 200, 300, 400, 500]

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


# ---------------------------------------------------------------------
# Plot 1: CPU usage over time
# ---------------------------------------------------------------------
if metrics:
    plt.figure(figsize=(10, 5))

    for size in sorted(metrics):
        df = metrics[size]
        plt.plot(
            df["elapsed_s"],
            df["cpu_cores"],
            linewidth=1.8,
            label=f"{size} entries",
        )

    plt.xlabel("Elapsed time (s)")
    plt.ylabel("CPU usage (cores)")
    plt.title("Monolithic application CPU usage vs. cache size")
    plt.grid(True, alpha=0.25)
    plt.legend(title="Cache size")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "01_cpu_usage.png", dpi=300)
    plt.close()


# ---------------------------------------------------------------------
# Plot 2: Memory usage over time
# ---------------------------------------------------------------------
if metrics:
    plt.figure(figsize=(10, 5))

    for size in sorted(metrics):
        df = metrics[size]
        plt.plot(
            df["elapsed_s"],
            df["memory_mib"],
            linewidth=1.8,
            label=f"{size} entries",
        )

    plt.xlabel("Elapsed time (s)")
    plt.ylabel("Memory usage (MiB)")
    plt.title("Monolithic application memory usage vs. cache size")
    plt.grid(True, alpha=0.25)
    plt.legend(title="Cache size")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "02_memory_usage.png", dpi=300)
    plt.close()


# ---------------------------------------------------------------------
# Plot 3: Throughput over time
# ---------------------------------------------------------------------
if history:
    plt.figure(figsize=(10, 5))

    for size in sorted(history):
        df = history[size]

        if "Requests/s" not in df.columns:
            continue

        plt.plot(
            df["elapsed_s"],
            df["Requests/s"],
            linewidth=1.8,
            label=f"{size} entries",
        )

    plt.xlabel("Elapsed time (s)")
    plt.ylabel("Requests/s")
    plt.title("Monolithic application throughput vs. cache size")
    plt.grid(True, alpha=0.25)
    plt.legend(title="Cache size")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "03_throughput.png", dpi=300)
    plt.close()


# ---------------------------------------------------------------------
# Plot 4: Average response time over time
# ---------------------------------------------------------------------
if history:
    plt.figure(figsize=(10, 5))

    for size in sorted(history):
        df = history[size]

        if "Total Average Response Time" not in df.columns:
            continue

        plt.plot(
            df["elapsed_s"],
            df["Total Average Response Time"],
            linewidth=1.8,
            label=f"{size} entries",
        )

    plt.xlabel("Elapsed time (s)")
    plt.ylabel("Average response time (ms)")
    plt.title("Monolithic application latency vs. cache size")
    plt.grid(True, alpha=0.25)
    plt.legend(title="Cache size")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "04_average_latency.png", dpi=300)
    plt.close()


# ---------------------------------------------------------------------
# Plot 5: Percentile latency comparison
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
        plt.figure(figsize=(10, 5))

        for p in ["50%", "75%", "90%", "95%", "99%", "100%"]:
            if p in percentile_df:
                plt.plot(
                    percentile_df["cache_size"],
                    percentile_df[p],
                    marker="o",
                    linewidth=1.8,
                    label=p,
                )

        plt.xlabel("Cache size (entries)")
        plt.ylabel("Response time (ms)")
        plt.title("Latency percentiles vs. cache size")
        plt.xticks(CACHE_SIZES)
        plt.grid(True, alpha=0.25)
        plt.legend(title="Percentile")
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / "05_latency_percentiles.png", dpi=300)
        plt.close()


# ---------------------------------------------------------------------
# Plot 6: Feed endpoint latency
# ---------------------------------------------------------------------
if final_stats:
    feed_rows = []

    for size in sorted(final_stats):
        df = final_stats[size]

        if "Name" not in df.columns:
            continue

        feed = df[df["Name"].astype(str).str.contains(
            r"/feed", case=False, regex=True, na=False
        )]

        if feed.empty:
            continue

        row = feed.iloc[0]

        feed_rows.append({
            "cache_size": size,
            "median": row.get("Median Response Time", np.nan),
            "average": row.get("Average Response Time", np.nan),
            "p95": row.get("95%", np.nan),
            "p99": row.get("99%", np.nan),
            "max": row.get("Max Response Time", np.nan),
        })

    feed_df = pd.DataFrame(feed_rows)

    if not feed_df.empty:
        plt.figure(figsize=(10, 5))

        for column, label in [
            ("median", "Median"),
            ("average", "Average"),
            ("p95", "P95"),
            ("p99", "P99"),
        ]:
            plt.plot(
                feed_df["cache_size"],
                feed_df[column],
                marker="o",
                linewidth=1.8,
                label=label,
            )

        plt.xlabel("Cache size (entries)")
        plt.ylabel("Response time (ms)")
        plt.title("GET /feed latency vs. cache size")
        plt.xticks(CACHE_SIZES)
        plt.grid(True, alpha=0.25)
        plt.legend()
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / "06_feed_latency.png", dpi=300)
        plt.close()


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