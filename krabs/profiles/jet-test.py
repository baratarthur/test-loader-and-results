import random
import numpy as np
from locust import FastHttpUser, task, constant_throughput, tag, LoadTestShape

# Variáveis globais para controle de estado compartilhado entre o Shape e os Usuários
CURRENT_ZIPF_PROBABILITY = 0.0

class DynamicBehaviorShape(LoadTestShape):
    stages = [
        {"duration": 10, "total_users": 10, "spawn_rate": 2, "zipf_ratio": 0.0},
        {"duration": 20, "total_users": 20, "spawn_rate": 1, "zipf_ratio": 0.1},
        {"duration": 50, "total_users": 40, "spawn_rate": 1, "zipf_ratio": 0.8},
        {"duration": 60, "total_users": 20, "spawn_rate": 5, "zipf_ratio": 0.1},
    ]

    def tick(self):
        global CURRENT_ZIPF_PROBABILITY
        run_time = self.get_run_time()
        
        for stage in self.stages:
            if run_time < stage["duration"]:
                # Atualiza a probabilidade global que os usuários usam para decidir a tarefa
                CURRENT_ZIPF_PROBABILITY = stage["zipf_ratio"]
                return (stage["total_users"], stage["spawn_rate"])
                
        return None


class CombinedUser(FastHttpUser):
    wait_time = constant_throughput(1) 
    
    def on_start(self):
        self.user_id = random.randint(1, 1000)
        self.zipf_parameter = 1.2 
        self.total_posts = 1000 

    @task
    def dynamic_router(self):
        """
        Em vez de deixar o Locust decidir qual usuário spawnar, o próprio usuário
        decide dinamicamente qual comportamento assumir com base no momento do teste.
        """
        global CURRENT_ZIPF_PROBABILITY
        
        # Decisão baseada na probabilidade do estágio atual
        if random.random() < CURRENT_ZIPF_PROBABILITY:
            # --- COMPORTAMENTO ZIPFIAN ---
            post_id = min(np.random.zipf(self.zipf_parameter), self.total_posts) + 1000
            self.client.get(f"/post/{post_id}", name="/post/[zipf_id]")
        else:
            # --- COMPORTAMENTO REDE SOCIAL NORMAL ---
            # Proporção interna de 1 escrita para 9 leituras
            if random.randint(1, 10) == 1:
                self.client.post("/post", json={"content": "foo", "userId": self.user_id}, name="/posts")
            else:
                self.client.get(f"/feed/{self.user_id}", name="/feed/[id]")