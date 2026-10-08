#!/usr/bin/env python3
"""Analysis of Locust statistics history with adaptation moments and components marking."""

import argparse
import datetime
import os

import matplotlib.pyplot as plt
import pandas as pd

DEFAULT_CSV = 'results_csv/edge-adaptation-10ms/round1_stats_history.csv'
DEFAULT_OUTPUT_DIR = 'images/analysis-adaptation/round1'
# New pattern accepts time:components
DEFAULT_ADAPTATION_SECONDS = '80:2,180:0,310:0,322:3,420:2,540:0'

plt.rcParams.update({
    'font.size': 18,
    'axes.titlesize': 23,
    'axes.labelsize': 21,
    'xtick.labelsize': 18,
    'ytick.labelsize': 18,
    'legend.fontsize': 17,
})


def parse_args():
    parser = argparse.ArgumentParser(
        description='Analyzes a Locust stats_history file, marking adaptations and active components.'
    )
    parser.add_argument(
        '--csv-file',
        default=DEFAULT_CSV,
        help='Path to the stats_history CSV file.',
    )
    parser.add_argument(
        '--adaptation-times',
        default=DEFAULT_ADAPTATION_SECONDS,
        help="List of times and optional components separated by commas. Ex: '80:2,180:0'",
    )
    parser.add_argument(
        '--output-dir',
        default=DEFAULT_OUTPUT_DIR,
        help='Folder where the graph will be saved.',
    )
    return parser.parse_args()


def parse_adaptation_inputs(value):
    if not value:
        return []
    events_data = []
    for item in str(value).split(','):
        item = item.strip()
        if not item:
            continue
        
        if ':' in item:
            try:
                time_part, comp_part = item.split(':')
                events_data.append({
                    'elapsed': float(time_part.strip()),
                    'components': int(comp_part.strip())
                })
            except ValueError:
                raise ValueError(f"Invalid format. Use 'time:components' (ex: 80:2). Error in: '{item}'")
        else:
            try:
                events_data.append({
                    'elapsed': float(item),
                    'components': None
                })
            except ValueError:
                raise ValueError(f"Invalid time: '{item}'. Use simple number or 'time:components'.")
    return events_data


def load_stats_history(csv_path):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File not found: {csv_path}")

    df = pd.read_csv(csv_path, na_values=['N/A'])
    df.columns = df.columns.str.strip()

    if 'Name' in df.columns:
        df = df[df['Name'] == 'Aggregated'].copy()
    
    if df.empty:
        raise ValueError("The CSV is empty or does not contain the 'Aggregated' global metric line.")

    if 'Timestamp' not in df.columns:
        raise ValueError('Timestamp column not found in CSV.')

    if pd.api.types.is_numeric_dtype(df['Timestamp']):
        df['Time'] = pd.to_datetime(df['Timestamp'], unit='s', origin='unix', errors='coerce')
    else:
        df['Time'] = pd.to_datetime(df['Timestamp'], errors='coerce')

    if df['Time'].isna().all():
        raise ValueError('Unable to convert any Timestamp to datetime.')

    df = df[df['Time'].notna()].copy()
    df = df.sort_values('Time').reset_index(drop=True)
    df['Elapsed'] = (df['Time'] - df['Time'].iloc[0]).dt.total_seconds()
    return df


def build_adaptation_events(start_time, parsed_inputs):
    events = []
    for i, data in enumerate(parsed_inputs):
        events.append(
            {
                'name': f'Adaptation {i + 1}',
                'elapsed': data['elapsed'],
                'components': data['components'],
                'timestamp': start_time + datetime.timedelta(seconds=data['elapsed']),
            }
        )
    return events


