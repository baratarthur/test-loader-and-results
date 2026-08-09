#!/usr/bin/env python3
"""Analysis of Locust statistics history (Workload and Latency) for HPA setup on unified scale."""

import argparse
import datetime
import os

import matplotlib.pyplot as plt
import pandas as pd

DEFAULT_CSV = 'results_csv/edge-adaptation-10ms/round1_stats_history.csv'
DEFAULT_OUTPUT_DIR = 'results/analysis-adaptation'
DEFAULT_ADAPTATION_SECONDS = '80,180,310,322,420,540'


def parse_args():
    parser = argparse.ArgumentParser(
        description='Analyzes a Locust stats_history file for workload and latency.'
    )
    parser.add_argument(
        '--csv-file',
        default=DEFAULT_CSV,
        help='Path to the stats_history CSV file.',
    )
    parser.add_argument(
        '--adaptation-times',
        default=DEFAULT_ADAPTATION_SECONDS,
        help="List of adaptation/event times in seconds separated by commas. Ex: '80,180,310'",
    )
    parser.add_argument(
        '--output-dir',
        default=DEFAULT_OUTPUT_DIR,
        help='Folder where the graph will be saved.',
    )
    return parser.parse_args()


def parse_elapsed_times(value):
    if not value:
        return []
    elapsed = []
    for item in str(value).split(','):
        item = item.strip()
        if not item:
            continue
        time_part = item.split(':')[0] if ':' in item else item
        try:
            elapsed.append(float(time_part))
        except ValueError:
            raise ValueError(f"Invalid time: '{item}'. Use numerical values in seconds.")
    return elapsed


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


def build_adaptation_events(start_time, elapsed_times):
    events = []
    for i, elapsed in enumerate(elapsed_times):
        events.append(
            {
                'name': f'Adaptation {i + 1}',
                'elapsed': elapsed,
                'timestamp': start_time + datetime.timedelta(seconds=elapsed),
            }
        )
    return events


def plot_analysis(df, adaptation_events, output_dir, csv_path):
    os.makedirs(output_dir, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    plt.subplots_adjust(hspace=0.25)

    # --- PLOT 1: WORKLOAD & THROUGHPUT (MESMA ESCALA) ---
    ax1.set_title('Workload and Throughput during the test', fontsize=15, fontweight='bold')
    
    if 'User Count' in df.columns:
        ax1.plot(df['Elapsed'], df['User Count'], label='Active Users', color='tab:blue', linewidth=2)
    if 'Requests/s' in df.columns:
        ax1.plot(df['Elapsed'], df['Requests/s'], label='Requests/s', color='tab:green', linestyle='--', linewidth=1.8)
    if 'Failures/s' in df.columns:
        ax1.plot(df['Elapsed'], df['Failures/s'], label='Failures/s', color='tab:red', linestyle=':', linewidth=1.6)

    ax1.set_ylabel('Users / Requests per second', fontsize=12)
    ax1.grid(True, linestyle='--', alpha=0.4)
    ax1.legend(loc='upper left', fontsize=10)

    # --- PLOT 2: LATENCY ---
    ax2.set_title('Test latency (percentiles)', fontsize=15, fontweight='bold')
    percentile_columns = [col for col in ['50%', '90%', '95%', '99%'] if col in df.columns]

    if not percentile_columns:
        raise ValueError('No percentile columns found for latency plotting.')

    colors = {'50%': 'tab:green', '90%': 'tab:purple', '95%': 'tab:orange', '99%': 'tab:red'}
    for col in percentile_columns:
        ax2.plot(df['Elapsed'], df[col], label=col, color=colors.get(col, 'black'), linewidth=1.8)

    ax2.set_ylabel('Response time (ms)', fontsize=12)
    ax2.set_xlabel('Elapsed time (seconds)', fontsize=12)
    ax2.grid(True, linestyle='--', alpha=0.4)
    ax2.legend(loc='upper left', fontsize=10)

    # --- VERTICAL LINES AND EVENT LABELS ---
    for event in adaptation_events:
        for ax in (ax1, ax2):
            ax.axvline(event['elapsed'], color='magenta', linestyle='--', linewidth=1.5, alpha=0.7)

        label_text = f"{event['name']}\n{event['timestamp'].strftime('%H:%M:%S')}"

        ax2.text(
            event['elapsed'],
            0.95,
            label_text,
            transform=ax2.get_xaxis_transform(),
            rotation=90,
            verticalalignment='top',
            horizontalalignment='right',
            color='magenta',
            fontsize=9,
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.85, edgecolor='magenta'),
        )

    fig.suptitle(
        f'Workload and Latency Analysis - {os.path.basename(csv_path)}',
        fontsize=18,
        fontweight='bold',
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    output_png = os.path.join(output_dir, 'analysis_adaptation.png')
    output_pdf = os.path.join(output_dir, 'analysis_adaptation.pdf')
    fig.savefig(output_png, dpi=300)
    fig.savefig(output_pdf, dpi=300)
    print(f'Graph saved at: {output_png}')
    print(f'Graph saved at: {output_pdf}')


def main():
    args = parse_args()
    elapsed_times = parse_elapsed_times(args.adaptation_times)
    df = load_stats_history(args.csv_file)
    events = build_adaptation_events(df['Time'].iloc[0], elapsed_times)
    plot_analysis(df, events, args.output_dir, args.csv_file)


if __name__ == '__main__':
    main()