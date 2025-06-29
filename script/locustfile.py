from locust import HttpUser, task, between
import random
import uuid
from datetime import datetime, timedelta, UTC


class PostgresWriteUser(HttpUser):
    wait_time = between(0.5, 1.5)  # simulate user delay

    @task
    def write_log(self):
        log_data = self.generate_random_log()
        self.client.post(
            "/write",
            json={"message": log_data},
            headers={"accept": "application/json"}
        )

    def generate_random_log(self):
        return {
            "user_id": random.randint(1000, 9999),
            "event": random.choice(["login", "logout", "purchase", "search", "error"]),
            "session_id": str(uuid.uuid4()),
            "success": random.choice([True, False]),
            "ip": f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 255)}",
            "timestamp": datetime.now(UTC).isoformat(),
            "details": {
                "device": random.choice(["desktop", "mobile", "tablet"]),
                "browser": random.choice(["chrome", "firefox", "safari", "edge"]),
                "os": random.choice(["windows", "macos", "linux", "android", "ios"]),
            }
        }
