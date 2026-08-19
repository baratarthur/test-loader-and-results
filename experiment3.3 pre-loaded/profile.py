import random
import numpy as np
from locust import FastHttpUser, task, constant_throughput, LoadTestShape

# Shared state between Shape and Users
CURRENT_ZIPF_PROBABILITY = 0.0
CURRENT_WRITE_RATIO = 0.1  # Default: 10% writes


class DynamicBehaviorShape(LoadTestShape):
    stages = [
        { # 0 -> 10s
            "duration": 10,
            "total_users": 10,
            "spawn_rate": 2,
            "zipf_ratio": 0.0,
            "write_ratio": 0.1,
        },
        { # 10 -> 20s
            "duration": 20,
            "total_users": 20,
            "spawn_rate": 2,
            "zipf_ratio": 0.2,
            "write_ratio": 0.1,
        },
        { # 20 -> 30s
            "duration": 30,
            "total_users": 30,
            "spawn_rate": 2,
            "zipf_ratio": 0.3,
            "write_ratio": 0.2,
        },
        { # 30s -> 6m
            "duration": 6*60,
            "total_users": 50,
            "spawn_rate": 3,
            "zipf_ratio": 0.8,
            "write_ratio": 0.2,
        }
    ]

    def tick(self):
        global CURRENT_ZIPF_PROBABILITY
        global CURRENT_WRITE_RATIO

        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                CURRENT_ZIPF_PROBABILITY = stage["zipf_ratio"]
                CURRENT_WRITE_RATIO = stage["write_ratio"]

                return (
                    stage["total_users"],
                    stage["spawn_rate"],
                )

        return None


class CombinedUser(FastHttpUser):
    wait_time = constant_throughput(1)

    def on_start(self):
        self.user_id = random.randint(1, 1000)
        self.zipf_parameter = 1.2
        self.total_posts = 1000

    @task
    def dynamic_router(self):
        global CURRENT_ZIPF_PROBABILITY
        global CURRENT_WRITE_RATIO

        # ----------------------------------------
        # Zipfian workload
        # ----------------------------------------
        if random.random() < CURRENT_ZIPF_PROBABILITY:
            post_id = min(
                np.random.zipf(self.zipf_parameter),
                self.total_posts,
            ) + 1000

            self.client.get(
                f"/post/{post_id}",
                name="/post/[zipf_id]",
            )
            return

        # ----------------------------------------
        # Social workload
        # ----------------------------------------
        elif random.random() < CURRENT_WRITE_RATIO:
            self.client.post(
                "/post",
                json={
                    "content": "foo",
                    "userId": self.user_id,
                },
                name="/post",
            )
        else:
            self.client.get(
                f"/feed/{self.user_id}",
                name="/feed/[id]",
            )