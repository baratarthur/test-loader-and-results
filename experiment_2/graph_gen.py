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
merged["Cache Hits/s"] = cache["hits_per_sec"]
merged["Cache Misses/s"] = cache["misses_per_sec"]
merged["Cache Hit Ratio"] = cache["cache_hit_ratio"]

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
    "Cache Hits/s",
    "Cache Misses/s",
    "Cache Hit Ratio",
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

# -------------------------------------------------
# PLOT
# -------------------------------------------------

fig, ax1 = plt.subplots(figsize=(16, 8))

# =====================================================
# Left axis - Service latency
# =====================================================
ax1.set_xlabel("Sample", fontsize=20)
ax1.set_ylabel("Latency (ms)", fontsize=20)

ax1.plot(
    merged["Sample"],
    merged["Total Average Response Time"],
    color="black",
    linestyle="-",
    linewidth=2.5,
    label="Avg Response Time"
)

ax1.plot(
    merged["Sample"],
    merged["95%"],
    color="black",
    linestyle="--",
    linewidth=2,
    label="95th Percentile"
)

ax1.tick_params(axis="both", labelsize=18)

# =====================================================
# Right axis - Cache hit ratio
# =====================================================
ax2 = ax1.twinx()

ax2.set_ylabel("Cache Hit Ratio", fontsize=20)
ax2.plot(
    merged["Sample"],
    merged["Cache Hit Ratio"],
    color="black",
    linewidth=2,
    linestyle="-.",
    label="Cache Hit Ratio"
)

ax2.set_ylim(0, 1)
ax2.tick_params(axis="y", labelsize=18)

# =====================================================
# Legend
# =====================================================
lines = ax1.get_lines() + ax2.get_lines()

labels = [line.get_label() for line in lines]

ax1.legend(lines, labels, loc="upper left", fontsize=19, frameon=True)

plt.title("Cache Hit Ratio and Service Response Time", fontsize=24)

ax1.grid(axis="both", linestyle=":", linewidth=0.8, color="gray", alpha=0.7)

plt.tight_layout()

plt.savefig(
    "images/cache_hit_ratio_response_time.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close(fig)
