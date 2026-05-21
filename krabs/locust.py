import random
import string
from locust import FastHttpUser, task, constant_throughput, tag, LoadTestShape

class StepLoadShape(LoadTestShape):
    # CORREÇÃO: Tempos ajustados para serem cumulativos (Estágio 1 dura 20s, o 2 dura 30s, etc.)
    stages = [
        {"duration": 20, "users": 10, "spawn_rate": 5},
        {"duration": 50, "users": 50, "spawn_rate": 10},   # 20s + 30s
        {"duration": 90, "users": 100, "spawn_rate": 10},  # 50s + 40s
        {"duration": 190, "users": 120, "spawn_rate": 10}, # 90s + 100s
        {"duration": 370, "users": 150, "spawn_rate": 10}, # 190s + 180s
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None


class SocialMediaUser(FastHttpUser):
    # Mantém o throughput controlado por usuário (ex: 1 requisição por segundo por usuário)
    wait_time = constant_throughput(1) 
    
    def on_start(self):
        # MELHORIA: Expandido o range para evitar gargalos artificiais de cache no banco
        self.user_id = random.randint(1, 100000)

    def _generate_random_content(self):
        """Helper para gerar conteúdos diferentes e forçar o backend a trabalhar."""
        return "".join(random.choices(string.ascii_letters, k=10))

    @tag('write')
    @task(1)
    def write_post(self):
        payload = {"content": self._generate_random_content(), "userId": self.user_id}
        
        # MELHORIA: Adicionado timeout de 5 segundos para conexões presas
        with self.client.post("/post", json=payload, name="/posts", timeout=5.0, catch_response=True) as response:
            if response.status_code != 201:
                response.failure(f"Post falhou. Status: {response.status_code} | Resposta: {response.text[:100]}")

    @tag('read')
    @task(9)
    def view_items(self):
        with self.client.get(f"/feed/{self.user_id}", name="/feed/[id]", timeout=5.0, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Feed falhou. Status: {response.status_code}")
                return # Impede que o código continue e tente ler o JSON de uma requisição que falhou
            
            # CORREÇÃO: Tratamento seguro para parsing de JSON
            try:
                json_data = response.json()
                if isinstance(json_data, list):
                    # Validação opcional: verifica apenas o primeiro item para economizar CPU do Locust
                    if json_data and "content" not in json_data[0]:
                        response.failure("Estrutura do feed inválida: campo 'content' ausente.")
                else:
                    response.failure("Resposta do feed não veio no formato de lista esperado.")
            except ValueError:
                response.failure("O corpo da resposta não é um JSON válido.")