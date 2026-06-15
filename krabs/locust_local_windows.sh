#!/bin/bash

# Define a URL base da API
API_URL="http://127.0.0.1:30080"
FILENAME=$1

# 1. Marca o início do teste nos logs da API
echo "[SHELL] Sinalizando início do teste para a API..."
echo curl -s -X GET "${API_URL}/"

# 2. Executa o teste de carga com o Locust (bloqueante até o fim do Shape)
echo "[SHELL] Iniciando o Locust em modo headless..."
locust -f locust.py --headless -H "$API_URL" --csv="results_csv/${FILENAME}"

# 3. Marca o término do teste nos logs da API quando o Locust finalizar
echo "[SHELL] Locust finalizado. Sinalizando término do teste para a API..."
echo curl -s -X GET "${API_URL}/end"

echo "[SHELL] Teste concluído com sucesso!"