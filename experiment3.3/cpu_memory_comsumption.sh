export POD_NAME=$(kubectl get pod -l app=dana-main -o jsonpath="{.items[0].metadata.name}")
echo "timestamp,CPU,Memory" > metrics.csv
for i in {1..345}; do
    echo "$(date +%s),$(kubectl top pod $POD_NAME --no-headers | awk '{print $2","$3}')" >> metrics.csv
    echo "Measuring second $i"
    sleep 1
done