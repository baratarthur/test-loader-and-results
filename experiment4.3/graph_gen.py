import pandas as pd
import matplotlib.pyplot as plt

# -------------------------------------------------
# Configuration
# -------------------------------------------------
LOCUST_CSV = "results_csv/dana2_stats_history.csv"
RESOURCE_CSV = "results_csv/dana2_metrics.csv"

OUTPUT_CSV = "results_csv/correlated_dana2_metrics.csv"
CORRELATION_CSV = "results_csv/correlation_matrix_dana2.csv"

PLOT_PATH = "images/dana2_remote_resource_analysis.png"


# -------------------------------------------------
# Load CSVs
# -------------------------------------------------
locust = pd.read_csv(LOCUST_CSV)
resources = pd.read_csv(RESOURCE_CSV)


# -------------------------------------------------
# Timestamp
# -------------------------------------------------
resources["timestamp"] = pd.to_datetime(
    resources["timestamp"],
    unit="s"
)


# -------------------------------------------------
# CPU conversion
#
# Kubernetes examples:
#   100m -> 100 mCPU
#   500m -> 500 mCPU
#   1    -> 1000 mCPU
# -------------------------------------------------

def convert_cpu(value):
    value = str(value).strip()

    if value.endswith("m"):
        return float(value[:-1])

    # Kubernetes CPU expressed in cores
    return float(value) * 1000


cpu_columns = [
    "dana_cpu",
    "remote_cpu"
]

for col in cpu_columns:
    resources[col] = resources[col].apply(convert_cpu)


# -------------------------------------------------
# Memory conversion
#
# Converts:
#   Ki -> MiB
#   Mi -> MiB
#   Gi -> MiB
#   Ti -> MiB
# -------------------------------------------------

def convert_memory(value):
    value = str(value).strip()

    if value.endswith("Ki"):
        return float(value[:-2]) / 1024

    elif value.endswith("Mi"):
        return float(value[:-2])

    elif value.endswith("Gi"):
        return float(value[:-2]) * 1024

    elif value.endswith("Ti"):
        return float(value[:-2]) * 1024 * 1024

    else:
        return float(value)


memory_columns = [
    "dana_mem",
    "remote_mem"
]

for col in memory_columns:
    resources[col] = resources[col].apply(convert_memory)


print("\nResource metrics:")
print(resources.head())


# -------------------------------------------------
# Keep only the smallest dataset length
# -------------------------------------------------
n = min(
    len(locust),
    len(resources)
)

locust = locust.iloc[:n].reset_index(drop=True)
resources = resources.iloc[:n].reset_index(drop=True)

print(f"\nUsing {n} samples.")


# -------------------------------------------------
# Merge by sample index
# -------------------------------------------------
merged = locust.copy()

merged["Captured Timestamp"] = resources["timestamp"]

merged["Dana CPU"] = pd.to_numeric(
    resources["dana_cpu"],
    errors="coerce"
)

merged["Dana Memory"] = pd.to_numeric(
    resources["dana_mem"],
    errors="coerce"
)

merged["Remote CPU"] = pd.to_numeric(
    resources["remote_cpu"],
    errors="coerce"
)

merged["Remote Memory"] = pd.to_numeric(
    resources["remote_mem"],
    errors="coerce"
)


# -------------------------------------------------
# Create sample index
# -------------------------------------------------
merged.insert(
    0,
    "Sample",
    range(n)
)


# -------------------------------------------------
# Create elapsed time
# -------------------------------------------------
merged["Elapsed Time (s)"] = (
    merged["Captured Timestamp"]
    - merged["Captured Timestamp"].iloc[0]
).dt.total_seconds()


# -------------------------------------------------
# Convert Locust numeric columns
# -------------------------------------------------
numeric_columns = [
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
    "Dana CPU",
    "Dana Memory",
    "Remote CPU",
    "Remote Memory",
]

for col in numeric_columns:

    if col in merged.columns:

        merged[col] = pd.to_numeric(
            merged[col],
            errors="coerce"
        )


# -------------------------------------------------
# Save merged data
# -------------------------------------------------
merged.to_csv(
    OUTPUT_CSV,
    index=False
)

print(
    f"\nMerged dataset written to {OUTPUT_CSV}"
)


# =================================================
# CORRELATION MATRIX
# =================================================

