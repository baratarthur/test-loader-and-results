#!/bin/bash

# Configurações - Altere aqui com os dados do seu cluster
POD_NAME=$1
OUTPUT_FILE_PATH=$2
NAMESPACE="default" # Mude se o pod estiver em outro namespace

# Verifica se o kubectl está instalado
if ! command -v kubectl &> /dev/null; then
    echo "Erro: kubectl não está instalado ou não foi encontrado no PATH."
    exit 1
fi

echo "Buscando logs do pod '$POD_NAME' e filtrando por [STORE]..."
echo "--------------------------------------------------------"

# Executa o kubectl, filtra com grep e exibe no terminal
kubectl logs "$POD_NAME" -n "$NAMESPACE" | grep '\[STORE\]' > OUTPUT_FILE_PATH