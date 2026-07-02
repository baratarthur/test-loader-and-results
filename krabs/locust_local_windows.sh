#!/bin/bash

API_URL="http://127.0.0.1:30080"
FILENAME=$1

START_TIMESTAMP=$(date +%s)

echo "[SHELL] Timestamp de início do teste (Timestamp: ${START_TIMESTAMP})"

echo "[SHELL] Sinalizando início do teste para a API..."
curl -s -X GET "${API_URL}/" | echo

echo "[SHELL] Iniciando o Locust em modo headless..."
locust -f high-latency-locust.py --headless -H "$API_URL" --csv="results_csv/${FILENAME}"

echo "[SHELL] Locust finalizado. Sinalizando término do teste para a API..."
curl -s -X GET "${API_URL}/end" | echo

echo "[SHELL] Teste concluído com sucesso!"