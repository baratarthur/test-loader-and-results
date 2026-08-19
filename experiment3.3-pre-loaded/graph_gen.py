import pandas as pd
import matplotlib.pyplot as plt

# -------------------------------------------------
# Configuration
# -------------------------------------------------
LOCUST_CSV = "results_csv/dana_stats_history.csv"
RESOURCE_CSV = "results_csv/dana_metrics.csv"
OUTPUT_CSV = "results_csv/correlated_dana_metrics.csv"
CACHE_CSV = "results_csv/cache_metrics.csv"

# -------------------------------------------------
# Load CSVs
# -------------------------------------------------
locust = pd.read_csv(LOCUST_CSV)
resources = pd.read_csv(RESOURCE_CSV)
cache = pd.read_csv(CACHE_CSV)

# -------------------------
# Timestamp
# -------------------------
resources["timestamp"] = pd.to_datetime(
    resources["timestamp"],
    unit="s"
)

cache["timestamp"] = pd.to_datetime(
    cache["timestamp"],
    unit="s"
)

# -------------------------
# CPU (1m -> 1)
# If you prefer cores, divide by 1000.
# -------------------------
resources["CPU"] = (
    resources["CPU"]
    .astype(str)
    .str.replace("m", "", regex=False)
    .astype(float)
)

# Uncomment to convert to CPU cores instead of millicores
# resources["CPU"] = resources["CPU"] / 1000

# -------------------------
# Memory
# Converts Ki, Mi, Gi to MiB
# -------------------------

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

resources["Memory"] = resources["Memory"].apply(convert_memory)

print(resources.head())

# -------------------------------------------------
# Keep only the smallest dataset length
# -------------------------------------------------
n = min(len(locust),
        len(resources),
        len(cache))

locust = locust.iloc[:n].reset_index(drop=True)
resources = resources.iloc[:n].reset_index(drop=True)
cache = cache.iloc[:n].reset_index(drop=True)

print(f"Using {n} samples.")

# -------------------------------------------------
# Merge by sample index
# -------------------------------------------------
merged = locust.copy()

merged["Captured Timestamp"] = resources["timestamp"]
merged["CPU"] = pd.to_numeric(resources["CPU"], errors="coerce")
merged["Memory"] = pd.to_numeric(resources["Memory"], errors="coerce")

# Cache metrics
merged["Cache Hits"] = pd.to_numeric(cache["cacheHits"], errors="coerce")
merged["Cache Misses"] = pd.to_numeric(cache["cacheMiss"], errors="coerce")
merged["Cache Size"] = pd.to_numeric(cache["cacheSize"], errors="coerce")

merged["Cache Hits/s"] = pd.to_numeric(cache["hits_per_sec"], errors="coerce")
merged["Cache Misses/s"] = pd.to_numeric(cache["misses_per_sec"], errors="coerce")
merged["Cache Requests/s"] = pd.to_numeric(cache["requests_per_sec"], errors="coerce")
merged["Cache Hit Ratio"] = pd.to_numeric(cache["cache_hit_ratio"], errors="coerce")
merged["Cache Avg Latency"] = pd.to_numeric(cache["total_latency"], errors="coerce")

# Create an explicit sample index
merged.insert(0, "Sample", range(n))

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
    "CPU",
    "Memory",
    # Cache metrics
    "Cache Hits",
    "Cache Misses",
    "Cache Size",
    "Cache Hits/s",
    "Cache Misses/s",
    "Cache Requests/s",
    "Cache Hit Ratio",
    "Cache Avg Latency",
]

for col in numeric_columns:
    if col in merged.columns:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")

# -------------------------------------------------
# Save merged data
# -------------------------------------------------
merged.to_csv(OUTPUT_CSV, index=False)
print(f"Merged dataset written to {OUTPUT_CSV}")

# -------------------------------------------------
# Correlation matrix
# -------------------------------------------------
corr = merged[numeric_columns].corr(method="pearson")

print("\nCorrelation Matrix")
print(corr.round(3))

corr.to_csv("results_csv/correlation_matrix_dana.csv")

# -------------------------------------------------
# CPU and Memory correlations
# -------------------------------------------------
print("\nCPU correlations")
print(corr["CPU"].sort_values(ascending=False))

print("\nMemory correlations")
print(corr["Memory"].sort_values(ascending=False))

