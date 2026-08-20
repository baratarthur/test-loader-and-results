import re
import json
import pandas as pd

LOG_FILE = "dana.txt"
OUTPUT_CSV = "cache_metrics.csv"

metrics_pattern = re.compile(
    r"\[(\d+)\].*?\[@MetricsStore\]\s*-\s*(\{.*\})"
)
server_pattern = re.compile(
    r"\[(\d+)\].*?\[Server\]\s*-\s*(\{.*\})"
)

rows = {}

with open(LOG_FILE, "r") as f:
    for line in f:
        metrics_match = metrics_pattern.search(line)
        if metrics_match:
            timestamp = int(metrics_match.group(1))
            data = json.loads(metrics_match.group(2))
            row = rows.setdefault(timestamp, {"timestamp": timestamp})
            row.update({
                "cacheHits": int(data["cacheHits"]),
                "cacheMiss": int(data["cacheMiss"]),
                "total_latency": float(data["total_latency"]),
            })
            continue

        server_match = server_pattern.search(line)
        if server_match:
            timestamp = int(server_match.group(1))
            data = json.loads(server_match.group(2))
            row = rows.setdefault(timestamp, {"timestamp": timestamp})
            row["cacheSize"] = int(data.get("cacheSize", 0))

if not rows:
    raise SystemExit("No matching log entries found")

df = pd.DataFrame(rows.values())

df = df.sort_values("timestamp").reset_index(drop=True)

# Ensure every second in the observed range is represented, even if no
# cache metrics were logged for that second.
for col in ["cacheHits", "cacheMiss", "total_latency", "cacheSize"]:
    if col not in df.columns:
        df[col] = pd.NA
    df[col] = pd.to_numeric(df[col], errors="coerce")

if not df.empty:
    df = df.set_index("timestamp")
    start_ts = int(df.index.min())
    end_ts = int(df.index.max())
    df = df.reindex(range(start_ts, end_ts + 1)).ffill().fillna(0)
    df = df.reset_index().rename(columns={"index": "timestamp"})

# Fill missing values with zeros for consistency
for col in ["cacheHits", "cacheMiss", "total_latency", "cacheSize"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

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