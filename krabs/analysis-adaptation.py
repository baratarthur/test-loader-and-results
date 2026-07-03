#!/usr/bin/env python3
"""Análise de história de estatísticas do Locust com marcação de momentos de adaptação e componentes."""

import argparse
import datetime
import os

import matplotlib.pyplot as plt
import pandas as pd

DEFAULT_CSV = 'results_csv/edge-adaptation-10ms/round1_stats_history.csv'
DEFAULT_OUTPUT_DIR = 'results/analysis-adaptation'
# Novo padrão aceita tempo:componentes
DEFAULT_ADAPTATION_SECONDS = '80:2,180:0,310:0,322:3,420:2,540:0'


def parse_args():
    parser = argparse.ArgumentParser(
        description='Analisa um arquivo Locust stats_history, marcando adaptações e componentes ativos.'
    )
    parser.add_argument(
        '--csv-file',
        default=DEFAULT_CSV,
        help='Caminho para o arquivo stats_history CSV.',
    )
    parser.add_argument(
        '--adaptation-times',
        default=DEFAULT_ADAPTATION_SECONDS,
        help="Lista de tempos e componentes opcionais separados por vírgula. Ex: '80:2,180:0'",
    )
    parser.add_argument(
        '--output-dir',
        default=DEFAULT_OUTPUT_DIR,
        help='Pasta onde o gráfico será salvo.',
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
                raise ValueError(f"Formato inválido. Use 'tempo:componentes' (ex: 80:2). Erro em: '{item}'")
        else:
            try:
                events_data.append({
                    'elapsed': float(item),
                    'components': None
                })
            except ValueError:
                raise ValueError(f"Tempo inválido: '{item}'. Use número simples ou 'tempo:componentes'.")
    return events_data


def load_stats_history(csv_path):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {csv_path}")

    df = pd.read_csv(csv_path, na_values=['N/A'])
    df.columns = df.columns.str.strip()

    if 'Name' in df.columns:
        df = df[df['Name'] == 'Aggregated'].copy()
    
    if df.empty:
        raise ValueError("O CSV está vazio ou não contém a linha métrica global 'Aggregated'.")

    if 'Timestamp' not in df.columns:
        raise ValueError('Coluna Timestamp não encontrada no CSV.')

    if pd.api.types.is_numeric_dtype(df['Timestamp']):
        df['Time'] = pd.to_datetime(df['Timestamp'], unit='s', origin='unix', errors='coerce')
    else:
        df['Time'] = pd.to_datetime(df['Timestamp'], errors='coerce')

    if df['Time'].isna().all():
        raise ValueError('Não foi possível converter nenhum Timestamp para datetime.')

    df = df[df['Time'].notna()].copy()
    df = df.sort_values('Time').reset_index(drop=True)
    df['Elapsed'] = (df['Time'] - df['Time'].iloc[0]).dt.total_seconds()
    return df


def build_adaptation_events(start_time, parsed_inputs):
    events = []
    for i, data in enumerate(parsed_inputs):
        events.append(
            {
                'name': f'Adaptação {i + 1}',
                'elapsed': data['elapsed'],
                'components': data['components'],
                'timestamp': start_time + datetime.timedelta(seconds=data['elapsed']),
            }
        )
    return events


def plot_analysis(df, adaptation_events, output_dir, csv_path):
    os.makedirs(output_dir, exist_ok=True)

    # Alterado para 3 subplots para abrir espaço exclusivo para os componentes remotos
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 13), sharex=True)
    plt.subplots_adjust(hspace=0.3)

    # --- PLOT 1: WORKLOAD ---
    ax1.set_title('Workload durante o teste', fontsize=15, fontweight='bold')
    if 'User Count' in df.columns:
        ax1.plot(df['Elapsed'], df['User Count'], label='User Count', color='tab:blue', linewidth=2)
    ax1.set_ylabel('Usuários ativos', color='tab:blue', fontsize=12)
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    ax1.grid(True, linestyle='--', alpha=0.4)

    ax1b = ax1.twinx()
    if 'Requests/s' in df.columns:
        ax1b.plot(df['Elapsed'], df['Requests/s'], label='Requests/s', color='tab:green', linestyle='--', linewidth=1.8)
    if 'Failures/s' in df.columns:
        ax1b.plot(df['Elapsed'], df['Failures/s'], label='Failures/s', color='tab:red', linestyle=':', linewidth=1.6)
    ax1b.set_ylabel('Requests/s / Failures/s', color='tab:green', fontsize=12)
    ax1b.tick_params(axis='y', labelcolor='tab:green')
    
    handles, labels = ax1.get_legend_handles_labels()
    handles_b, labels_b = ax1b.get_legend_handles_labels()
    ax1.legend(handles + handles_b, labels + labels_b, loc='upper left', fontsize=10)

    # --- PLOT 2: COMPONENTES REMOTOS (Novo!) ---
    ax2.set_title('Uso de Componentes Remotos', fontsize=15, fontweight='bold')
    
    has_components = any(e['components'] is not None for e in adaptation_events)
    if has_components:
        # Monta a linha do tempo em degraus do estado dos componentes
        step_x = [0.0]
        step_y = [0] # Assume 0 no início do teste
        
        for e in sorted(adaptation_events, key=lambda x: x['elapsed']):
            if e['components'] is not None:
                step_x.append(e['elapsed'])
                step_y.append(e['components'])
        
        step_x.append(df['Elapsed'].max())
        step_y.append(step_y[-1])
        
        ax2.step(step_x, step_y, where='post', color='tab:orange', linewidth=2.5, label='Componentes Ativos')
        ax2.set_yticks(range(0, int(max(step_y)) + 2))
    else:
        ax2.text(0.5, 0.5, "Nenhum dado de componente fornecido\nUse o formato tempo:componentes", 
                 ha='center', va='center', transform=ax2.transAxes, color='gray')
        
    ax2.set_ylabel('Qtd. Componentes', fontsize=12)
    ax2.grid(True, linestyle='--', alpha=0.4)
    ax2.legend(loc='upper left', fontsize=10)

    # --- PLOT 3: LATÊNCIA ---
    ax3.set_title('Latência do teste (percentis)', fontsize=15, fontweight='bold')
    percentile_columns = [col for col in ['50%', '90%', '95%', '99%'] if col in df.columns]
    
    if not percentile_columns:
        raise ValueError('Nenhuma coluna de percentil encontrada para plotagem de latência.')

    colors = {'50%': 'tab:green', '90%': 'tab:purple', '95%': 'tab:orange', '99%': 'tab:red'}
    for col in percentile_columns:
        ax3.plot(df['Elapsed'], df[col], label=col, color=colors.get(col, 'black'), linewidth=1.8)
    
    ax3.set_ylabel('Tempo de resposta (ms)', fontsize=12)
    ax3.set_xlabel('Tempo decorrido (segundos)', fontsize=12)
    ax3.grid(True, linestyle='--', alpha=0.4)
    ax3.legend(loc='upper left', fontsize=10)

    # --- LINHAS VERTICAIS E LABELS DE EVENTOS ---
    for event in adaptation_events:
        for ax in (ax1, ax2, ax3):
            ax.axvline(event['elapsed'], color='magenta', linestyle='--', linewidth=1.5, alpha=0.7)
        
        # Constrói o texto da label (inclui os componentes se existirem)
        label_text = f"{event['name']}"
        if event['components'] is not None:
            label_text += f" ({event['components']} comp.)"
        label_text += f"\n{event['timestamp'].strftime('%H:%M:%S')}"

        # Plota o texto ancorado no topo do gráfico inferior (ax3)
        ax3.text(
            event['elapsed'],
            0.95,  
            label_text,
            transform=ax3.get_xaxis_transform(),
            rotation=90,
            verticalalignment='top',
            horizontalalignment='right',
            color='magenta',
            fontsize=9,
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.85, edgecolor='magenta'),
        )

    fig.suptitle(
        f'Análise de workload, Componentes e Adaptação - {os.path.basename(csv_path)}',
        fontsize=18,
        fontweight='bold',
        y=0.98,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    output_png = os.path.join(output_dir, 'analysis_adaptation.png')
    output_pdf = os.path.join(output_dir, 'analysis_adaptation.pdf')
    fig.savefig(output_png, dpi=300)
    fig.savefig(output_pdf, dpi=300)
    print(f'Gráfico salvo em: {output_png}')
    print(f'Gráfico salvo em: {output_pdf}')


def main():
    args = parse_args()
    parsed_inputs = parse_adaptation_inputs(args.adaptation_times)
    df = load_stats_history(args.csv_file)
    events = build_adaptation_events(df['Time'].iloc[0], parsed_inputs)
    plot_analysis(df, events, args.output_dir, args.csv_file)


if __name__ == '__main__':
    main()