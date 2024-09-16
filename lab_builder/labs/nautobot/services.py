import inspect
import os
from os import path

from jinja2 import Environment, FileSystemLoader

from lab_builder.lab import Service, LinuxNode
from lab_builder.labs.common import DB, Redis
from lab_builder import config

class NautobotBase(LinuxNode):
    """Nautobot application node."""
    node_config = config.NodeConfig(
        image="ghcr.io/nautobot/nautobot-dev:2.2"
    )


class NautobotApp(NautobotBase):
    def started(self):
        super().started()
        self.load_fixtures()

    def load_fixtures(self):
        fixtures = sorted(self.list_dir("/fixtures"))
        for fixture in fixtures:
            _, ext = path.splitext(fixture)
            if ext in [".yaml", ".yml", ".json"]:
                fixture = path.join("/fixtures", fixture)
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

        self.lab.adapter.exec(self, config.Command(cmd))

class Worker(NautobotBase):
    """Nautobot worker node."""

    node_config = config.NodeConfig(
        health_check=config.HealthCheck(
            interval=60,
            timeout=30,
            start_period=30,
            retries=3,
            test=["CMD-SHELL", "nautobot-server celery inspect ping --destination celery@$$HOSTNAME"],
        ),
        entrypoint="nautobot-server celery worker -l INFO --events"
    )


class Scheduler(NautobotBase):
    """Nautobot scheduler node."""

    node_config = config.NodeConfig(
        entrypoint="sh -c nautobot-server celery beat -l INFO",
        health_check=config.HealthCheck(
            test=["CMD", "true"],
        ),
    )


class NautobotService(Service):
    """Nautobot application stack as a service."""
    nautobot_config = "nautobot_config.py.j2"
    environment = config.Environment({
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
        "NAUTOBOT_ALLOWED_HOSTS": "*",
    })

    nautobot: NautobotApp = config.NodeConfig(
        dependencies=config.Dependencies(
            config.Dependency(name="db", stage=config.DependencyState.HEALTHY),
        ),
        ports=["127.0.0.1:8080:8080/tcp"],
    )

    worker: Worker = config.NodeConfig(
        dependencies=config.Dependencies(
            config.Dependency(name="nautobot", stage=config.DependencyState.HEALTHY),
        ),
    )

    scheduler: Scheduler = config.NodeConfig(
        dependencies=config.Dependencies(
            config.Dependency(name="nautobot", stage=config.DependencyState.HEALTHY),
        ),
    )

    db: DB
    redis: Redis

    def start(self):
        extra_config = ""
        if config_template := getattr(self.__class__, "extra_nautobot_config", None):
            extra_config = self.load_template(config_template).render()

        if config_template := getattr(self.__class__, "nautobot_config", None):
            template = self.load_template(config_template)
            lab_config = path.join(self.state_directory, "nautobot_config.py")
            with open(lab_config, "w", encoding="utf-8") as output:
                output.write(template.render(extra_config=extra_config))
            nautobot_config = config.FilesystemBind(
                mount_point="/opt/nautobot/nautobot_config.py",
                local_path=lab_config,
                read_only=True,
            )
            self.nautobot.node_config.binds.add(nautobot_config)
            self.worker.node_config.binds.add(nautobot_config)
            self.scheduler.node_config.binds.add(nautobot_config)

    def load_template(self, name):
        searchpath = []
        for _class in self.__class__.mro():
            if _class is not object:
                searchpath.append(path.dirname(inspect.getfile(_class)))
        loader = FileSystemLoader(searchpath=searchpath)
        return Environment(loader=loader).get_template(name)

    def restore_db(self, container_path: str):
        """Drop the nautobot database and recreate it.

        This command will drop the existing Nautobot database and recreate it from
        the provided `.sql` file.

        Args:
            container_path (str): The full path (including filename) to the `.sql` file
              to be imported in the new Nautobot database. This should be the absolute
              path within the container, not within the host filesystem.
        """
        adapter = self.lab.adapter
        adapter.exec(self.db, config.Command(["/usr/bin/dropdb", "-U", "nautobot", "-f", "nautobot"]))
        adapter.exec(self.db, config.Command(["/usr/bin/createdb", "-U", "nautobot", "nautobot"]))
        adapter.exec(self.db, config.Command([
            "/bin/sh",
            "-c",
            f"psql -h localhost -U nautobot < {container_path}",
        ]))
