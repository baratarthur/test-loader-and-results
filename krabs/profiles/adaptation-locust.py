import random
import numpy as np
from locust import FastHttpUser, task, constant_throughput, tag, LoadTestShape

# Variáveis globais para controle de estado compartilhado entre o Shape e os Usuários
CURRENT_ZIPF_PROBABILITY = 0.0

class DynamicBehaviorShape(LoadTestShape):
    stages = [
        # Cenário 1: Apenas tráfego normal (0% Zipfian) (0:00 a 0:30)
        {"duration": 30, "total_users": 10, "spawn_rate": 2, "zipf_ratio": 0.0},
        
        # Cenário 2: Tráfego normal cresce, um pouco de Zipfian aparece (10% Zipfian) (0:30 a 2:00)
        {"duration": 2*60, "total_users": 20, "spawn_rate": 1, "zipf_ratio": 0.1},

        # Cenário 3: Tráfego normal cresce, um pouco de Zipfian aparece (80% Zipfian) (2:00 a 6:00)
        {"duration": 6*60, "total_users": 40, "spawn_rate": 1, "zipf_ratio": 0.8},
        
        # Cenário 4: O pico passa, tráfego Zipfian reduz drasticamente (10% Zipfian) (6:00 a 7:00)
        {"duration": 7*60, "total_users": 20, "spawn_rate": 5, "zipf_ratio": 0.1},
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