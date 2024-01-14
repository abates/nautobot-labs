from lab_builder import Application
from lab_builder.node import HealthCheck, ApplicationNode

class App(ApplicationNode):
    name = "nautobot"
    image = "ghcr.io/nautobot/nautobot:2.0"


class Worker(App):
    name = "worker"
    health_check = HealthCheck(
      interval=60,
      timeout=30,
      start_period=30,
      retries=3,
      test=["CMD", "bash", "-c", "nautobot-server celery inspect ping --destination celery@$$HOSTNAME"],
    )


class Scheduler(App):
    name = "scheduler"


class DB(ApplicationNode):
    name = "db"
    image = "postgres:13"


class Redis(ApplicationNode):
    name = "redis"
    image = "redis:6-alpine"


class Nautobot(Application):
    name = "Nautobot"
    environment = {
        # Admin User
        "NAUTOBOT_CREATE_SUPERUSER": True,
        "NAUTOBOT_SUPERUSER_NAME": "admin",
        "NAUTOBOT_SUPERUSER_EMAIL": "admin@example.com",
        "NAUTOBOT_SUPERUSER_PASSWORD": "admin",
        "NAUTOBOT_SUPERUSER_API_TOKEN": "0123456789abcdef0123456789abcdef01234567",
        # Database credentials
        "NAUTOBOT_DB_NAME": "nautobot",
        "NAUTOBOT_DB_USER": "nautobot",
        "NAUTOBOT_DB_PASSWORD": "nautobot",
        "NAUTOBOT_DB_HOST": "db",
        # Napalm credentials
        "NAUTOBOT_NAPALM_USERNAME": "",
        "NAUTOBOT_NAPALM_PASSWORD": "",
        # Redis and Django secrets
        "NAUTOBOT_REDIS_HOST": "redis",
        "NAUTOBOT_REDIS_PORT": "6379",
        "NAUTOBOT_REDIS_PASSWORD": "changeme",
        "NAUTOBOT_SECRET_KEY": "changeme",
        # PostgreSQL details
        "POSTGRES_PASSWORD": "{NAUTOBOT_DB_PASSWORD}",
        "POSTGRES_USER": "{NAUTOBOT_DB_USER}",
        "POSTGRES_DB": "{NAUTOBOT_DB_NAME}",
        "PGPASSWORD": "{NAUTOBOT_DB_PASSWORD}",
    }

    nodes = {
        App: {
            "wait_for": {
                "DB": "healthy",
                "Redis": "started",
            }
        },
        Worker: {
            "wait_for": {
                "App": "healthy",
            }
        },
        Scheduler: {
            "wait_for": {
                "App": "healthy",
            }
        },
        DB: {},
        Redis: {},
    }

    networks = {
        "App": ["default", "mgmt"],
    }
