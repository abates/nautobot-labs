"""The config module contains all of the available configuration items for a lab.

This module provides data classes that help to define lab configuration, but also
provides a way to override configuration when labs are composed of re-usable
components.

Configuration items represent objects that can be merged with other configuration
items in order to update the configuration for overrides as service and node classes
are inherited and used in composable labs.

For instance, a node definition may provide some default volume mounts (binds). This
node definition may be used in several different service definitions each specifying
slightly different binds.

Additionally, the service itself may be used more than once in a single lab, and the
binds for each of the nodes may be redefined in each of the services.

Consider the following list of node configs:

>>> configs = [
>>>    NodeConfig(binds={"/mnt/point1": "/path/to/local1"}),
>>>    NodeConfig(binds={"/mnt/point1": "/path/to/local2"}),
>>>    NodeConfig(binds={"/mnt/point2": "/path/to/local3"}),
>>> ]

The configs can be merged using reduce:
>>> from functools import reduce
>>> merge_config = reduce(NodeConfig.update, configs)

This would result with a merged config where the binds are:

>>> print(merge_config.binds)
{'/mnt/point1': '/path/to/local2', '/mnt/point3': '/path/to/local3'}

The configuration items appearing later in the list will override the configuration
items that appear earlier in the list. The `Config.update` method ensures that
only like configuration items are merged. Scalar values are overwritten, dictionaries
are merged and lists are appended.

Additionally, configuration items can be converted to keyword argument dictionaries
for use in initializing their lab object counterparts. Given the merged configuration
above, it can be used to initialize a node:

>>> node = Node(name="My Node", parent=my_service, **merge_config.kwargs)
"""
from abc import ABC, abstractmethod
from collections import UserDict
from dataclasses import dataclass, field, fields
from enum import Enum
from os import path
from typing import List, TypeVar
from glob import glob
import typing

if typing.TYPE_CHECKING:
    from .lab import Node


class Config(ABC):
    @abstractmethod
    def copy(self) -> "Config":
        """Return a copy of the config item."""

    @abstractmethod
    def update(self, other: "Config"):
        """Update the values of the current config with the supplied config."""

    @abstractmethod
    def bind(self, instance):
        """Bind the configuration object to an actual lab instance (lab, service or node)."""

class DataclassConfig(Config):
    """A `Config` class for dataclasses that has concrete implementations for `copy` and `update`."""

    def copy(self) -> "Config":
        """Return a copy of the config.
        
        This method will iterate the dataclass fields and copy their
        values. If a value is an instance of the `Config` class then
        that item itself will have the `copy` method called.
        """
        kwargs = {}
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, Config):
                kwargs[field.name] = value.copy()
            else:
                kwargs[field.name] = value
        return self.__class__(**kwargs)

    def update(self, other: "Config"):
        """Update the fields of the current config with those supplied with another config.
        
        This method will iterate the dataclass fields and update the local
        config, with the values of the other config's attributes that are _not_
        default values.
        """
        if other is None:
            return

        for field in fields(self):
            value = getattr(other, field.name)
            if isinstance(value, Config):
                self_value = getattr(self, field.name, None)
                if self_value:
                    self_value.update(value)
                else:
                    setattr(self, field.name, value.copy())
            elif value != field.default:
                setattr(self, field.name, value)

    def bind(self, instance):
        """Bind the configuration object to an actual lab instance (lab, service or node)."""
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, Config):
                value.bind(instance)


@dataclass
class HealthCheck(DataclassConfig):
    """Config for defining a node's healthcheck parameters."""
    test: list[str] = None
    start_period: int = 0
    retries: int = 3
    interval: int = 30
    timeout: int = 30


class DependencyState(Enum):
    """States of nodes to match for a node dependency tree."""
    CREATE = "create"
    CREATE_LINKS = "create-links"
    CONFIGURE = "configure"
    HEALTHY = "healthy"
    EXIT = "exit"


@dataclass
class Dependency(DataclassConfig):
    """A dependency is a state that must be met on another node before a target node can be started."""
    name: str
    stage: DependencyState

    def __str__(self):
        return self.name


T = TypeVar("T")

