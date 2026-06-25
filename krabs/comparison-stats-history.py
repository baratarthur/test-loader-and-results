import ast
import os
import pandas as pd
import matplotlib.pyplot as plt

# 1. List of your Locust stats_history.csv files to compare
# Replace these with the actual paths to your files
csv_files = [
    'results_csv/test_max_monolith_behavior_stats_history.csv',
    'results_csv/test_max_distributed_proxy1_behavior_stats_history.csv',
    'results_csv/test_max_distributed_proxy2_behavior_stats_history.csv',
    'results_csv/test_max_distributed_proxy3_behavior_stats_history.csv',
    'results_csv/test_max_distributed_proxy4_behavior_stats_history.csv'
]

locust_file = 'locust.py'


def parse_locust_stages(path):
    """Parse stages from locust.py without importing Locust."""
    if not os.path.exists(path):
        return None

    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()

    tree = ast.parse(source, path)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == 'DynamicBehaviorShape':
            for body_item in node.body:
                if isinstance(body_item, ast.Assign):
                    for target in body_item.targets:
                        if isinstance(target, ast.Name) and target.id == 'stages':
                            try:
                                return ast.literal_eval(body_item.value)
                            except Exception:
                                return None
    return None


def build_user_load_curve(stages):
    """Convert stage definitions into a step curve for planned user load."""
    if not stages:
        return None, None

    times = [0]
    users = [stages[0].get('total_users', 0)]

    for stage in stages:
        duration = stage.get('duration', 0)
        total_users = stage.get('total_users', 0)

        # Locust stage duration here is the cumulative end time for the stage.
        times.append(duration)
        users.append(total_users)

    return times, users


# Create the plot
plt.figure(figsize=(12, 6))

for file_path in csv_files:
    if not os.path.exists(file_path):
        print(f"Warning: File not found: '{file_path}'. Skipping.")
        continue
        
    # Read the CSV file
    df = pd.read_csv(file_path)
    
    # Strip whitespace from column names just in case
    df.columns = df.columns.str.strip()
    
    # 2. Filter for overall test statistics
    # Locust logs each endpoint individually and an 'Aggregated' row for the total
    if 'Name' in df.columns:
        df_filtered = df[df['Name'] == 'Aggregated'].copy()
    else:
        df_filtered = df.copy()
        
    if df_filtered.empty:
        # Fallback to 'Total' if 'Aggregated' isn't used in your Locust version
        df_filtered = df[df['Name'] == 'Total'].copy() if 'Name' in df.columns else df.copy()
    
    if df_filtered.empty:
        print(f"Warning: No aggregated data found in {file_path}. Using raw data.")
        df_filtered = df.copy()

    # Sort chronologically by Timestamp
    df_filtered = df_filtered.sort_values(by='Timestamp')
    
    # 3. Normalize the X-axis to "Elapsed Time" in seconds
    try:
        # Try parsing as UNIX timestamp (numeric)
        timestamps = pd.to_numeric(df_filtered['Timestamp'])
        df_filtered['Elapsed Time (s)'] = timestamps - timestamps.iloc[0]
    except (ValueError, TypeError):
        # Fallback to datetime string parsing if Locust stored it as text
        timestamps = pd.to_datetime(df_filtered['Timestamp'])
        df_filtered['Elapsed Time (s)'] = (timestamps - timestamps.iloc[0]).dt.total_seconds()
    
    # 4. Identify the 99th percentile column (usually named '99%')
    p99_col = None
    for col in ['99%', '99th', 'Percentile 99', '99.0%']:
        if col in df_filtered.columns:
            p99_col = col
            break
            
    if p99_col is None:
        print(f"Error: Could not find 99th percentile column in '{file_path}'. Skipping.")
        continue
        
    # Define a clean label for the legend using the file name
    label_name = os.path.basename(file_path).replace('_stats_history.csv', '')
    
    # 5. Plot the P99 Latency line
    plt.plot(
        df_filtered['Elapsed Time (s)'], 
        df_filtered[p99_col], 
        label=label_name, 
        linewidth=2
    )

# 6. Add Locust user load overlay from locust.py
stages = parse_locust_stages(locust_file)
load_times, load_users = build_user_load_curve(stages)

ax = plt.gca()
if load_times is not None and load_users is not None:
    ax2 = ax.twinx()
    ax2.step(load_times, load_users, where='post', color='gray', linestyle='--', linewidth=2, label='Locust user load')
    ax2.set_ylabel('Active users', fontsize=12, labelpad=10)
    ax2.grid(False)

    # Combine legends from both axes
    handles, labels = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(handles + handles2, labels + labels2, title='Test Runs', fontsize=10, title_fontsize=11, loc='upper left')
else:
    ax.legend(title='Test Runs', fontsize=10, title_fontsize=11, loc='upper left')

# 7. Chart Styling (Titles and Legends in English)
plt.title('Locust Performance Test - 99th Percentile (P99) Latency Comparison', fontsize=14, fontweight='bold', pad=15)
plt.xlabel('Elapsed Time (seconds)', fontsize=12, labelpad=10)
plt.ylabel('P99 Latency (ms)', fontsize=12, labelpad=10)
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()

# 7. Save and display the graph
output_image = 'locust_p99_comparison.png'
plt.savefig(output_image, dpi=300)
print(f"\nGraph successfully generated and saved as '{output_image}'")
plt.show()