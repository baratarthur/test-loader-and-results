import json

post_repository_tag = '[@PostsRepository]'

thread_data = []

with open('logs_jet_test_monolith.txt', 'r') as file:
    logs = file.readlines()
    for line in logs:
        if post_repository_tag in line:
            json_data = line.split('-')[1].strip().replace(post_repository_tag, '')
            json_dict = json.loads(json_data)
            threadId = int(json_dict.get('threadId'))
            connectionTime = int(json_dict.get('connectionTime'))
            executionTime = int(json_dict.get('executionTime'))
            thread_data.append({"threadId": threadId, "connectionTime": connectionTime, "executionTime": executionTime})

with open('requests_jet_test_monolith.txt', 'r') as file:
    logs = file.readlines()
    request_info = json.loads(logs[0].strip())
    for request in request_info:
        for thread in thread_data:
            if request['id'] == thread['threadId']:
                request['databaseRequestStartTime'] = request['arrivalTime'] + thread['connectionTime']
                request['databaseRequestEndTime'] = request['arrivalTime'] + thread['connectionTime'] + thread['executionTime']

with open('treated_requests_jet_test_monolith.txt', 'w') as file:
    file.write(json.dumps(request_info, indent=4))
