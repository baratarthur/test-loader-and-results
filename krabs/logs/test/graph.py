import json

post_repository_tag = '[@PostsRepository]'

thread_data = []

with open('thread_logs.txt', 'r') as file:
    logs = file.readlines()
    for line in logs:
        if post_repository_tag in line:
            json_data = line.split('-')[1].strip().replace(post_repository_tag, '')
            json_dict = json.loads(json_data)
            threadId = int(json_dict.get('threadId'))
            connectionTime = int(json_dict.get('connectionTime'))
            executionTime = int(json_dict.get('executionTime'))
            thread_data.append({"threadId": threadId, "connectionTime": connectionTime, "executionTime": executionTime})

with open('log_requests.csv', 'r') as file:
    logs = file.readlines()
    request_info = []
    for data in logs[1:]:
        data_parts = data.strip().split(',')
        if len(data_parts) >= 8:
            id = int(data_parts[0])
            arrivalTime = int(data_parts[1])
            cacheLookupTime = int(data_parts[2])
            cacheLookupEndTime = int(data_parts[3])
            databaseRequestStartTime = int(data_parts[4])
            databaseRequestEndTime = int(data_parts[5])
            cacheUpdateStartTime = int(data_parts[6])
            cacheUpdateEndTime = int(data_parts[7])
            executionEnd = int(data_parts[8])
            databaseConncetionTime = 0
            databaseExecutionTime = 0

            for thread in thread_data:
                if thread['threadId'] == id:
                    databaseConncetionTime = thread['connectionTime']
                    databaseExecutionTime = thread['executionTime']

            request_info.append({
                "id": id,
                "arrivalTime": arrivalTime,
                "cacheLookupTime": cacheLookupTime,
                "cacheLookupEndTime": cacheLookupEndTime,
                "cacheUpdateStartTime": cacheUpdateStartTime,
                "cacheUpdateEndTime": cacheUpdateEndTime,
                "executionEnd": executionEnd,
                "databaseConncetionTime": databaseConncetionTime,
                "databaseExecutionTime": databaseExecutionTime
            })

with open('treated_requests_jet_test_monolith.txt', 'w') as file:
    file.write(json.dumps(request_info, indent=4))
