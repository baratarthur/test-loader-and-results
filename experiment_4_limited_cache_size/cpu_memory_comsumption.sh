#!/bin/bash

OUTPUT="metrics.csv"

echo "timestamp,dana_cpu,dana_mem,remote_cpu,remote_mem" > "$OUTPUT"

MAIN_NAMESPACE="default"
REMOTE_NAMESPACE="dana-remote-social-media-app-components"

for i in {1..40}; do

    timestamp=$(date +%s)

    # Main service
    read dana_cpu dana_mem <<< $(
        kubectl top pod -n $MAIN_NAMESPACE \
        -l app=dana-main \
        --no-headers | awk '{print $2,$3}'
    )

    # Sum all remote components
    read remote_cpu remote_mem <<< $(
        kubectl top pods -n $REMOTE_NAMESPACE --no-headers |
        awk '
        function cpu(v){
            sub(/m/,"",v)
            return v
        }

        function mem(v){
            if(v~/Gi/){sub(/Gi/,"",v); return v*1024}
            if(v~/Mi/){sub(/Mi/,"",v); return v}
            if(v~/Ki/){sub(/Ki/,"",v); return v/1024}
            return v
        }

        {
            cpu_sum += cpu($2)
            mem_sum += mem($3)
        }

        END{
            print cpu_sum, mem_sum
        }'
    )

    echo "${timestamp},${dana_cpu},${dana_mem},${remote_cpu}m,${remote_mem}Mi" >> "$OUTPUT"

    echo "Collected sample $i"

    sleep 1

done