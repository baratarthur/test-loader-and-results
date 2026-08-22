#!/usr/bin/env python3
"""
Plot monolithic/distributed resource behavior for the new metrics format.

New metrics files:
    dana_metrics_r_3c_100.csv
    dana_metrics_r_3c_200.csv
    dana_metrics_r_3c_300.csv
    dana_metrics_r_3c_400.csv
    dana_metrics_r_3c_500.csv

Expected metrics columns:
    timestamp,dana_cpu,dana_mem,remote_cpu,remote_mem

The script also supports the Locust files if they follow:
    dana_monolith_100_stats.csv
    dana_monolith_100_stats_history.csv
    ...

All plots are written to:
    monolith_cache_plots_r_3c/
"""

from pathlib import Path
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ================================================================
# Configuration
# ================================================================
DATA_DIR = Path("./results_csv/replicate")
OUTPUT_DIR = DATA_DIR / "monolith_cache_plots_r_3c"

CACHE_SIZES = [100, 200, 300, 400, 500]

# New metrics filename pattern.
METRICS_PATTERN = "dana_metrics_r_3c_{cache}.csv"

# Locust files can remain in the old format.
STATS_PATTERN = "dana_r_3c_{cache}_stats.csv"
HISTORY_PATTERN = "dana_r_3c_{cache}_stats_history.csv"

# Ignore initial warm-up period in history plots.
WARMUP_SECONDS = 10


# ================================================================
# Parsing helpers
# ================================================================
def parse_cpu(value):
    """
    Convert Kubernetes CPU quantities to CPU cores.

    Examples:
        54m   -> 0.054 cores
        1077m -> 1.077 cores
        1     -> 1.0 cores
    """
    if pd.isna(value):
        return np.nan

    s = str(value).strip()

    try:
        if s.endswith("n"):
            return float(s[:-1]) / 1_000_000_000
        if s.endswith("u"):
            return float(s[:-1]) / 1_000_000
        if s.endswith("m"):
            return float(s[:-1]) / 1000
        return float(s)
    except ValueError:
        return np.nan


def parse_memory_mib(value):
    """
    Convert Kubernetes memory quantities to MiB.

    Examples:
        38Mi  -> 38
        1Gi   -> 1024
        500Ki -> 0.488...
    """
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
        # If no unit exists, assume bytes.
        return float(s) / (1024 ** 2)
    except ValueError:
        return np.nan


def load_metrics(cache_size):
    """
    Load the new resource metrics format:
        timestamp,dana_cpu,dana_mem,remote_cpu,remote_mem
    """
    path = DATA_DIR / METRICS_PATTERN.format(cache=cache_size)

    if not path.exists():
        print(f"[WARN] Missing metrics file: {path.name}")
        return None

    df = pd.read_csv(path)

    required = {
        "timestamp",
        "dana_cpu",
        "dana_mem",
        "remote_cpu",
        "remote_mem",
    }

    missing = required - set(df.columns)

    if missing:
        print(
            f"[WARN] {path.name}: missing columns "
            f"{sorted(missing)}"
        )
        return None

    df = df.copy()

    df["dana_cpu_cores"] = df["dana_cpu"].apply(parse_cpu)
    df["remote_cpu_cores"] = df["remote_cpu"].apply(parse_cpu)

    df["dana_memory_mib"] = df["dana_mem"].apply(parse_memory_mib)
    df["remote_memory_mib"] = df["remote_mem"].apply(parse_memory_mib)

    df["total_cpu_cores"] = (
        df["dana_cpu_cores"] +
        df["remote_cpu_cores"]
    )

    df["total_memory_mib"] = (
        df["dana_memory_mib"] +
        df["remote_memory_mib"]
    )

    # Make time relative to the beginning of each experiment.
    df["elapsed_s"] = (
        df["timestamp"] - df["timestamp"].iloc[0]
    )

    df["cache_size"] = cache_size

    return df


def load_history(cache_size):
    path = DATA_DIR / HISTORY_PATTERN.format(cache=cache_size)

    if not path.exists():
        return None

    df = pd.read_csv(path)

    if "Timestamp" not in df.columns:
        print(f"[WARN] {path.name}: no Timestamp column")
        return None

    # Prefer Locust's Aggregated row.
    if "Name" in df.columns:
        aggregated = df[
            df["Name"].astype(str).str.lower() == "aggregated"
        ]

        if not aggregated.empty:
            df = aggregated.copy()

    df = df.copy()

    df["elapsed_s"] = (
        df["Timestamp"] - df["Timestamp"].iloc[0]
    )

    if WARMUP_SECONDS > 0:
        df = df[
            df["elapsed_s"] >= WARMUP_SECONDS
        ].copy()

    return df


