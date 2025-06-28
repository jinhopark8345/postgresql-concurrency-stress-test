from locust import HttpUser, task, between

class PostgresWriteUser(HttpUser):
    wait_time = between(1, 2)  # time between requests per user (seconds)

    @task
    def write_log(self):
        self.client.post("/write", params={"message": "Hello"}, headers={"accept": "application/json"})
