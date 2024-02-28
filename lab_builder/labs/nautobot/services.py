import inspect
import os

from jinja2 import Environment, FileSystemLoader

from lab_builder.lab import Service
from lab_builder.labs.common import DB, Redis
from lab_builder.node import Dependency, DependencyState, HealthCheck, LinuxNode

class NautobotBase(LinuxNode):
    """Nautobot application node."""
    image = "ghcr.io/nautobot/nautobot:2.0"

class NautobotApp(NautobotBase):
    def started(self):
        super().started()
        self.load_fixtures()

    def load_fixtures(self):
        fixtures = sorted(self.list_dir("/fixtures"))
        for fixture in fixtures:
            _, ext = os.path.splitext(fixture)
            if ext in [".yaml", ".yml", ".json"]:
                fixture = os.path.join("/fixtures", fixture)
                self.load_fixture(fixture)

    def load_fixture(self, container_path: str):
        """Load a single fixture file into the Nautobot server.

        Args:
            container_path (str): The path (within the container) to the
            fixture file.
        """
        cmd = [
            "nautobot-server",
            "loaddata",
            container_path,
        ]

        self.run_cmd(cmd)

class Worker(NautobotBase):
    """Nautobot worker node."""

    health_check = HealthCheck(
      interval=60,
      timeout=30,
      start_period=30,
      retries=3,
      test=["CMD-SHELL", "nautobot-server celery inspect ping --destination celery@$$HOSTNAME"],
    )

    entrypoint = "nautobot-server celery worker -l INFO --events"


class Scheduler(NautobotBase):
    """Nautobot scheduler node."""

    entrypoint = "sh -c nautobot-server celery beat -l INFO"
    health_check = HealthCheck(
      test=["CMD", "true"],
    )


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
        "nautobot": NautobotApp,
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
        "nautobot": ["127.0.0.1:8080:8080/tcp"],
    }

    def start(self):
        super().start()
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
        searchpath = []
        for _class in self.__class__.mro():
            if _class is not object:
                searchpath.append(os.path.dirname(inspect.getfile(_class)))
        loader = FileSystemLoader(searchpath=searchpath)
        return Environment(loader=loader).get_template(name)
