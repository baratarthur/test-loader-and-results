#!/usr/bin/env python3
"""Generate selected cache comparison plots for fragmentation and replication."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


CACHE_SIZES = [200, 300, 400, 500]
EXPERIMENTS = {
    "fragment": {
        "label": "Fragmentation",
        "data_dir": Path("results_csv/fragment"),
        "output_dir": Path("results_csv/fragment/plots_cache_200_300_400_500"),
        "metrics_pattern": "dana_metrics_f_3c_{cache}.csv",
        "stats_pattern": "dana_f_3c_{cache}_stats.csv",
    },
    "replicate": {
        "label": "Replication",
        "data_dir": Path("results_csv/replicate"),
        "output_dir": Path("results_csv/replicate/plots_cache_200_300_400_500"),
        "metrics_pattern": "dana_metrics_r_3c_{cache}.csv",
        "stats_pattern": "dana_r_3c_{cache}_stats.csv",
    },
}

CACHE_LINE_STYLES = ["-", "--", "-.", ":"]
PERCENTILE_LINE_STYLES = ["-", "--", "-.", ":", (0, (8, 2, 1, 2))]
PERCENTILES = [("50%", "P50"), ("75%", "P75"), ("90%", "P90"), ("95%", "P95"), ("99%", "P99")]

plt.rcParams.update({
    "font.size": 18,
    "axes.titlesize": 24,
    "axes.labelsize": 20,
    "xtick.labelsize": 18,
    "ytick.labelsize": 18,
    "legend.fontsize": 19,
    "legend.title_fontsize": 19,
})


def parse_cpu(value):
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    try:
        if text.endswith("n"):
            return float(text[:-1]) / 1_000_000_000
        if text.endswith("u"):
            return float(text[:-1]) / 1_000_000
        if text.endswith("m"):
            return float(text[:-1]) / 1000
        return float(text)
    except ValueError:
        return np.nan


def parse_memory_mib(value):
    if pd.isna(value):
        return np.nan

    text = str(value).strip()
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
        if text.endswith(unit):
            try:
                return float(text[:-len(unit)]) * multiplier
            except ValueError:
                return np.nan

    try:
        return float(text) / (1024 ** 2)
    except ValueError:
        return np.nan


def load_metrics(config, cache_size):
    path = config["data_dir"] / config["metrics_pattern"].format(cache=cache_size)
    if not path.exists():
        print(f"[WARN] Missing metrics file: {path}")
        return None

    df = pd.read_csv(path)
    required = {"timestamp", "dana_cpu", "dana_mem", "remote_cpu", "remote_mem"}
    missing = required - set(df.columns)
    if missing:
        print(f"[WARN] {path}: missing columns {sorted(missing)}")
        return None

    df = df.copy()
    df["dana_cpu_cores"] = df["dana_cpu"].apply(parse_cpu)
    df["dana_memory_mib"] = df["dana_mem"].apply(parse_memory_mib)
    df["remote_memory_mib"] = df["remote_mem"].apply(parse_memory_mib)
    df["total_memory_mib"] = df["dana_memory_mib"] + df["remote_memory_mib"]
    timestamp = pd.to_numeric(df["timestamp"], errors="coerce")
    df["elapsed_s"] = timestamp - timestamp.iloc[0]
    return df


def load_stats(config, cache_size):
    path = config["data_dir"] / config["stats_pattern"].format(cache=cache_size)
    if not path.exists():
        print(f"[WARN] Missing stats file: {path}")
        return None
    return pd.read_csv(path)


def make_time_series_plot(config, metrics, value_column, y_label, title, filename):
    fig, ax = plt.subplots(figsize=(16, 8))
    for index, cache_size in enumerate(CACHE_SIZES):
        df = metrics.get(cache_size)
        if df is None:
            continue
        ax.plot(
            df["elapsed_s"],
            df[value_column],
            color="black",
            linestyle=CACHE_LINE_STYLES[index],
            linewidth=2.6,
            label=f"Cache {cache_size}",
        )

    ax.set_xlabel("Elapsed time (s)")
    ax.set_ylabel(y_label)
    ax.set_title(f"{config['label']}: {title}")
    ax.tick_params(axis="both", labelsize=18)
    ax.grid(True, linestyle=":", linewidth=0.8, alpha=0.7)
    ax.legend(
        title="Cache size",
        title_fontsize=19,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
    )
    fig.tight_layout(rect=(0, 0, 0.78, 1))
    fig.savefig(config["output_dir"] / filename, dpi=300, bbox_inches="tight")
    plt.close(fig)


def make_percentile_plot(config, stats_by_size):
    rows = []
    for cache_size in CACHE_SIZES:
        df = stats_by_size.get(cache_size)
        if df is None or "Name" not in df.columns:
            continue

        aggregated = df[df["Name"].astype(str).str.lower() == "aggregated"]
        if aggregated.empty:
            continue

        row = aggregated.iloc[0]
        values = {"cache_size": cache_size}
        for column, _label in PERCENTILES:
            values[column] = pd.to_numeric(row.get(column), errors="coerce")
        rows.append(values)

    percentiles = pd.DataFrame(rows)
    if percentiles.empty:
        print(f"[WARN] No aggregated percentile rows found for {config['label']}.")
        return

    fig, ax = plt.subplots(figsize=(16, 8))
    for index, (column, label) in enumerate(PERCENTILES):
        ax.plot(
            percentiles["cache_size"],
            percentiles[column],
            color="black",
            linestyle=PERCENTILE_LINE_STYLES[index],
            marker="o",
            markersize=8,
            linewidth=2.6,
            label=label,
        )

    ax.set_xlabel("Cache size (entries)")
    ax.set_ylabel("Response time (ms)")
    ax.set_title(f"{config['label']}: Latency percentiles by cache size")
    ax.set_xticks(CACHE_SIZES)
    ax.tick_params(axis="both", labelsize=18)
    ax.grid(True, linestyle=":", linewidth=0.8, alpha=0.7)
    ax.legend(
        title="Percentile",
        title_fontsize=19,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
    )
    fig.tight_layout(rect=(0, 0, 0.78, 1))
    fig.savefig(
        config["output_dir"] / "11_latency_percentiles_vs_cache.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)


def make_throughput_plot(config, stats_by_size):
    rows = []
    for cache_size in CACHE_SIZES:
        df = stats_by_size.get(cache_size)
        if df is None or "Name" not in df.columns or "Requests/s" not in df.columns:
            continue

        aggregated = df[df["Name"].astype(str).str.lower() == "aggregated"]
        if aggregated.empty:
            continue
        rows.append({
            "cache_size": cache_size,
            "throughput": pd.to_numeric(aggregated.iloc[0]["Requests/s"], errors="coerce"),
        })

    throughput = pd.DataFrame(rows).dropna(subset=["throughput"])
    if throughput.empty:
        print(f"[WARN] No aggregated throughput rows found for {config['label']}.")
        return

    fig, ax = plt.subplots(figsize=(16, 8))
    ax.plot(
        throughput["cache_size"],
        throughput["throughput"],
        color="black",
        linestyle="-",
        marker="o",
        markersize=9,
        linewidth=2.8,
    )
    for cache_size, value in zip(throughput["cache_size"], throughput["throughput"]):
        ax.annotate(
            f"{value:.2f}",
            (cache_size, value),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=16,
        )
    ax.set_xlabel("Cache size (entries)")
    ax.set_ylabel("Throughput (requests/s)")
    ax.set_title(f"{config['label']}: Throughput by cache size")
    ax.set_xticks(CACHE_SIZES)
    ax.set_ylim(bottom=0, top=max(throughput["throughput"]) * 1.12)
    ax.tick_params(axis="both", labelsize=18)
    ax.grid(True, linestyle=":", linewidth=0.8, alpha=0.7)
    fig.tight_layout()
    fig.savefig(
        config["output_dir"] / "01_throughput_vs_cache.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)


def generate_experiment(config):
    metrics = {}
    stats = {}
    for cache_size in CACHE_SIZES:
        metrics_df = load_metrics(config, cache_size)
        stats_df = load_stats(config, cache_size)
        if metrics_df is not None:
            metrics[cache_size] = metrics_df
        if stats_df is not None:
            stats[cache_size] = stats_df

    if not metrics or not stats:
        print(f"[WARN] Skipping {config['label']}: required metric or stats data is missing.")
        return

    config["output_dir"].mkdir(parents=True, exist_ok=True)
    print(f"\n{config['label']} loaded cache sizes:")
    print(f"  Metrics: {sorted(metrics)}")
    print(f"  Stats:   {sorted(stats)}")

    make_throughput_plot(config, stats)
    make_time_series_plot(
        config,
        metrics,
        "total_memory_mib",
        "Total memory (MiB)",
        "Total memory by cache size",
        "06_total_memory.png",
    )
    make_percentile_plot(config, stats)

    print(f"Plots written to: {config['output_dir'].resolve()}")
    for path in sorted(config["output_dir"].glob("*.png")):
        print(f"  {path.name}")


for experiment in EXPERIMENTS.values():
    generate_experiment(experiment)
