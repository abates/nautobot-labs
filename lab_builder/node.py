from enum import Enum
import json
import os
import shlex
import shutil
from typing import TypedDict
from dataclasses import dataclass
from lab_builder.lab import Definition


def command(method):
    """Decorator to indicate a method should be a command."""
    return method

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
        "entrypoint": str,
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
    entrypoint: str

    # These attributes are re-defined here because in `Layer` they
    # are dictionaries of `node_name`/definitions, but in the `Node`
    # itself, they are just the definition.
    dependencies: list[Dependency]
    binds: list[str]
    ports: list[str]
    links: dict[str, str]

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
        self.update_dict(values, "entrypoint")
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
        self.update_dict(values, "binds")
        self.update_dict(values, "ports")
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
        container_file = getattr(self, "containerfile", None)
        image = getattr(self, "image", None)
        if container_file is None and image is None:
            raise ValueError(f"Either containerfile or image must be specified for {self.__class__.__name__}.")
        if not ((container_file is None) ^ (image is None)):
            print(container_file, image)
            raise ValueError(f"Both containerfile and image are set for {self.__class__.__name__}. Choose only one.")
        
        if container_file:
            container_file = os.path.join(self.definition_directory, container_file)
            self.image = f"lab_builder/{self.__class__.__name__.lower()}:latest"
            cmd = [
                "docker",
                "image",
                "build",
                "--tag",
                self.image,
                "--file",
                container_file,
                os.path.dirname(container_file),
            ]
            self.lab.run_cmd(cmd)

    def destroyed(self):
        shutil.rmtree(self.state_directory)

    def run_cmd(self, cmd, working_directory=None, interactive=False):
        shell_command = shlex.join(cmd)
        if working_directory:
            shell_command = " ".join([
                "sh",
                "-c",
                shlex.quote(" ".join(["cd", working_directory, "&&", shell_command])),
            ])

        cmd = [
            "exec",
            "--label", f"clab-node-name={self.name}",
            "--format", "json",
        ]

        if interactive:
            cmd.append("-it")
        
        cmd.extend(["--cmd", shell_command])

        process = self.lab.run_clab_cmd(cmd)
        output = json.loads(process.stdout)
        output = next(iter(output.values())).pop()
        if output["return-code"] != 0:
            print(shell_command)
            print(output["stderr"])
        return output

class NetworkNode(Node):
    """A containerlab network device node."""

class LinuxNode(Node):
    """A container lab linux node."""
    kind = "linux"

    def list_dir(self, path):
        """Retrieve the contents of a path within a node.

        Args:
            path (str): The directory path to list

        Returns:
            list[str]: The contents of the node's directory
        """
        output = self.run_cmd(["ls", path])
        if output["return-code"] == 0:
            if output["stdout"]:
                return output["stdout"].split("\n")
        return []

    def path_exists(self, path):
        """Determine if a path exists on the node.

        Args:
            path (str): Path to check

        Returns:
            bool: True if the path exists, otherwise False
        """
        output = self.run_cmd(["ls", path])
        return output["return-code"] == 0