corr = merged[numeric_columns].corr(
    method="pearson"
)

print("\nCorrelation Matrix")
print(
    corr.round(3)
)

corr.to_csv(
    CORRELATION_CSV
)


# -------------------------------------------------
# Resource correlations
# -------------------------------------------------

print("\nDana CPU correlations")
print(
    corr["Dana CPU"]
    .sort_values(ascending=False)
)

print("\nDana Memory correlations")
print(
    corr["Dana Memory"]
    .sort_values(ascending=False)
)

print("\nRemote CPU correlations")
print(
    corr["Remote CPU"]
    .sort_values(ascending=False)
)

print("\nRemote Memory correlations")
print(
    corr["Remote Memory"]
    .sort_values(ascending=False)
)


# =================================================
# PLOT
# =================================================

x = merged["Elapsed Time (s)"]


fig, axes = plt.subplots(
    3,
    1,
    figsize=(16, 11),
    sharex=True,
    gridspec_kw={
        "height_ratios": [1.2, 1, 1]
    }
)


# =================================================
# PANEL 1
# SERVICE PERFORMANCE
# =================================================

ax = axes[0]

# Average latency
ax.plot(
    x,
    merged["Total Average Response Time"],
    linewidth=2.5,
    label="Average latency"
)

# P95 latency
ax.plot(
    x,
    merged["95%"],
    linestyle="--",
    linewidth=2,
    label="P95 latency"
)

ax.set_ylabel(
    "Latency (ms)"
)

ax.set_title(
    "Service Performance",
    loc="left",
    fontweight="bold"
)

ax.grid(
    axis="y",
    alpha=0.3
)


# -------------------------------------------------
# Users on secondary axis
# -------------------------------------------------

ax_users = ax.twinx()

ax_users.plot(
    x,
    merged["User Count"],
    linestyle=":",
    linewidth=2,
    alpha=0.8,
    label="Users"
)

ax_users.set_ylabel(
    "Users"
)


# -------------------------------------------------
# Combined legend
# -------------------------------------------------

lines1, labels1 = ax.get_legend_handles_labels()

lines2, labels2 = (
    ax_users.get_legend_handles_labels()
)

ax.legend(
    lines1 + lines2,
    labels1 + labels2,
    loc="upper left",
    ncol=3
)


# =================================================
# PANEL 2
# CPU UTILIZATION
# =================================================

ax = axes[1]

# Dana CPU
ax.plot(
    x,
    merged["Dana CPU"],
    linewidth=2.5,
    label="Dana CPU"
)

# Remote CPU
ax.plot(
    x,
    merged["Remote CPU"],
    linestyle="--",
    linewidth=2.5,
    label="Remote CPU"
)

ax.set_ylabel(
    "CPU (mCPU)"
)

ax.set_title(
    "CPU Utilization",
    loc="left",
    fontweight="bold"
)

ax.grid(
    axis="y",
    alpha=0.3
)

ax.legend(
    loc="upper left"
)


# =================================================
# PANEL 3
# MEMORY UTILIZATION
# =================================================

ax = axes[2]

# Dana memory
ax.plot(
    x,
    merged["Dana Memory"],
    linewidth=2.5,
    label="Dana memory"
)

# Remote memory
ax.plot(
    x,
    merged["Remote Memory"],
    linestyle="--",
    linewidth=2.5,
    label="Remote memory"
)

ax.set_ylabel(
    "Memory (MiB)"
)

ax.set_xlabel(
    "Elapsed time (s)"
)

ax.set_title(
    "Memory Utilization",
    loc="left",
    fontweight="bold"
)

ax.grid(
    axis="y",
    alpha=0.3
)

ax.legend(
    loc="upper left"
)


# =================================================
# OVERALL TITLE
# =================================================

fig.suptitle(
    "Service Performance and Resource Utilization",
    fontsize=16,
    fontweight="bold",
    y=0.995
)


# =================================================
# LAYOUT
# =================================================

plt.tight_layout(
    rect=[0, 0, 1, 0.97]
)


# =================================================
# SAVE FIGURE
# =================================================

plt.savefig(
    PLOT_PATH,
    dpi=300,
    bbox_inches="tight"
)

print(
    f"\nPlot written to {PLOT_PATH}"
)

plt.show()