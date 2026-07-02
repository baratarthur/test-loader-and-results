import ast
import os
import pandas as pd
import matplotlib.pyplot as plt

method = 'fragment-weak'
analysis_folder = 'test_4_components_lesser_logs_10ms_latency'

# 1. List of your Locust stats_history.csv files to compare
csv_files = [
    f'results_csv/{analysis_folder}/close-to-database/{method}_stats_history.csv',
    f'results_csv/{analysis_folder}/close-to-app/{method}_stats_history.csv',
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

    times = [0]
    users = [0]

    for stage in stages:
        duration = stage.get('duration', 0)
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
    
    # Identify the Throughput column
    rps_col = None
    for col in ['Requests/s', 'Current RPS', 'RPS', 'Total Requests/s']:
        if col in df_filtered.columns:
            rps_col = col
            break
            
    if rps_col is None:
        print(f"Error: Could not find Throughput/RPS column in '{file_path}'. Skipping.")
        continue
        
    # Clean label for the legend
    label_name = os.path.basename(file_path).replace('_stats_histlocust_throughput_same_scaleory.csv', '')
    
    # Plot the Throughput (RPS) line on the main axis
    ax.plot(
        df_filtered['Elapsed Time (s)'], 
        df_filtered[rps_col], 
        label=label_name, 
        linewidth=2
    )

# 2. Add Locust user load overlay directly on the MAIN axis (ax)
stages = parse_locust_stages(locust_file)
load_times, load_users = build_user_load_curve(stages)

if load_times is not None and load_users is not None:
    # Plotted directly on 'ax' so it shares the exact same Y scale
    ax.step(
        load_times, 
        load_users, 
        where='pre', 
        color='gray', 
        linestyle='--', 
        linewidth=1.5, 
        label='Locust user load'
    )

# 3. Simplified Legend Handling (Everything is on a single axis now)
ax.legend(title='Test Runs / Metrics', fontsize=10, title_fontsize=11, loc='upper left')

# 4. Chart Styling (Updated Y-label to reflect shared scale)
ax.set_title('Locust Performance Test - Throughput & User Load Comparison', fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel('Elapsed Time (seconds)', fontsize=12, labelpad=10)
ax.set_ylabel('Scale (Requests/s or Active Users)', fontsize=12, labelpad=10)
ax.grid(True, linestyle='--', alpha=0.5)

plt.tight_layout()


# Save and display the graph
output_image = f'results/{analysis_folder}/comparisons/{method}/throughput.pdf'
plt.savefig(output_image, dpi=300)
print(f"\nGraph successfully generated and saved as '{output_image}'")
# plt.show()