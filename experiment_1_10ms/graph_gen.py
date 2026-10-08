from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


DATASETS = {
    "dana": {
        "locust": "results_csv/dana_stats_history.csv",
        "resources": "results_csv/dana_metrics_cpu.csv",
    },
    "python": {
        "locust": "results_csv/python_stats_history.csv",
        "resources": "results_csv/python_metrics_cpu.csv",
    },
}

NUMERIC_COLUMNS = [
    "User Count",
    "Requests/s",
    "Failures/s",
    "50%",
    "66%",
    "75%",
    "80%",
    "90%",
    "95%",
    "98%",
    "99%",
    "99.9%",
    "99.99%",
    "100%",
    "Total Request Count",
    "Total Failure Count",
    "Total Median Response Time",
    "Total Average Response Time",
    "Total Min Response Time",
    "Total Max Response Time",
    "Total Average Content Size",
    "CPU",
    "Memory",
]


def convert_memory(value):
    value = str(value).strip()
    units = {"Ki": 1 / 1024, "Mi": 1, "Gi": 1024, "Ti": 1024 * 1024}

    for unit, multiplier in units.items():
        if value.endswith(unit):
            return float(value[: -len(unit)]) * multiplier

    return float(value)


def make_chart(merged, dataset_name):
    fig, ax1 = plt.subplots(figsize=(16, 8))
    ax1.set_xlabel("Sample", fontsize=20)
    ax1.set_ylabel("Latency (ms)", fontsize=20)

    ax1.plot(
        merged["Sample"],
        merged["Total Average Response Time"],
        color="black",
        linestyle="-",
        linewidth=2.5,
        label="Avg Response Time",
    )
    ax1.plot(
        merged["Sample"],
        merged["95%"],
        color="black",
        linestyle="--",
        linewidth=2,
        label="95th Percentile",
    )
    ax1.tick_params(axis="both", labelsize=18)

    ax2 = ax1.twinx()
    ax2.set_ylabel("CPU (mCPU)", fontsize=20)
    ax2.plot(
        merged["Sample"],
        merged["CPU"],
        color="black",
        linestyle="-.",
        linewidth=2,
        label="CPU",
    )
    ax2.tick_params(axis="y", labelsize=18)

    lines = ax1.get_lines() + ax2.get_lines()
    ax1.legend(
        lines,
        [line.get_label() for line in lines],
        loc="upper left",
        fontsize=19,
        frameon=True,
    )
    ax1.set_title(
        f"Experiment 1 (10 ms) — {dataset_name.title()}: Response Time and CPU",
        fontsize=24,
    )
    ax1.grid(axis="both", linestyle=":", linewidth=0.8, color="gray", alpha=0.7)
    fig.tight_layout()

    output_path = Path("images") / f"latency_response_time_cpu_{dataset_name}.png"
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Chart saved to {output_path}")


def process_dataset(dataset_name, paths):
    locust = pd.read_csv(paths["locust"])
    resources = pd.read_csv(paths["resources"])

    resources["timestamp"] = pd.to_datetime(resources["timestamp"], unit="s")
    resources["CPU"] = (
        resources["CPU"].astype(str).str.replace("m", "", regex=False).astype(float)
    )
    resources["Memory"] = resources["Memory"].apply(convert_memory)

    sample_count = min(len(locust), len(resources))
    locust = locust.iloc[:sample_count].reset_index(drop=True)
    resources = resources.iloc[:sample_count].reset_index(drop=True)

    merged = locust.copy()
    merged["Captured Timestamp"] = resources["timestamp"]
    merged["CPU"] = pd.to_numeric(resources["CPU"], errors="coerce")
    merged["Memory"] = pd.to_numeric(resources["Memory"], errors="coerce")
    merged.insert(0, "Sample", range(sample_count))

    for column in NUMERIC_COLUMNS:
        if column in merged.columns:
            merged[column] = pd.to_numeric(merged[column], errors="coerce")

    merged_path = Path("results_csv") / f"correlated_{dataset_name}_metrics.csv"
    merged.to_csv(merged_path, index=False)
    print(f"Using {sample_count} samples for {dataset_name}.")
    print(f"Merged dataset written to {merged_path}")

    correlation_columns = [column for column in NUMERIC_COLUMNS if column in merged.columns]
    corr = merged[correlation_columns].corr(method="pearson")
    correlation_path = Path("results_csv") / f"correlation_matrix_{dataset_name}.csv"
    corr.to_csv(correlation_path)

    if "CPU" in corr:
        print(f"\n{dataset_name.title()} CPU correlations")
        print(corr["CPU"].sort_values(ascending=False))
    if "Memory" in corr:
        print(f"\n{dataset_name.title()} Memory correlations")
        print(corr["Memory"].sort_values(ascending=False))

    make_chart(merged, dataset_name)


for name, dataset_paths in DATASETS.items():
    process_dataset(name, dataset_paths)
