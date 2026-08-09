while true; do
    echo "$(date +%s),$(kubectl top pod my-pod --no-headers | awk '{print $2","$3}')" >> metrics.csv
    sleep 1
done