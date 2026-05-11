import random
from locust import FastHttpUser, task, constant_throughput, tag, LoadTestShape

class StepLoadShape(LoadTestShape):
    stages = [
        {"duration": 20, "users": 10, "spawn_rate": 5},
        {"duration": 40, "users": 50, "spawn_rate": 5},
        {"duration": 60, "users": 50, "spawn_rate": 5},
        {"duration": 80, "users": 100, "spawn_rate": 5},
        {"duration": 100, "users": 100, "spawn_rate": 5},
        {"duration": 120, "users": 100, "spawn_rate": 5},
        {"duration": 140, "users": 100, "spawn_rate": 5},
        {"duration": 160, "users": 100, "spawn_rate": 5},
        {"duration": 180, "users": 100, "spawn_rate": 5},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None


class SocialMediaUser(FastHttpUser):
    # Fix: constant_throughput(1) results in 1 req/sec. 
    # For 10 req/sec per user, use 10.
    wait_time = constant_throughput(1) 
    
    def on_start(self):
        """
        Called when a virtual user starts. 
        Good for initializing session-specific data.
        """
        self.user_id = random.randint(1, 1000)

    @tag('write')
    @task(1)
    def write_post(self):
        # Using a context manager allows for better error handling/grouping
        with self.client.post("/post", 
                             json={"content": "foo", "userId": self.user_id}, 
                             name="/posts", catch_response=True) as response:
            if response.status_code != 201:
                response.failure(f"Post failed with status: {response.status_code}")

    @tag('read')
    @task(9)
    def view_items(self):
        # name parameter groups URLs with dynamic IDs into one entry in the UI
        self.client.get(f"/feed/{self.user_id}", name="/feed/[id]")