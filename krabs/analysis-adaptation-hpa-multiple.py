#!/usr/bin/env python3
"""Compara dois arquivos stats_history do Locust no mesmo gráfico (Workload e Latência)."""

import argparse
import datetime
import os

import matplotlib.pyplot as plt
import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser(
        description='Compara dois arquivos stats_history do Locust no mesmo gráfico.'
    )
    # Argumentos do primeiro CSV
    parser.add_argument(
        '--csv-file1',
        required=True,
        help='Caminho para o primeiro arquivo CSV (ex: Krabs).',
    )
    parser.add_argument(
        '--label1',
        default='Experimento 1',
        help='Rótulo/Nome do primeiro experimento no gráfico.',
    )
    parser.add_argument(
        '--adaptation-times1',
        default='',
        help="Tempos de adaptação para o CSV 1 em segundos. Ex: '78,89,197,207'",
    )

    # Argumentos do segundo CSV
    parser.add_argument(
        '--csv-file2',
        required=True,
        help='Caminho para o segundo arquivo CSV (ex: HPA).',
    )
    parser.add_argument(
        '--label2',
        default='Experimento 2',
        help='Rótulo/Nome do segundo experimento no gráfico.',
    )
    parser.add_argument(
        '--adaptation-times2',
        default='',
        help="Tempos de adaptação para o CSV 2 em segundos. Ex: '120,240'",
    )

    # Saída
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


def plot_comparison(df1, events1, label1, df2, events2, label2, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 11), sharex=True)
    plt.subplots_adjust(hspace=0.25)

    # --- PLOT 1: WORKLOAD & THROUGHPUT ---
    ax1.set_title(f'Workload e Throughput: {label1} vs {label2}', fontsize=15, fontweight='bold')

    # Experimento 1 (Linhas Sólidas)
    if 'User Count' in df1.columns:
        ax1.plot(df1['Elapsed'], df1['User Count'], label=f'{label1} - Usuários', color='tab:blue', linestyle='-', linewidth=2)
    if 'Requests/s' in df1.columns:
        ax1.plot(df1['Elapsed'], df1['Requests/s'], label=f'{label1} - Req/s', color='tab:green', linestyle='-', linewidth=1.8)

    # Experimento 2 (Linhas Tracejadas)
    if 'User Count' in df2.columns:
        ax1.plot(df2['Elapsed'], df2['User Count'], label=f'{label2} - Usuários', color='tab:cyan', linestyle='--', linewidth=1.8, alpha=0.8)
    if 'Requests/s' in df2.columns:
        ax1.plot(df2['Elapsed'], df2['Requests/s'], label=f'{label2} - Req/s', color='tab:olive', linestyle='--', linewidth=1.8)

    ax1.set_ylabel('Usuários / Req por segundo', fontsize=12)
    ax1.grid(True, linestyle='--', alpha=0.4)
    ax1.legend(loc='upper left', fontsize=10, ncol=2)

    # --- PLOT 2: LATÊNCIA ---
    ax2.set_title(f'Latência (Sólido = {label1} | Tracejado = {label2})', fontsize=15, fontweight='bold')

    percentiles = ['50%', '90%', '95%', '99%']
    colors = {'50%': 'tab:green', '90%': 'tab:purple', '95%': 'tab:orange', '99%': 'tab:red'}

    # Plot Experimento 1 (Sólido)
    for p in percentiles:
        if p in df1.columns:
            ax2.plot(df1['Elapsed'], df1[p], label=f'{p} ({label1})', color=colors.get(p, 'black'), linestyle='-', linewidth=2)

    # Plot Experimento 2 (Tracejado)
    for p in percentiles:
        if p in df2.columns:
            ax2.plot(df2['Elapsed'], df2[p], label=f'{p} ({label2})', color=colors.get(p, 'black'), linestyle='--', linewidth=1.8, alpha=0.85)

    ax2.set_ylabel('Tempo de resposta (ms)', fontsize=12)
    ax2.set_xlabel('Tempo decorrido (segundos)', fontsize=12)
    ax2.grid(True, linestyle='--', alpha=0.4)
    ax2.legend(loc='upper left', fontsize=9, ncol=2)

    # --- LINHAS DE ADAPTAÇÃO ---
    # Eventos do Exp 1 (Linhas Magenta)
    for event in events1:
        for ax in (ax1, ax2):
            ax.axvline(event['elapsed'], color='magenta', linestyle='--', linewidth=1.5, alpha=0.7)
        ax2.text(
            event['elapsed'],
            0.95,
            f"{label1}\n{event['name']}",
            transform=ax2.get_xaxis_transform(),
            rotation=90,
            verticalalignment='top',
            horizontalalignment='right',
            color='magenta',
            fontsize=8,
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8, edgecolor='magenta'),
        )

    # Eventos do Exp 2 (Linhas Cyan Escuro)
    for event in events2:
        for ax in (ax1, ax2):
            ax.axvline(event['elapsed'], color='darkcyan', linestyle=':', linewidth=1.5, alpha=0.8)
        ax2.text(
            event['elapsed'],
            0.80, # Altura ligeiramente menor para não sobrepor rótulos se os tempos forem parecidos
            f"{label2}\n{event['name']}",
            transform=ax2.get_xaxis_transform(),
            rotation=90,
            verticalalignment='top',
            horizontalalignment='right',
            color='darkcyan',
            fontsize=8,
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8, edgecolor='darkcyan'),
        )

    fig.suptitle(
        f'Análise Comparativa de Desempenho: {label1} vs {label2}',
        fontsize=18,
        fontweight='bold',
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    output_png = os.path.join(output_dir, 'comparison_analysis.png')
    output_pdf = os.path.join(output_dir, 'comparison_analysis.pdf')
    fig.savefig(output_png, dpi=300)
    fig.savefig(output_pdf, dpi=300)
    print(f'Gráfico comparativo salvo em: {output_png}')
    print(f'Gráfico comparativo salvo em: {output_pdf}')


def main():
    args = parse_args()

    df1 = load_stats_history(args.csv_file1)
    elapsed1 = parse_elapsed_times(args.adaptation_times1)
    events1 = build_adaptation_events(df1['Time'].iloc[0], elapsed1)

    df2 = load_stats_history(args.csv_file2)
    elapsed2 = parse_elapsed_times(args.adaptation_times2)
    events2 = build_adaptation_events(df2['Time'].iloc[0], elapsed2)

    plot_comparison(df1, events1, args.label1, df2, events2, args.label2, args.output_dir)


if __name__ == '__main__':
    main()