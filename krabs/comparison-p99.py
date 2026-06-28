import ast
import os
import pandas as pd
import matplotlib.pyplot as plt

# 1. List of your Locust stats_history.csv files to compare
csv_files = [
    'results_csv/test_12_components_less_logs/max_monolith_stats_history.csv',
    'results_csv/test_12_components_less_logs/max_proxy_replicate_strong_stats_history.csv',
    'results_csv/test_12_components_less_logs/max_proxy_replicate_weak_stats_history.csv',
    'results_csv/test_12_components_less_logs/max_proxy_fragment_strong_stats_history.csv',
    'results_csv/test_12_components_less_logs/max_proxy_fragment_weak_stats_history.csv'
]

locust_file = 'locust.py'


def parse_locust_stages(path):
    """Parse stages from locust.py without importing Locust."""
    if not os.path.exists(path):
        return None

    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        tree = ast.parse(source, path)
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == 'DynamicBehaviorShape':
                for body_item in node.body:
                    if isinstance(body_item, ast.Assign):
                        for target in body_item.targets:
                            if isinstance(target, ast.Name) and target.id == 'stages':
                                return ast.literal_eval(body_item.value)
    except Exception as e:
        print(f"Warning: Could not parse AST from {path}: {e}")
        return None
    return None


def build_user_load_curve(stages):
    """Convert stage definitions into a step curve for planned user load."""
    if not stages:
        return None, None

    # Start at 0 users at time 0
    times = [0]
    users = [0]

    for stage in stages:
        duration = stage.get('duration', 0)
        # Fallback support for both 'total_users' and standard 'users' key
        total_users = stage.get('total_users', stage.get('users', 0))

        times.append(duration)
        users.append(total_users)

    return times, users


# Initialize the plot and get the main axis (ax)
fig, ax = plt.subplots(figsize=(12, 6))

for file_path in csv_files:
    if not os.path.exists(file_path):
        print(f"Warning: File not found: '{file_path}'. Skipping.")
        continue
        
    # Read the CSV file
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()
    
    # Filter for overall test statistics
    if 'Name' in df.columns:
        df_filtered = df[df['Name'] == 'Aggregated'].copy()
    else:
        df_filtered = df.copy()
        
    if df_filtered.empty:
        df_filtered = df[df['Name'] == 'Total'].copy() if 'Name' in df.columns else df.copy()
    
    if df_filtered.empty:
        print(f"Warning: No aggregated data found in {file_path}. Using raw data.")
        df_filtered = df.copy()

    # Sort chronologically by Timestamp
    df_filtered = df_filtered.sort_values(by='Timestamp')
    
    # Normalize the X-axis to "Elapsed Time" in seconds
    try:
        timestamps = pd.to_numeric(df_filtered['Timestamp'])
        df_filtered['Elapsed Time (s)'] = timestamps - timestamps.iloc[0]
    except (ValueError, TypeError):
        timestamps = pd.to_datetime(df_filtered['Timestamp'])
        df_filtered['Elapsed Time (s)'] = (timestamps - timestamps.iloc[0]).dt.total_seconds()
    
    # Identify the 99th percentile column
    p99_col = None
    for col in ['99%', '99th', 'Percentile 99', '99.0%']:
        if col in df_filtered.columns:
            p99_col = col
            break
            
    if p99_col is None:
        print(f"Error: Could not find 99th percentile column in '{file_path}'. Skipping.")
        continue
        
    # Clean label for the legend
    label_name = os.path.basename(file_path).replace('_stats_history.csv', '')
    
    # Plot the P99 Latency line on the main axis
    ax.plot(
        df_filtered['Elapsed Time (s)'], 
        df_filtered[p99_col], 
        label=label_name, 
        linewidth=2
    )

# Add Locust user load overlay from locust.py
stages = parse_locust_stages(locust_file)
load_times, load_users = build_user_load_curve(stages)

if load_times is not None and load_users is not None:
    ax2 = ax.twinx()
    # Using where='pre' ensures the user count applies to the duration leading up to the timestamp
    ax2.step(load_times, load_users, where='pre', color='gray', linestyle='--', linewidth=1.5, label='Locust user load')
    ax2.set_ylabel('Active Users', fontsize=12, labelpad=10)
    ax2.grid(False)

    # Combine legends from both axes safely
    handles, labels = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_get_legend_handles_labels() if hasattr(ax2, 'get_get_legend_handles_labels') else ax2.get_legend_handles_labels()
    ax.legend(handles + handles2, labels + labels2, title='Test Runs / Metrics', fontsize=10, title_fontsize=11, loc='upper left')
else:
    ax.legend(title='Test Runs', fontsize=10, title_fontsize=11, loc='upper left')

# Explicit Chart Styling using the correct Axis object (Fixes the Bug)
ax.set_title('Locust Performance Test - 99th Percentile (P99) Latency Comparison', fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel('Elapsed Time (seconds)', fontsize=12, labelpad=10)
ax.set_ylabel('P99 Latency (ms)', fontsize=12, labelpad=10)
ax.grid(True, linestyle='--', alpha=0.5)

plt.tight_layout()

# Save and display the graph
output_image = 'locust_p99_comparison.png'
plt.savefig(output_image, dpi=300)
print(f"\nGraph successfully generated and saved as '{output_image}'")
plt.show()