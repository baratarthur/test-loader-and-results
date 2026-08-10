import re
import json
import pandas as pd

LOG_FILE = "dana.txt"
OUTPUT_CSV = "cache_metrics.csv"

pattern = re.compile(
    r"\[(\d+)\].*?\[@MetricsStore\]\s*-\s*(\{.*\})"
)

records = []

with open(LOG_FILE, "r") as f:
    for line in f:
        m = pattern.search(line)
        if not m:
            continue

        timestamp = int(m.group(1))

        data = json.loads(m.group(2))

        records.append({
            "timestamp": timestamp,
            "cacheHits": int(data["cacheHits"]),
            "cacheMiss": int(data["cacheMiss"]),
            "total_latency": float(data["total_latency"])
        })

df = pd.DataFrame(records)

# Remove duplicate timestamps (keep latest sample each second)
df = df.groupby("timestamp").last().reset_index()

# Per-second increments
df["hits_per_sec"] = df["cacheHits"].diff().fillna(df["cacheHits"])
df["misses_per_sec"] = df["cacheMiss"].diff().fillna(df["cacheMiss"])

# Total accesses during each second
df["requests_per_sec"] = (
    df["hits_per_sec"] +
    df["misses_per_sec"]
)

# Cache hit ratio
df["cache_hit_ratio"] = (
    df["hits_per_sec"] /
    df["requests_per_sec"]
)

df["cache_hit_ratio"] = (
    df["cache_hit_ratio"]
    .fillna(0)
    .clip(0, 1)
)

df.to_csv(OUTPUT_CSV, index=False)

print(df.head())
print(f"Saved {OUTPUT_CSV}")