def load_stats(cache_size):
    path = DATA_DIR / STATS_PATTERN.format(cache=cache_size)

    if not path.exists():
        return None

    return pd.read_csv(path)


# ================================================================
# Load experiments
# ================================================================
metrics = {}
history = {}
stats = {}

for cache in CACHE_SIZES:

    m = load_metrics(cache)
    if m is not None:
        metrics[cache] = m

    h = load_history(cache)
    if h is not None:
        history[cache] = h

    s = load_stats(cache)
    if s is not None:
        stats[cache] = s


if not metrics:
    raise SystemExit(
        "No new metrics files were found.\n"
        "Expected files such as:\n"
        "  dana_metrics_r_3c_100.csv\n"
        "  dana_metrics_r_3c_200.csv\n"
        "  dana_metrics_r_3c_300.csv\n"
        "  dana_metrics_r_3c_400.csv\n"
        "  dana_metrics_r_3c_500.csv"
    )


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("\nLoaded metrics:")
for cache, df in metrics.items():
    print(
        f"  cache={cache}: "
        f"{len(df)} samples"
    )


# ================================================================
# 1. Dana CPU
# ================================================================
plt.figure(figsize=(10, 5))

for cache in sorted(metrics):
    df = metrics[cache]

    plt.plot(
        df["elapsed_s"],
        df["dana_cpu_cores"],
        linewidth=1.8,
        label=f"Cache {cache}",
    )

plt.xlabel("Elapsed time (s)")
plt.ylabel("Dana CPU usage (cores)")
plt.title("Monolithic application: Dana CPU usage")
plt.grid(True, alpha=0.25)
plt.legend()
plt.tight_layout()
plt.savefig(
    OUTPUT_DIR / "01_dana_cpu.png",
    dpi=300,
)
plt.close()


# ================================================================
# 2. Remote CPU
# ================================================================
plt.figure(figsize=(10, 5))

for cache in sorted(metrics):
    df = metrics[cache]

    plt.plot(
        df["elapsed_s"],
        df["remote_cpu_cores"],
        linewidth=1.8,
        label=f"Cache {cache}",
    )

plt.xlabel("Elapsed time (s)")
plt.ylabel("Remote CPU usage (cores)")
plt.title("Remote component CPU usage vs. cache size")
plt.grid(True, alpha=0.25)
plt.legend()
plt.tight_layout()
plt.savefig(
    OUTPUT_DIR / "02_remote_cpu.png",
    dpi=300,
)
plt.close()


# ================================================================
# 3. Total CPU
# ================================================================
plt.figure(figsize=(10, 5))

for cache in sorted(metrics):
    df = metrics[cache]

    plt.plot(
        df["elapsed_s"],
        df["total_cpu_cores"],
        linewidth=1.8,
        label=f"Cache {cache}",
    )

plt.xlabel("Elapsed time (s)")
plt.ylabel("Total CPU usage (cores)")
plt.title("Total CPU consumption vs. cache size")
plt.grid(True, alpha=0.25)
plt.legend()
plt.tight_layout()
plt.savefig(
    OUTPUT_DIR / "03_total_cpu.png",
    dpi=300,
)
plt.close()


# ================================================================
# 4. Dana memory
# ================================================================
plt.figure(figsize=(10, 5))

for cache in sorted(metrics):
    df = metrics[cache]

    plt.plot(
        df["elapsed_s"],
        df["dana_memory_mib"],
        linewidth=1.8,
        label=f"Cache {cache}",
    )

plt.xlabel("Elapsed time (s)")
plt.ylabel("Dana memory (MiB)")
plt.title("Monolithic application: Dana memory usage")
plt.grid(True, alpha=0.25)
plt.legend()
plt.tight_layout()
plt.savefig(
    OUTPUT_DIR / "04_dana_memory.png",
    dpi=300,
)
plt.close()


# ================================================================
# 5. Remote memory
# ================================================================
plt.figure(figsize=(10, 5))

for cache in sorted(metrics):
    df = metrics[cache]

    plt.plot(
        df["elapsed_s"],
        df["remote_memory_mib"],
        linewidth=1.8,
        label=f"Cache {cache}",
    )

