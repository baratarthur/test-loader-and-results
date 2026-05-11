import pandas as pd
import matplotlib.pyplot as plt
import datetime

# 1. Carregar os dados
# Substitua 'seu_arquivo_stats_history.csv' pelo nome do seu arquivo
file_path = 'locust_test_limited_monolith_stats_history.csv'

# Lendo o CSV e tratando valores 'N/A' como NaN
df = pd.read_csv(file_path, na_values=['N/A'])
df = df.fillna(0)

# 2. Pré-processamento
# Converter Timestamp Unix para formato de hora legível
df['Time'] = df['Timestamp'].apply(lambda x: datetime.datetime.fromtimestamp(x))
# Normalizar o tempo para começar em 0 segundos
start_time = df['Time'].min()
df['Elapsed'] = (df['Time'] - start_time).dt.total_seconds()

# 3. Criar a visualização
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 15), sharex=True)
plt.subplots_adjust(hspace=0.3)

# --- Gráfico 1: Usuários e Throughput (RPS) ---
ax1.set_title('Carga vs Throughput', fontsize=14, fontweight='bold')
ax1.plot(df['Elapsed'], df['User Count'], color='tab:blue', label='User Count', linewidth=2)
ax1.set_ylabel('Users', color='tab:blue', fontsize=12)
ax1.tick_params(axis='y', labelcolor='tab:blue')

ax1_2 = ax1.twinx()
ax1_2.plot(df['Elapsed'], df['Requests/s'], color='tab:green', label='Requests/s', linestyle='--')
ax1_2.set_ylabel('Requests/s', color='tab:green', fontsize=12)
ax1_2.tick_params(axis='y', labelcolor='tab:green')
ax1.grid(True, which='both', linestyle='--', alpha=0.5)

# --- Gráfico 2: Tempos de Resposta (Percentis) ---
ax2.set_title('Latência (Percentis)', fontsize=14, fontweight='bold')
ax2.plot(df['Elapsed'], df['50%'], label='Mediana (50%)', color='green')
ax2.plot(df['Elapsed'], df['95%'], label='P95', color='orange')
ax2.plot(df['Elapsed'], df['99%'], label='P99', color='red')
ax2.set_ylabel('Response Time (ms)', fontsize=12)
ax2.legend(loc='upper left')
ax2.grid(True, linestyle='--', alpha=0.5)

# --- Gráfico 3: Falhas por Segundo ---
ax3.set_title('Falhas por Segundo', fontsize=14, fontweight='bold')
ax3.fill_between(df['Elapsed'], df['Failures/s'], color='tab:red', alpha=0.3)
ax3.plot(df['Elapsed'], df['Failures/s'], color='tab:red', label='Failures/s')
ax3.set_ylabel('Failures/s', fontsize=12)
ax3.set_xlabel('Tempo decorrido (segundos)', fontsize=12)
ax3.grid(True, linestyle='--', alpha=0.5)

# Finalizar e salvar
plt.tight_layout()
output_filename = 'resultado_teste_locust.png'
plt.savefig(output_filename, dpi=300)
print(f"Gráfico gerado com sucesso: {output_filename}")
plt.show()