print("\nCache Hit Ratio correlations")
print(corr["Cache Hit Ratio"].sort_values(ascending=False))

print("\nCache Size correlations")
print(corr["Cache Size"].sort_values(ascending=False))

print("\nCache Requests/s correlations")
print(corr["Cache Requests/s"].sort_values(ascending=False))

# -------------------------------------------------
# PLOT
# -------------------------------------------------

# -------------------------------------------------
# BETTER EXPERIMENT PLOT
# -------------------------------------------------

import matplotlib.pyplot as plt
import numpy as np

# -------------------------------------------------
# Configuration
# -------------------------------------------------

FIGURE_PATH = "images/latency_cpu_memory_cache.png"

x = merged["Sample"]

fig, axes = plt.subplots(
    3,
    1,
    figsize=(16, 11),
    sharex=True,
    gridspec_kw={"height_ratios": [1.2, 1, 1]}
)

# =================================================
# 1. SERVICE PERFORMANCE
# =================================================

ax = axes[0]

ax.plot(
    x,
    merged["Total Average Response Time"],
    linewidth=2.5,
    label="Average latency"
)

ax.plot(
    x,
    merged["95%"],
    linestyle="--",
    linewidth=2,
    label="P95 latency"
)

# Users on a secondary axis
ax_users = ax.twinx()

ax_users.plot(
    x,
    merged["User Count"],
    linestyle=":",
    linewidth=2,
    alpha=0.8,
    label="Users"
)

ax.set_ylabel("Latency (ms)")
ax_users.set_ylabel("Users")

ax.set_title(
    "Service Performance",
    loc="left",
    fontweight="bold"
)

ax.grid(
    axis="y",
    alpha=0.3
)

# Combine legends
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax_users.get_legend_handles_labels()

ax.legend(
    lines1 + lines2,
    labels1 + labels2,
    loc="upper left",
    ncol=3
)


# =================================================
# 2. RESOURCE UTILIZATION
# =================================================

ax = axes[1]

ax.plot(
    x,
    merged["CPU"],
    linewidth=2.5,
    label="CPU"
)

ax.set_ylabel("CPU (mCPU)")

# Memory secondary axis
ax_memory = ax.twinx()

ax_memory.plot(
    x,
    merged["Memory"],
    linewidth=2,
    linestyle="--",
    label="Memory"
)

ax_memory.set_ylabel("Memory (MiB)")

ax.set_title(
    "Resource Utilization",
    loc="left",
    fontweight="bold"
)

ax.grid(
    axis="y",
    alpha=0.3
)

lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax_memory.get_legend_handles_labels()

ax.legend(
    lines1 + lines2,
    labels1 + labels2,
    loc="upper left"
)


# =================================================
# 3. CACHE BEHAVIOR
# =================================================

ax = axes[2]

# Cache hit ratio
ax.plot(
    x,
    merged["Cache Hit Ratio"],
    linewidth=2.5,
    label="Cache hit ratio"
)

ax.set_ylabel("Hit ratio")
ax.set_ylim(0, 1.05)

# Cache size + requests/s on secondary axis
ax_cache = ax.twinx()

ax_cache.plot(
    x,
    merged["Cache Requests/s"],
    linestyle=":",
    linewidth=2,
    label="Cache requests/s"
)

ax_cache.set_ylabel(
    "Cache size / requests/s"
)

ax.set_title(
    "Cache Behavior",
    loc="left",
    fontweight="bold"
)

ax.grid(
    axis="y",
    alpha=0.3
)

lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax_cache.get_legend_handles_labels()

ax.legend(
    lines1 + lines2,
    labels1 + labels2,
    loc="upper left"
)


# =================================================
# X AXIS
# =================================================

axes[2].set_xlabel(
    "Experiment sample"
)

# -------------------------------------------------
# Overall title
# -------------------------------------------------

fig.suptitle(
    "Impact of Cache Behavior on Service Performance "
    "and Resource Utilization",
    fontsize=16,
    fontweight="bold",
    y=0.995
)

# -------------------------------------------------
# Layout
# -------------------------------------------------

plt.tight_layout(
    rect=[0, 0, 1, 0.97]
)

plt.savefig(
    FIGURE_PATH,
    dpi=300,
    bbox_inches="tight"
)

plt.show()