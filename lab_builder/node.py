from enum import Enum
import os
import shutil
from typing import TypedDict
from dataclasses import dataclass
import typing

from lab_builder.util import resolve_attribute, resolve_binds

if typing.TYPE_CHECKING:
    from lab import Service

class ConfigObject:
    def update_dict(self, values: dict, attr, key = None, check = lambda value: value):
        if key is None:
            key = attr
        value = getattr(self, attr, None)
        if check(value):
            if hasattr(value, "as_dict"):
                values[key] = value.as_dict()
            else:
                values[key] = value


HealthCheckConfig = TypedDict(
    "HealthCheckConfig", {
        "test": list[str],
        "interval": int,
        "start-period": int,
        "retries": int,
        "timeout": int,
    },
)


@dataclass
class HealthCheck(ConfigObject):
    test: list[str]
    start_period: int = 0
    retries: int = 3
    interval: int = 30
    timeout: int = 30

    def as_dict(self) -> HealthCheckConfig:
        values = {}
        self.update_dict(values, "test")
        self.update_dict(values, "start_period", "start-period")
        self.update_dict(values, "retries",)
        self.update_dict(values, "interval")
        self.update_dict(values, "timeout")
        return values


class DependencyState(Enum):
    CREATE = "create"
    CREATE_LINKS = "create-links"
    CONFIGURE = "configure"
    HEALTHY = "healthy"
    EXIT = "exit"


@dataclass
class Dependency:
    name: str
    state: DependencyState

    def as_dict(self):
        return {"node": self.name, "state": self.state.value}


NodeConfig = TypedDict(
    "NodeConfig",
    {
        "kind": str,
        "image": str,
        "healthcheck": HealthCheckConfig,
        "network-mode": str,
        "stages": dict[str, dict[str, str]],
        "env": dict[str, str],
        "cmd": str,
        "binds": list[str],
        "ports": list[str],
    }
)


class Node(ConfigObject):
    service: "Service"
    name: str = None
    kind: str = None
    network_mode: str = "bridge"
    health_check: HealthCheck = None
    command: str = None
    dependencies: dict[str, str]
    networks: list[str]
    binds: list[str]
    ports: list[str]

    def __init__(
            self,
            name: str,
            service,
            dependencies: list[Dependency] = None,
            binds: list[str] = None,
            ports: list[str] = None,
        ):
        self.name = name
        self.service = service
        self.dependencies = resolve_attribute(self.__class__, "dependencies", dependencies or [])
        self.ports = resolve_attribute(self.__class__, "ports", ports or [])
        self.binds = resolve_attribute(self.__class__, "binds", binds or [])
        self.binds = resolve_binds(self, self.binds)

    def as_dict(self) -> NodeConfig:
        values = {}
        self.update_dict(values, "kind")
        self.update_dict(values, "image")
        self.update_dict(values, "health_check", "healthcheck")
        self.update_dict(values, "network_mode", "network-mode", lambda value: value != "bridge")
        self.update_dict(values, "dependencies", "stages")
        if "stages" in values:
            stages = []
            for dependency in values["stages"]:
                stages.append(dependency.as_dict())

            values["stages"] = {
                "create": {
                    "wait-for": stages,
                }
            }
        self.update_dict(values, "command", "cmd")
        self.update_dict(values, "binds", "binds")
        self.update_dict(values, "ports", "ports")
        if getattr(self, "environment", None):
            values["env"] = self.service.resolve_environment(self.environment)
        else:
            values["env"] = self.service.default_environment
        return values

    @property
    def directory(self):
        return os.path.join(self.service.directory, self.name)

    def created(self):
        try:
            os.mkdir(self.directory)
        except FileExistsError:
            pass
        for bind in self.binds:
            local, _ = bind.split(":", 1)
            if local.startswith(self.directory):
                try:
                    os.makedirs(local)
                except FileExistsError:
                    pass
        self.binds.append(f"{self.directory}:/lab_builder_data")

    def started(self):
        pass

    def stopped(self):
        shutil.rmtree(self.directory)

    def run_cmd(self, cmd):
        cmd = [
            "exec",
            "--label", f"clab-node-name={self.name}",
            "--cmd", " ".join(cmd),
        ]

        self.service.lab.run_clab_cmd(cmd)

class LinuxNode(Node):
    kind = "linux"
