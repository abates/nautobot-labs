from enum import Enum
import os
import shutil
from typing import TypedDict
from dataclasses import dataclass
from lab_builder.lab import Definition

class ConfigObjectMixin:
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
class HealthCheck(ConfigObjectMixin):
    test: list[str] = None
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


class Node(Definition, ConfigObjectMixin):
    kind: str = None
    network_mode: str = "bridge"
    health_check: HealthCheck = None
    command: str = None
    networks: list[str]
    environment: dict[str, str]

    # These attributes are re-defined here because in `Layer` they
    # are dictionaries of `node_name`/definitions, but in the `Node`
    # itself, they are just the definition.
    dependencies: list[Dependency]
    binds: list[str]
    ports: list[str]

    def __init__(
            self,
            name: str,
            parent: Definition,
            health_check: HealthCheck = None,
            **kwargs
        ):
        self.health_check = health_check
        super().__init__(name, parent, **kwargs)
        self.binds = self._resolve_binds(self.binds)

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
        env = getattr(self, "environment", {})
        values["env"] = self.parent.resolve_environment(env)
        return values

    def start(self):
        super().start()
        for bind in self.binds:
            local, _ = bind.split(":", 1)
            if local.startswith(self.state_directory):
                try:
                    os.makedirs(local)
                except FileExistsError:
                    pass

    def created(self):
        super().created()
        self.binds.append(f"{self.state_directory}:/lab_builder_data")

    def destroyed(self):
        shutil.rmtree(self.state_directory)

    def run_cmd(self, cmd):
        cmd = [
            "exec",
            "--label", f"clab-node-name={self.name}",
            "--cmd", " ".join(cmd),
        ]

        self.lab.run_clab_cmd(cmd)

class LinuxNode(Node):
    kind = "linux"
