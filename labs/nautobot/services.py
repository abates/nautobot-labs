import inspect
import os

from jinja2 import Environment, FileSystemLoader

from lab_builder import Service
from lab_builder.node import Dependency, DependencyState, HealthCheck, LinuxNode

class NautobotNode(LinuxNode):
    """Nautobot application node."""
    image = "ghcr.io/nautobot/nautobot:2.0"

    def load_fixture(self, container_path: str):
        cmd = [
            "nautobot-server",
            "loaddata",
            container_path,
        ]

        self.run_cmd(cmd)

class Worker(NautobotNode):
    """Nautobot worker node."""

    health_check = HealthCheck(
      interval=60,
      timeout=30,
      start_period=30,
      retries=3,
      test=["CMD-SHELL", "nautobot-server celery inspect ping --destination celery@$$HOSTNAME"],
    )


class Scheduler(NautobotNode):
    """Nautobot scheduler node."""


class DB(LinuxNode):
    """PostgreSQL database node."""

    image = "postgres:13"
    health_check = HealthCheck(
      interval=10,
      timeout=5,
      retries=10,
      test=["CMD-SHELL", "pg_isready --username=$$POSTGRES_USER --dbname=$$POSTGRES_DB"],
    )

    environment = {
        "POSTGRES_PASSWORD": "{NAUTOBOT_DB_PASSWORD}",
        "POSTGRES_USER": "{NAUTOBOT_DB_USER}",
        "POSTGRES_DB": "{NAUTOBOT_DB_NAME}",
        "PGPASSWORD": "{NAUTOBOT_DB_PASSWORD}",
    }

    binds = ["data:/var/lib/postgresql/data"]


class Redis(LinuxNode):
    """Redis node."""

    image = "redis:6-alpine"
    command = 'sh -c "redis-server --loglevel debug --appendonly yes --requirepass $$REDIS_PASSWORD"'
    environment = {
        "REDIS_PASSWORD": "{NAUTOBOT_REDIS_PASSWORD}"
    }


class NautobotService(Service):
    """Nautobot application stack as a service."""
    nautobot_config = "nautobot_config.py.j2"
    shared_environment = {
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
        "NAUTOBOT_ALLOWED_HOSTS": "localhost",
    }

    nodes = {
        "nautobot": NautobotNode,
        "worker": Worker,
        "scheduler": Scheduler,
        "db": DB,
        "redis": Redis,
    }

    dependencies = {
        "nautobot": [Dependency(name="db", state=DependencyState.HEALTHY)],
        "worker": [Dependency(name="nautobot", state=DependencyState.HEALTHY)],
        "scheduler": [Dependency(name="nautobot", state=DependencyState.HEALTHY)],
    }

    ports = {
        "nautobot": ["8080/tcp"],
    }

    def created(self):
        super().created()
        extra_config = ""
        if config_template := getattr(self.__class__, "extra_nautobot_config", None):
            extra_config = self.load_template(config_template).render()

        if config_template := getattr(self.__class__, "nautobot_config", None):
            template = self.load_template(config_template)
            lab_config = os.path.join(self.state_directory, "nautobot_config.py")
            with open(lab_config, "w", encoding="utf-8") as output:
                output.write(template.render(extra_config=extra_config))
            self.nodes["nautobot"].binds.append(f"{lab_config}:/opt/nautobot/nautobot_config.py")
            self.nodes["worker"].binds.append(f"{lab_config}:/opt/nautobot/nautobot_config.py")
            self.nodes["scheduler"].binds.append(f"{lab_config}:/opt/nautobot/nautobot_config.py")

    def load_template(self, name):
        searchpath = os.path.dirname(inspect.getfile(self.__class__))
        loader = FileSystemLoader(searchpath=searchpath)
        return Environment(loader=loader).get_template(name)