def plot_analysis(df, adaptation_events, output_dir, csv_path):
    os.makedirs(output_dir, exist_ok=True)

    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=(20, 18), sharex=True,
        gridspec_kw={'height_ratios': [1.1, 0.8, 1.4]},
    )

    # Workload and request rates use line patterns so the plot remains readable in grayscale.
    ax1.set_title('Workload and request throughput', fontweight='bold')
    if 'User Count' in df.columns:
        user_count = pd.to_numeric(df['User Count'], errors='coerce')
        ax1.plot(df['Elapsed'], user_count, label='Active users', color='black', linewidth=3.0)
        ax1.set_ylim(bottom=0, top=max(user_count.max(), 1) * 1.25)
    ax1.set_ylabel('Active users')
    ax1.grid(True, linestyle=':', linewidth=0.8, alpha=0.7)

    ax1b = ax1.twinx()
    if 'Requests/s' in df.columns:
        requests_per_second = pd.to_numeric(df['Requests/s'], errors='coerce')
        ax1b.plot(df['Elapsed'], requests_per_second, label='Requests/s', color='black', linestyle='--', linewidth=2.8)
        ax1b.set_ylim(bottom=0, top=max(requests_per_second.max(), 1) * 1.25)
    ax1b.set_ylabel('Requests/s')
    handles, labels = ax1.get_legend_handles_labels()
    handles_b, labels_b = ax1b.get_legend_handles_labels()
    ax1.legend(handles + handles_b, labels + labels_b, loc='upper left', ncol=2, frameon=True)

    ax2.set_title('Application components', fontweight='bold')
    component_events = [e for e in sorted(adaptation_events, key=lambda item: item['elapsed']) if e['components'] is not None]
    if component_events:
        step_x = [0.0] + [event['elapsed'] for event in component_events] + [df['Elapsed'].max()]
        step_y = [0] + [event['components'] for event in component_events]
        step_y.append(step_y[-1])
        ax2.step(step_x, step_y, where='post', color='black', linewidth=3.2, label='Active components')
        ax2.set_yticks(range(0, int(max(step_y)) + 1))
        ax2.set_ylim(bottom=0, top=max(step_y) + 1)
        ax2.legend(loc='upper left', frameon=True)
    else:
        ax2.text(0.5, 0.5, 'No component counts were provided', ha='center', va='center', transform=ax2.transAxes)
    ax2.set_ylabel('Number of components')
    ax2.grid(True, linestyle=':', linewidth=0.8, alpha=0.7)

    ax3.set_title('Latency percentiles', fontweight='bold')
    percentile_styles = {'50%': '-', '90%': '--', '95%': '-.', '99%': ':'}
    percentile_columns = [col for col in percentile_styles if col in df.columns]
    if not percentile_columns:
        raise ValueError('No percentile columns found for latency plotting.')
    for col in percentile_columns:
        ax3.plot(df['Elapsed'], pd.to_numeric(df[col], errors='coerce'), label=col, color='black', linestyle=percentile_styles[col], linewidth=2.8)
    max_latency = max(pd.to_numeric(df[col], errors='coerce').max() for col in percentile_columns)
    ax3.set_ylim(bottom=0, top=max_latency * 1.25)
    ax3.set_ylabel('Response time (ms)')
    ax3.set_xlabel('Elapsed time (seconds)')
    ax3.grid(True, linestyle=':', linewidth=0.8, alpha=0.7)
    ax3.legend(loc='upper left', ncol=4, frameon=True)

    for event in adaptation_events:
        for ax in (ax1, ax2, ax3):
            ax.axvline(event['elapsed'], color='0.35', linestyle='--', linewidth=1.5, alpha=0.85)

    event_summary = '   |   '.join(
        f"A{i}: {event['elapsed']:g} s" + (f", {event['components']} comp." if event['components'] is not None else '')
        for i, event in enumerate(sorted(adaptation_events, key=lambda item: item['elapsed']), start=1)
    )
    round_name = os.path.basename(csv_path).replace('_stats_history.csv', '')
    fig.suptitle(f'KRABS application adaptation — {round_name}', fontsize=25, fontweight='bold', y=0.985)
    fig.text(0.5, 0.956, f'Adaptation events: {event_summary}', ha='center', va='top', fontsize=16)
    for ax in (ax1, ax1b, ax2, ax3):
        ax.tick_params(axis='both', labelsize=18)
    fig.subplots_adjust(top=0.87, bottom=0.10, hspace=0.31)

    output_png = os.path.join(output_dir, 'analysis_adaptation.png')
    output_pdf = os.path.join(output_dir, 'analysis_adaptation.pdf')
    fig.savefig(output_png, dpi=300)
    fig.savefig(output_pdf, dpi=300)
    print(f'Graph saved at: {output_png}')
    print(f'Graph saved at: {output_pdf}')


def main():
    args = parse_args()
    parsed_inputs = parse_adaptation_inputs(args.adaptation_times)
    df = load_stats_history(args.csv_file)
    events = build_adaptation_events(df['Time'].iloc[0], parsed_inputs)
    plot_analysis(df, events, args.output_dir, args.csv_file)


if __name__ == '__main__':
    main()
