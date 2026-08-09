import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def load_requests(path: Path):
    with path.open('r', encoding='utf-8') as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError('O arquivo deve conter uma lista JSON de requisições.')
    return data


from collections import defaultdict
from statistics import mean


def compute_metrics(requests):
    if not requests:
        return {
            'x': [],
            'cache_lookup': [],
            'database_service': [],
            'cache_update': [],
            'wait_cache_lookup': [],
            'wait_database': [],
            'wait_cache_update': [],
            'total_latency': [],
        }

    first_arrival = min(int(request.get('arrivalTime', 0)) for request in requests)
    grouped = defaultdict(list)
    for request in requests:
        arrival = int(request.get('arrivalTime', 0))
        second_bucket = int((arrival - first_arrival) / 1000)
        grouped[second_bucket].append(request)

    x = []
    cache_lookup = []
    database_service = []
    cache_update = []
    wait_cache_lookup = []
    wait_database = []
    wait_cache_update = []
    total_latency = []

    for second in sorted(grouped):
        metrics = []
        for request in grouped[second]:
            arrival = int(request.get('arrivalTime', 0))
            lookup_start = int(request.get('cacheLookupTime', 0))
            lookup_end = int(request.get('cacheLookupEndTime', 0))
            db_conn = int(request.get('databaseConncetionTime', 0))
            db_exec = int(request.get('databaseExecutionTime', 0))
            update_start = int(request.get('cacheUpdateStartTime', 0))
            update_end = int(request.get('cacheUpdateEndTime', 0))
            execution_end = int(request.get('executionEnd', 0))

            metrics.append({
                'cache_lookup': lookup_end - lookup_start if lookup_end != 0 and lookup_start != 0 else -1,
                'database_service': db_exec if db_exec != 0 else -1,
                'cache_update': update_end - update_start if update_end != 0 and update_start != 0 else -1,
                'wait_cache_lookup': lookup_start - arrival if lookup_start != 0 and arrival != 0 else -1,
                'wait_database': db_conn if db_conn != 0 else -1,
                'total_latency': execution_end - arrival,
            })

        x.append(second)
        cache_lookup_data = [m['cache_lookup'] for m in metrics if m['cache_lookup'] != -1]
        cache_lookup.append(mean(cache_lookup_data) if len(cache_lookup_data) > 0 else 0)
        database_service.append(mean(m['database_service'] for m in metrics))
        cache_update_data = [m['cache_update'] for m in metrics if m['cache_update'] != -1]
        cache_update.append(mean(cache_update_data) if len(cache_update_data) > 0 else 0)
        wait_cache_lookup_data = [m['wait_cache_lookup'] for m in metrics if m['wait_cache_lookup'] != -1]
        wait_cache_lookup.append(mean(wait_cache_lookup_data) if len(wait_cache_lookup_data) > 0 else 0)
        wait_database_data = [m['wait_database'] for m in metrics if m['wait_database'] != -1]
        wait_database.append(mean(wait_database_data) if len(wait_database_data) > 0 else 0)
        total_latency.append(mean(m['total_latency'] for m in metrics))

    return {
        'x': x,
        'cache_lookup': cache_lookup,
        'database_service': database_service,
        'cache_update': cache_update,
        'wait_cache_lookup': wait_cache_lookup,
        'wait_database': wait_database,
        'total_latency': total_latency,
    }


def plot_metrics(metrics, output_path: Path | None = None):
    x = metrics['x']
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

    axes[0].plot(x, metrics['cache_lookup'], label='Cache lookup time', linewidth=1.5)
    axes[0].plot(x, metrics['database_service'], label='Database service time', linewidth=1.5)
    axes[0].plot(x, metrics['cache_update'], label='Cache update time', linewidth=1.5)
    axes[0].plot(x, metrics['total_latency'], label='Total latency', linewidth=1.5, linestyle='--')
    axes[0].set_ylabel('Tempo (ms)')
    axes[0].set_title('Tempos de serviço e latência total por arrivalTime (s)')
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].plot(x, metrics['wait_cache_lookup'], label='Waiting before cache lookup', linewidth=1.5)
    axes[1].plot(x, metrics['wait_database'], label='Waiting before database', linewidth=1.5)
    axes[1].set_ylabel('Tempo (ms)')
    axes[1].set_xlabel('Arrival time (s)')
    axes[1].set_title('Tempos de espera entre etapas por arrivalTime (s)')
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=200)
        print(f'Gráfico salvo em: {output_path}')
    plt.show()


def main():
    parser = argparse.ArgumentParser(description='Plota métricas de requisições tratadas.')
    parser.add_argument(
        '--input', '-i',
        default='treated_requests_jet_test_monolith.txt',
        help='Arquivo JSON com os dados de requisição.'
    )
    parser.add_argument(
        '--output', '-o',
        default=None,
        help='Caminho opcional para salvar a imagem do gráfico.'
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f'Arquivo não encontrado: {input_path}')

    requests = load_requests(input_path)
    metrics = compute_metrics(requests)
    plot_metrics(metrics, Path(args.output) if args.output else None)


if __name__ == '__main__':
    main()
