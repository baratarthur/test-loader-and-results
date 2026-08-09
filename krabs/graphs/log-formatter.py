import sys
import re
import matplotlib.pyplot as plt

if len(sys.argv) < 2:
    print("por favor insira um nome de arquivo")
    sys.exit(1)


log_file_name = sys.argv[1]

print("reading file: ", f'logs/{log_file_name}')

def clear_tag(tag: str) -> str:
    return tag.replace('[', '').replace(']', '')

def separate_tags(log_text: str):
   pattern = r'\[([^\]]+)\]' 
   return list(map(clear_tag, re.findall(pattern, log_text)))

with open(f'logs/{log_file_name}', 'r', encoding='utf-8') as file:
    logs = {
        'adaptations_monolith': [],
        'adaptations_more': [],
        'latency': {}
    }
    current_adaptation = '0'

    for line in file:
        if '@PostsRepository' in line or 'current-latency' in line: continue
        information = list(map(lambda line: line.strip(), line.split('-', 2)))

        timestamp, log_type, log_info = information
        tags = separate_tags(timestamp)
        timestamp_second = int(tags[0]) // 1000

        if 'Server' in log_type:
            if '0' in log_info:
                logs['adaptations_monolith'].append(timestamp_second)
            else:
                logs['adaptations_more'].append(timestamp_second)
                
        elif 'LATENCY' in log_type:
            method, path, latency = log_info.split(' ')
            latency_int = int(latency.replace('ms', '').strip())

            if timestamp_second not in logs['latency']:
                logs['latency'][timestamp_second] = [latency_int]
            else:
                logs['latency'][timestamp_second].append(latency_int)

print("gerando gráfico...")

# 1. Ordena os tempos de latência e prepara as posições sequenciais
tempos_ordenados = sorted(logs['latency'].keys())
dados_latencia = [logs['latency'][t] for t in tempos_ordenados]
posicoes = list(range(1, len(tempos_ordenados) + 1))

plt.figure(figsize=(12, 6))

# 2. Plota os "Pistões" (Boxplots) de forma esparsa
plt.boxplot(dados_latencia, positions=posicoes, widths=0.4, patch_artist=True,
            boxprops=dict(facecolor='lightblue', color='blue'),
            medianprops=dict(color='blue', linewidth=1.5))

# Função auxiliar para calcular a posição das linhas verticais
def calcular_posicao_linha(tempo_adapt):
    if tempo_adapt < tempos_ordenados[0]:
        return 0.5
    elif tempo_adapt > tempos_ordenados[-1]:
        return len(posicoes) + 0.5
    else:
        for i in range(len(tempos_ordenados) - 1):
            if tempos_ordenados[i] <= tempo_adapt <= tempos_ordenados[i+1]:
                t1, t2 = tempos_ordenados[i], tempos_ordenados[i+1]
                p1, p2 = posicoes[i], posicoes[i+1]
                return p1 + (tempo_adapt - t1) / (t2 - t1) * (p2 - p1)
    return 1

# 3. Plota as linhas de Adaptação do Monólito (Verde)
for i, adapt in enumerate(logs['adaptations_monolith']):
    pos_x = calcular_posicao_linha(adapt)
    plt.axvline(x=pos_x, color='green', linestyle='--', linewidth=2, 
                label='Adaptação Monólito' if i == 0 else "")

# 4. Plota as linhas de Adaptação "More" (Roxa)
for i, adapt in enumerate(logs['adaptations_more']):
    pos_x = calcular_posicao_linha(adapt)
    plt.axvline(x=pos_x, color='purple', linestyle='-.', linewidth=2, 
                label='Adaptação More' if i == 0 else "")

# 5. O PULO DO GATO: Remove os valores e marcações do eixo X
plt.xticks([], []) 

# Ajusta os limites laterais para os pistões não colarem nas bordas
plt.xlim(0.5, len(posicoes) + 0.5)

# Configurações de exibição
plt.title("Distribuição de Latência com Múltiplas Adaptações (Eixo X Limpo)")
plt.xlabel("Tempo -> (Evolução do Teste)")
plt.ylabel("Latência (ms)")
plt.grid(True, linestyle=':', alpha=0.5)
plt.legend(loc='upper left')

plt.show()