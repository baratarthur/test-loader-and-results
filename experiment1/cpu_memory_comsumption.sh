while true; do
    echo "$(date +%s),$(kubectl top pod social-network-python-6fdf865897-2tj2f --no-headers | awk '{print $2","$3}')" >> metrics.csv
    sleep 1
done