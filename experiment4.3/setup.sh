#!/bin/bash

kubectl delete pods -n dana-remote-social-media-app-components dana-remote-social-media-app-0 dana-remote-social-media-app-1 dana-remote-social-media-app-2
source ../krabs/scripts/create-components.sh 0 4 172.29.1.10

wait 10

curl --request POST \
  --url http://127.0.0.1:30080/adapt/2 \
  --header 'Content-Type: application/json' \
  --data '[{"name": "192.168.5.10", "port": 30300}, {"name": "192.168.5.10", "port": 30301}, {"name": "192.168.5.10", "port": 30302}, {"name": "192.168.5.10", "port": 30303}]'

# export POD_NAME=$(kubectl get pod -l app=dana-main -o jsonpath="{.items[0].metadata.name}")
# kubectl logs -f $POD_NAME