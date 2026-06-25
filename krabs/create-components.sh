#!/bin/bash
set -euo pipefail

OFFSET=${1:-}
AMOUNT=${2:-}
IP=${3:-127.0.0.1}

if [[ -z "$OFFSET" || -z "$AMOUNT" ]]; then
    echo "Usage: $0 <offset> <amount> [ip]"
    exit 1
fi

if ! [[ "$OFFSET" =~ ^[0-9]+$ && "$AMOUNT" =~ ^[0-9]+$ ]]; then
    echo "Error: offset and amount must be non-negative integers"
    exit 1
fi

URL="http://127.0.0.1:30001/create-pod"

for ((i = OFFSET; i < OFFSET + AMOUNT; i++)); do
    echo "Creating component $i"
    PORT=$((30300 + i))
    NAME="dana-remote-social-media-app-$i"
    NAMESPACE="dana-remote-social-media-app-components"
    IMAGE="my.private-registry.lan:5000/dana-remote:latest"

    curl --request POST \
        --url "$URL" \
        --header 'Content-Type: application/json' \
        --data "{\"pod_name\": \"$NAME\", \"namespace\": \"$NAMESPACE\", \"image_name\": \"$IMAGE\", \"app_port\": $PORT}"

    echo "{\"address\": \"$IP\", \"port\": $PORT}"
done