plt.xlabel("Elapsed time (s)")
plt.ylabel("Remote memory (MiB)")
plt.title("Remote component memory usage vs. cache size")
plt.grid(True, alpha=0.25)
plt.legend()
plt.tight_layout()
plt.savefig(
    OUTPUT_DIR / "05_remote_memory.png",
    dpi=300,
)
plt.close()


# ================================================================
# 6. Total memory
# ================================================================
plt.figure(figsize=(10, 5))

for cache in sorted(metrics):
    df = metrics[cache]

    plt.plot(
        df["elapsed_s"],
        df["total_memory_mib"],
        linewidth=1.8,
        label=f"Cache {cache}",
    )

plt.xlabel("Elapsed time (s)")
plt.ylabel("Total memory (MiB)")
plt.title("Total memory consumption vs. cache size")
plt.grid(True, alpha=0.25)
plt.legend()
plt.tight_layout()
plt.savefig(
    OUTPUT_DIR / "06_total_memory.png",
    dpi=300,
)
plt.close()


# ================================================================
# 7. CPU vs cache size
# ================================================================
cpu_summary = []

for cache in sorted(metrics):
    df = metrics[cache]

    cpu_summary.append({
        "cache_size": cache,
        "dana_mean": df["dana_cpu_cores"].mean(),
        "dana_max": df["dana_cpu_cores"].max(),
        "remote_mean": df["remote_cpu_cores"].mean(),
        "remote_max": df["remote_cpu_cores"].max(),
        "total_mean": df["total_cpu_cores"].mean(),
        "total_max": df["total_cpu_cores"].max(),
    })

cpu_summary = pd.DataFrame(cpu_summary)

plt.figure(figsize=(10, 5))

plt.plot(
    cpu_summary["cache_size"],
    cpu_summary["dana_mean"],
    marker="o",
    linewidth=1.8,
    label="Dana mean",
)

plt.plot(
    cpu_summary["cache_size"],
    cpu_summary["remote_mean"],
    marker="o",
    linewidth=1.8,
    label="Remote mean",
)

plt.plot(
    cpu_summary["cache_size"],
    cpu_summary["total_mean"],
    marker="o",
    linewidth=1.8,
    label="Total mean",
)

plt.xlabel("Cache size (entries)")
plt.ylabel("Mean CPU usage (cores)")
plt.title("Mean CPU consumption vs. cache size")
plt.xticks(CACHE_SIZES)
plt.grid(True, alpha=0.25)
plt.legend()
plt.tight_layout()
plt.savefig(
    OUTPUT_DIR / "07_mean_cpu_vs_cache.png",
    dpi=300,
)
plt.close()


# ================================================================
# 8. Memory vs cache size
# ================================================================
memory_summary = []

for cache in sorted(metrics):
    df = metrics[cache]

    memory_summary.append({
        "cache_size": cache,
        "dana_mean": df["dana_memory_mib"].mean(),
        "remote_mean": df["remote_memory_mib"].mean(),
        "total_mean": df["total_memory_mib"].mean(),
        "dana_max": df["dana_memory_mib"].max(),
        "remote_max": df["remote_memory_mib"].max(),
        "total_max": df["total_memory_mib"].max(),
    })

memory_summary = pd.DataFrame(memory_summary)

plt.figure(figsize=(10, 5))

plt.plot(
    memory_summary["cache_size"],
    memory_summary["dana_mean"],
    marker="o",
    linewidth=1.8,
    label="Dana mean",
)

plt.plot(
    memory_summary["cache_size"],
    memory_summary["remote_mean"],
    marker="o",
    linewidth=1.8,
    label="Remote mean",
)

plt.plot(
    memory_summary["cache_size"],
    memory_summary["total_mean"],
    marker="o",
    linewidth=1.8,
    label="Total mean",
)

plt.xlabel("Cache size (entries)")
plt.ylabel("Mean memory usage (MiB)")
plt.title("Mean memory consumption vs. cache size")
plt.xticks(CACHE_SIZES)
plt.grid(True, alpha=0.25)
plt.legend()
plt.tight_layout()
plt.savefig(
    OUTPUT_DIR / "08_mean_memory_vs_cache.png",
    dpi=300,
)
plt.close()


# ================================================================
# 9. Locust throughput vs cache
# ================================================================
throughput_rows = []

