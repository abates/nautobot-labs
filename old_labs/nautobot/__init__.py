"""Lab definition for Nautobot lab"""

import os
import shutil
from datetime import timedelta
from string import Template
from dataclasses import dataclass, field


def find_link(path):
    try:
        link = os.readlink(path)
        return find_link(link)
    except OSError:  # if the last is not symbolic file will throw OSError
        return path


volume_template_str = '      - "$src:$dst"'

volume_template = Template(volume_template_str)

compose_template_str = """
version: "3.8"
services:
  nautobot:
    volumes: $volumes
  nautobot-worker:
    volumes: $volumes
"""

compose_template = Template(compose_template_str)


@dataclass
class Volume:
    name: str = ""
    local_path: str = ""
    container_path: str

    def __post_init__(self):
        if not self.name and not self.local_path:
            raise TypeError("Either name or local path must be specified for volume")
        if self.name and self.local_path:
            raise TypeError("Only name or local path can be specified for a volume")

    def __str__(self):
        if self.name:
            return f"{self.name}:{self.container_path}"
        return f"{self.local_path}:{self.container_path}"


@dataclass
class Port:
    local_port: int
    forwarded_port: int = 0

    def __str__(self):
        if self.forwarded_port == 0:
            return str(self.local_port)
        return f"{self.local_port}:{self.forwarded_port}"


@dataclass
class HealthCheck:
    interval: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    timeout: timedelta = field(default_factory=lambda: timedelta(seconds=10))
    start_period: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    retries: int = 3
    test: list[str]


@dataclass
class Service:
    image: str
    entrypoint: str = ""
    command: str = ""

    ports: list[Port] = field(default_factory=list)
    volumes: list[Volume] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
    tty: bool = False

@dataclass
class Component:
    services: list[Service] = field(default_factory=list)
    
class NautobotLab:
    def __init__(self):
        self.dir = os.path.dirname(__file__)
        self.tempdir = os.path.join(self.dir, ".tmp")
        self.tempfile = os.path.join(self.tempdir, "docker-compose.nautobot-apps.yaml")
        self.apps_dir = os.path.join(self.dir, "apps")
        if not os.path.exists(self.tempdir):
            os.mkdir(self.tempdir)

    @property
    def compose_files(self):
        if os.path.exists(self.tempfile):
            return ["docker-compose.nautobot.yml", self.tempfile]
        return ["docker-compose.nautobot.yml"]

    def pre_start(self):
        volumes = []
        if not os.path.exists(self.apps_dir):
            os.mkdir(self.apps_dir)

        for filename in os.listdir(self.apps_dir):
            if filename.startswith("."):
                continue

            volumes.append(volume_template.substitute(src=find_link(os.path.join(self.apps_dir, filename)), dst=f"/opt/nautobot/apps/{filename}"))

        volume_str = "\n" + "\n".join(volumes) if volumes else "[]"
        with open(self.tempfile, "w") as file:
            print(compose_template.substitute(volumes=volume_str), file=file)

    def post_stop(self):
        if os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir)


lab = NautobotLab
