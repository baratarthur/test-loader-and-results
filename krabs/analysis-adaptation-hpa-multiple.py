#!/usr/bin/env python3
"""Compara múltiplos arquivos stats_history do Locust no mesmo gráfico (Workload e Latência)."""

import argparse
import datetime
import os

import matplotlib.pyplot as plt
import pandas as pd

# Configurações visuais para diferenciar até 4 experimentos
LINESTYLES = ['-', '--', ':', '-.']
EVENT_COLORS = ['magenta', 'darkcyan', 'darkorange', 'saddlebrown']
LABEL_HEIGHTS = [0.95, 0.83, 0.71, 0.59]  # Alturas diferentes para evitar sobreposição de texto


def parse_args():
    parser = argparse.ArgumentParser(
        description='Compara múltiplos arquivos stats_history do Locust no mesmo gráfico.'
    )
    parser.add_argument(
        '--csv-files',
        nargs='+',
        required=True,
        help='Lista de caminhos para os CSVs separados por espaço. Ex: f1.csv f2.csv f3.csv f4.csv',
    )
    parser.add_argument(
        '--labels',
        nargs='+',
        default=[],
        help='Lista de nomes para cada experimento na legenda. Ex: "Krabs R1" "Krabs R2" "HPA R1" "HPA R2"',
    )
    parser.add_argument(
        '--adaptation-times',
        nargs='*',
        default=[],
        help='Lista de tempos de adaptação entre aspas para cada CSV. Ex: "80,180" "129,240" "" "78,89"',
    )
    parser.add_argument(
        '--output-dir',
        default='results/comparison',
        help='Pasta onde o gráfico comparativo será salvo.',
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
            raise ValueError(f"Tempo inválido: '{item}'. Use valores numéricos em segundos.")
    return elapsed


def load_stats_history(csv_path):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {csv_path}")

    df = pd.read_csv(csv_path, na_values=['N/A'])
    df.columns = df.columns.str.strip()

    if 'Name' in df.columns:
        df = df[df['Name'] == 'Aggregated'].copy()

    if df.empty:
        raise ValueError(f"O CSV '{csv_path}' está vazio ou não contém a linha 'Aggregated'.")

    if 'Timestamp' not in df.columns:
        raise ValueError(f"Coluna Timestamp não encontrada no CSV '{csv_path}'.")

    if pd.api.types.is_numeric_dtype(df['Timestamp']):
        df['Time'] = pd.to_datetime(df['Timestamp'], unit='s', origin='unix', errors='coerce')
    else:
        df['Time'] = pd.to_datetime(df['Timestamp'], errors='coerce')

    if df['Time'].isna().all():
        raise ValueError(f"Não foi possível converter os Timestamps do CSV '{csv_path}'.")

    df = df[df['Time'].notna()].copy()
    df = df.sort_values('Time').reset_index(drop=True)
    df['Elapsed'] = (df['Time'] - df['Time'].iloc[0]).dt.total_seconds()
    return df


def build_adaptation_events(start_time, elapsed_times):
    events = []
    for i, elapsed in enumerate(elapsed_times):
        events.append(
            {
                'name': f'Adaptação {i + 1}',
                'elapsed': elapsed,
                'timestamp': start_time + datetime.timedelta(seconds=elapsed),
            }
        )
    return events


def plot_comparison(experiments_data, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), sharex=True)
    plt.subplots_adjust(hspace=0.25)

    # --- PLOT 1: WORKLOAD & THROUGHPUT ---
    ax1.set_title('Workload e Throughput Comparativo', fontsize=15, fontweight='bold')

    for idx, exp in enumerate(experiments_data):
        df = exp['df']
        label = exp['label']
        linestyle = LINESTYLES[idx % len(LINESTYLES)]

        if 'User Count' in df.columns:
            ax1.plot(
                df['Elapsed'],
                df['User Count'],
                label=f'{label} - Usuários',
                linestyle=linestyle,
                linewidth=1.8,
                alpha=0.85,
            )
        if 'Requests/s' in df.columns:
            ax1.plot(
                df['Elapsed'],
                df['Requests/s'],
                label=f'{label} - Req/s',
                linestyle=linestyle,
                linewidth=1.8,
                alpha=0.85,
            )

    ax1.set_ylabel('Usuários / Req por segundo', fontsize=12)
    ax1.grid(True, linestyle='--', alpha=0.4)
    ax1.legend(loc='upper left', fontsize=9, ncol=2)

    # --- PLOT 2: LATÊNCIA ---
    ax2.set_title('Latência Comparativa (Estilo de Linha = Experimento)', fontsize=15, fontweight='bold')

    percentiles = ['50%', '90%', '95%', '99%']
    colors = {'50%': 'tab:green', '90%': 'tab:purple', '95%': 'tab:orange', '99%': 'tab:red'}

    for idx, exp in enumerate(experiments_data):
        df = exp['df']
        label = exp['label']
        linestyle = LINESTYLES[idx % len(LINESTYLES)]

        for p in percentiles:
            if p in df.columns:
                ax2.plot(
                    df['Elapsed'],
                    df[p],
                    label=f'{p} ({label})',
                    color=colors.get(p, 'black'),
                    linestyle=linestyle,
                    linewidth=1.8,
                    alpha=0.85,
                )

    ax2.set_ylabel('Tempo de resposta (ms)', fontsize=12)
    ax2.set_xlabel('Tempo decorrido (segundos)', fontsize=12)
    ax2.grid(True, linestyle='--', alpha=0.4)
    ax2.legend(loc='upper left', fontsize=8, ncol=len(experiments_data))

    # --- LINHAS DE ADAPTAÇÃO ---
    for idx, exp in enumerate(experiments_data):
        events = exp['events']
        label = exp['label']
        linestyle = LINESTYLES[idx % len(LINESTYLES)]
        color = EVENT_COLORS[idx % len(EVENT_COLORS)]
        height = LABEL_HEIGHTS[idx % len(LABEL_HEIGHTS)]

        for event in events:
            for ax in (ax1, ax2):
                ax.axvline(event['elapsed'], color=color, linestyle=linestyle, linewidth=1.4, alpha=0.75)

            ax2.text(
                event['elapsed'],
                height,
                f"{label}\n{event['name']}",
                transform=ax2.get_xaxis_transform(),
                rotation=90,
                verticalalignment='top',
                horizontalalignment='right',
                color=color,
                fontsize=8,
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.85, edgecolor=color),
            )

    fig.suptitle(
        'Análise Comparativa de Desempenho',
        fontsize=18,
        fontweight='bold',
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    output_png = os.path.join(output_dir, 'comparison_4_analysis.png')
    output_pdf = os.path.join(output_dir, 'comparison_4_analysis.pdf')
    fig.savefig(output_png, dpi=300)
    fig.savefig(output_pdf, dpi=300)
    print(f'Gráfico comparativo salvo em: {output_png}')
    print(f'Gráfico comparativo salvo em: {output_pdf}')


def main():
    args = parse_args()

    num_files = len(args.csv_files)
    if num_files < 2:
        raise ValueError("Forneça pelo menos 2 arquivos CSV para comparação.")

    # Ajusta rótulos e adaptações faltantes
    labels = args.labels
    while len(labels) < num_files:
        labels.append(f'Exp {len(labels) + 1}')

    adaptation_times = args.adaptation_times
    while len(adaptation_times) < num_files:
        adaptation_times.append('')

    experiments_data = []
    for i in range(num_files):
        csv_file = args.csv_files[i]
        label = labels[i]
        times_str = adaptation_times[i]

        df = load_stats_history(csv_file)
        elapsed = parse_elapsed_times(times_str)
        events = build_adaptation_events(df['Time'].iloc[0], elapsed)

        experiments_data.append({
            'df': df,
            'label': label,
            'events': events,
        })

    plot_comparison(experiments_data, args.output_dir)


if __name__ == '__main__':
    main()