for cache in sorted(history):
    df = history[cache]

    if "Requests/s" not in df.columns:
        continue

    throughput_rows.append({
        "cache_size": cache,
        "requests_per_second": pd.to_numeric(
            df["Requests/s"],
            errors="coerce",
        ).mean(),
    })

throughput_df = pd.DataFrame(throughput_rows)

if not throughput_df.empty:

    plt.figure(figsize=(10, 5))

    plt.plot(
        throughput_df["cache_size"],
        throughput_df["requests_per_second"],
        marker="o",
        linewidth=1.8,
    )

    plt.xlabel("Cache size (entries)")
    plt.ylabel("Requests/s")
    plt.title("Throughput vs. cache size")
    plt.xticks(CACHE_SIZES)
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "09_throughput_vs_cache.png",
        dpi=300,
    )
    plt.close()


# ================================================================
# 10. Locust latency vs cache
# ================================================================
latency_rows = []

for cache in sorted(history):
    df = history[cache]

    if "Total Average Response Time" not in df.columns:
        continue

    latency_rows.append({
        "cache_size": cache,
        "average_latency_ms": pd.to_numeric(
            df["Total Average Response Time"],
            errors="coerce",
        ).mean(),
    })

latency_df = pd.DataFrame(latency_rows)

if not latency_df.empty:

    plt.figure(figsize=(10, 5))

    plt.plot(
        latency_df["cache_size"],
        latency_df["average_latency_ms"],
        marker="o",
        linewidth=1.8,
    )

    plt.xlabel("Cache size (entries)")
    plt.ylabel("Average response time (ms)")
    plt.title("Average latency vs. cache size")
    plt.xticks(CACHE_SIZES)
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "10_average_latency_vs_cache.png",
        dpi=300,
    )
    plt.close()


# ================================================================
# 11. Latency percentiles vs cache
# ================================================================
percentile_rows = []

for cache in sorted(stats):

    df = stats[cache]

    if "Name" not in df.columns:
        continue

    aggregated = df[
        df["Name"].astype(str).str.lower() == "aggregated"
    ]

    if aggregated.empty:
        continue

    row = aggregated.iloc[0]

    percentile_rows.append({
        "cache_size": cache,
        "p50": pd.to_numeric(row.get("50%"), errors="coerce"),
        "p75": pd.to_numeric(row.get("75%"), errors="coerce"),
        "p90": pd.to_numeric(row.get("90%"), errors="coerce"),
        "p95": pd.to_numeric(row.get("95%"), errors="coerce"),
        "p99": pd.to_numeric(row.get("99%"), errors="coerce"),
    })

percentile_df = pd.DataFrame(percentile_rows)

if not percentile_df.empty:

    plt.figure(figsize=(10, 5))

    for column, label in [
        ("p50", "P50"),
        ("p75", "P75"),
        ("p90", "P90"),
        ("p95", "P95"),
        ("p99", "P99"),
    ]:

        plt.plot(
            percentile_df["cache_size"],
            percentile_df[column],
            marker="o",
            linewidth=1.8,
            label=label,
        )

    plt.xlabel("Cache size (entries)")
    plt.ylabel("Response time (ms)")
    plt.title("Latency percentiles vs. cache size")
    plt.xticks(CACHE_SIZES)
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "11_latency_percentiles_vs_cache.png",
        dpi=300,
    )
    plt.close()


# ================================================================
# 12. Combined summary CSV
# ================================================================
summary = cpu_summary.merge(
    memory_summary,
    on="cache_size",
    suffixes=("_cpu", "_memory"),
    how="outer",
)

if not throughput_df.empty:
    summary = summary.merge(
        throughput_df,
        on="cache_size",
        how="left",
    )

if not latency_df.empty:
    summary = summary.merge(
        latency_df,
        on="cache_size",
        how="left",
    )

if not percentile_df.empty:
    summary = summary.merge(
        percentile_df,
        on="cache_size",
        how="left",
    )

summary.to_csv(
    OUTPUT_DIR / "cache_size_summary.csv",
    index=False,
)


# ================================================================
# Final report
# ================================================================
print("\nGenerated plots:")
for path in sorted(OUTPUT_DIR.glob("*.png")):
    print(f"  {path.name}")

print(
    f"\nSummary:\n  "
    f"{OUTPUT_DIR / 'cache_size_summary.csv'}"
)

print("\nDone.")
