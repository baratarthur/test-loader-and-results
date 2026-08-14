#!/bin/bash

kubectl delete pods -n dana-remote-social-media-app-components dana-remote-social-media-app-0
source ../krabs/scripts/create-components.sh 0 1 172.29.1.10

wait 10

curl --request POST \
  --url http://127.0.0.1:30080/adapt/3 \
  --header 'Content-Type: application/json' \
  --data '[{"name": "192.168.5.10", "port": 30300}]'

# export POD_NAME=$(kubectl get pod -l app=dana-main -o jsonpath="{.items[0].metadata.name}")
# kubectl logs -f $POD_NAME