class DictConfig(Config, UserDict[str, T]):
    """This config represents a list of node dependencies to be used for node startup."""
    def __init__(self, *data: T):
        """Initialize the `Dependencies` config for the list of Dependency objects."""
        self.data = {}
        self.accepted_type = typing.get_args(self.__class__.__orig_bases__[0])
        for item in data:
            self.add(item)

    def add(self, item: T):
        if not isinstance(item, self.accepted_type):
            raise ValueError(f"{self.__class__.__name__} only accepts items of type {self.accepted_type} but got {item.__class__}")
        item_name = str(item)
        if item_name in self.data:
            self.data[item_name].update(item)
        else:
            self.data[item_name] = item.copy()

    def copy(self) -> "DictConfig":
        """Produce a copy of the dependency list."""
        return self.__class__(*self.data.values())

    def update(self, other: "DictConfig"):
        """Update the dependencies with the provided value.
        
        This method will update matching dependencies by name, or will
        add new dependencies if they are not already existing.
        """
        if other is None:
            return

        for item in other.values():
            self.add(item)

    def bind(self, instance):
        item_names = list(self.keys())
        for item_name in item_names:
            item = self[item_name]
            if isinstance(item, Config):
                item.bind(instance)
                # item name could have changed
                new_item_name = str(item)
                if new_item_name != item_name:
                    self.pop(item_name)
                    self.add(item)

class Dependencies(DictConfig[Dependency]):
    """This config represents a list of node dependencies to be used for node startup."""


@dataclass
class Bind(DataclassConfig):
    mount_point: str
    read_only: bool

    def __str__(self):
        return self.mount_point

@dataclass
class FilesystemBind(Bind):
    local_path: str

    def __str__(self):
        ro = ":ro" if self.read_only else ""
        return f"{self.local_path}:{self.mount_point}{ro}"


def GlobBinds(mount_point: str, local_path: str, read_only: bool) -> List[FilesystemBind]:
    binds = []
    for filename in glob(local_path):
        binds.append(FilesystemBind(
            mount_point=path.join(mount_point, path.basename(filename)),
            local_path=filename,
            read_only=read_only,
        ))
    return binds


@dataclass(kw_only=True)
class NamedBind(FilesystemBind):
    name: str
    local_path: str = None
    read_only: bool = False

    def bind(self, instance: "Node"):
        super().bind(instance)
        self.local_path = path.join(instance.state_directory, self.name)


@dataclass(kw_only=True)
class StateBind(FilesystemBind):
    read_only: bool = False


class Binds(DictConfig[Bind]):
    """Collection of binds."""


@dataclass
class Link(DataclassConfig):
    interface: str
    to_device: str
    to_interface: str


class Links(DictConfig[Link]):
    pass


class Environment(UserDict[str, str], Config):
    def bind(self, instance):
        for key, value in self.items():
            self[key] = str(value).format(**self.data)

@dataclass
class Command(DataclassConfig):
    path: str
    interactive: bool = False
    log_errors: bool = True
    working_directory: str = None

@dataclass
class NodeConfig(DataclassConfig):
    image: str = None
    containerfile: str = None
    entrypoint: str = None
    health_check: HealthCheck = None
    dependencies: Dependencies = field(default_factory=Dependencies)
    ports: dict[str, str] = None
    binds: Binds = field(default_factory=Binds)
    networks: dict[str, str] = None
    environment: Environment = field(default_factory=Environment)
    links: Links = field(default_factory=Links)
    network_mode: str = "bridge"
    kind: str = None
    command: str = None
    mgmt_ipv4: str = None
    shell: Command = None
    cli: Command = None

class ServiceConfig(Config):
    node_names: List[str]
    environment: Environment

    def __init__(self, **children):
        self.environment = Environment()
        self.node_names = []
        for node_name, node_config in children.items():
            if not isinstance(node_config, NodeConfig):
                raise ValueError("Only node configs are accepted for service config arguments.")
            self.node_names.append(node_name)
            setattr(self, node_name, node_config)

    def copy(self) -> "ServiceConfig":
        arguments = {node_name: getattr(self, node_name).copy() for node_name in self.node_names}
        return ServiceConfig(**arguments)

    def update(self, other: "ServiceConfig"):
        if other is None:
            return

        for node_name in other.node_names:
            value = getattr(other, node_name)
            self_value = getattr(self, node_name, None)
            if self_value:
                self_value.update(value)
            else:
                setattr(self, node_name, value.copy())

    def bind(self, instance):
        for node_name in self.node_names:
            value = getattr(self, node_name)
            value.bind(instance)
