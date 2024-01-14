from typing import TypedDict
from dataclasses import dataclass


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


`HealthCheckConfig = TypedDict(
    "HealthCheckConfig", {
        "test": list[str],
        "start-period": int,
        "retries": int,
        "timeout": int,
    },
)


@dataclass
class HealthCheck(ConfigObject):
    test: list[str]
    start_period: int
    retries: int
    interval: int
    timeout: int

    def as_dict(self) -> HealthCheckConfig:
        values = {}
        self.update_dict(values, "test")
        self.update_dict(values, "start_period", "start-period")
        self.update_dict(values, "retries",)
        self.update_dict(values, "interval")
        self.update_dict(values, "timeout")
        return values


NodeConfig = TypedDict(
    "NodeConfig",
    {
        "kind": str,
        "image": str,
        "healthcheck": HealthCheckConfig,
        "network-mode": str,
    }
)


class Node(ConfigObject):
    name: str = None
    kind: str = None
    network_mode: str = "bridge"
    health_check: HealthCheck = None

    dependencies: dict[str, str]
    networks: list[str]

    def __init__(self, lab, dependencies=None, networks=None):
        self.lab = lab
        self.dependencies = dependencies
        self.networks = networks

    def as_dict(self) -> NodeConfig:
        values = {}
        self.update_dict(values, "kind")
        self.update_dict(values, "image")
        self.update_dict(values, "health_check", "healthcheck")
        self.update_dict(values, "network_mode", "network-mode", lambda value: value is not "bridge")
        return values


class ApplicationNode(Node):
    kind = "linux"
    # network_mode = "none"

    def __init__(self, lab, application, **kwargs):
        super().__init__(lab, **kwargs)
        self.application = application


class NetworkNode(Node):
    pass
