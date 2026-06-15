import random
import numpy as np
from locust import FastHttpUser, task, constant_throughput, tag, LoadTestShape

# --- FORMATO DO TESTE COM PESOS DINÂMICOS ---
class DynamicStepShape(LoadTestShape):
    """
    Definimos os estágios especificando a duração e a quantidade exata 
    de cada tipo de usuário que queremos naquele momento.
    """
    stages = [
        # Cenário 1: Início leve, apenas usuários normais (Minuto 0 a 0:30)
        {"duration": 30, "SocialMediaUser": 10, "ZipfianUser": 0, "spawn_rate": 2},
        
        # Cenário 2: O tráfego normal cresce (Minuto 0:30 a 1:00)
        {"duration": 60, "SocialMediaUser": 20, "ZipfianUser": 2, "spawn_rate": 1},
        
        # Cenário 3: Um post viral acontece! Explosão de comportamento Zipfian (Minuto 1:00 a 2:00)
        {"duration": 120, "SocialMediaUser": 15, "ZipfianUser": 30, "spawn_rate": 4},
        
        # Cenário 4: O pico passa, o tráfego estabilizes (Minuto 2:00 a 3:00)
        {"duration": 180, "SocialMediaUser": 15, "ZipfianUser": 5, "spawn_rate": 2},
    ]

    def tick(self):
        run_time = self.get_run_time()
        
        for stage in self.stages:
            if run_time < stage["duration"]:
                # Retornamos uma tupla: (Total de usuários, Taxa de spawn, Dicionário com a proporção)
                # O Locust vai usar o dicionário user_classes para balancear o teste dinamicamente
                user_classes = {
                    SocialMediaUser: stage["SocialMediaUser"],
                    ZipfianUser: stage["ZipfianUser"]
                }
                # Calculamos o total de usuários combinados para este estágio
                total_users = stage["SocialMediaUser"] + stage["ZipfianUser"]
                
                return (total_users, stage["spawn_rate"], user_classes)
                
        return None


# --- COMPORTAMENTOS (Sem pesos estáticos nas classes) ---

class SocialMediaUser(FastHttpUser):
    wait_time = constant_throughput(1) 
    
    def on_start(self):
        self.user_id = random.randint(1, 1000)

    @tag('write')
    @task(1)
    def write_post(self):
        self.client.post("/post", json={"content": "foo", "userId": self.user_id}, name="/posts")

    @tag('read')
    @task(9)
    def view_items(self):
        self.client.get(f"/feed/{self.user_id}", name="/feed/[id]")


class ZipfianUser(FastHttpUser):
    wait_time = constant_throughput(1)

    def on_start(self):
        self.zipf_parameter = 1.2 
        self.total_posts = 1000 

    @tag('zipf_read')
    @task
    def view_popular_posts(self):
        post_id = min(np.random.zipf(self.zipf_parameter), self.total_posts)
        self.client.get(f"/post/{post_id}", name="/post/[zipf_id]")
