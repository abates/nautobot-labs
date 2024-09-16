"""This module provides the basic framework for lab definitions."""
from inspect import isclass
import os
import shutil
import typing

from lab_builder import config
from lab_builder.adapters import Adapter
from lab_builder.signal import DESTROYED, INITIALIZED, STARTED, STOPPED, emit

def command(method):
    """Decorator to indicate a method should be a command."""
    return method


class Node:
    service: "Service"
    node_config: config.NodeConfig

    def __init__(
            self,
            name: str,
            service: "Service",
            node_config,
        ):
        self.name = name
        self.service = service
        self.lab = service.lab
        self.node_config = node_config
        self.node_config.bind(self)

    def initialized(self):
        self.node_config.binds.add(config.StateBind(local_path=self.state_directory, mount_point="/lab_builder_data"))
        os.makedirs(self.state_directory, exist_ok=True)
        for bind in self.node_config.binds:
            if isinstance(bind, config.NamedBind):
                os.makedirs(os.path.join(self.state_directory, bind.name), exist_ok=True)
        container_file = self.node_config.containerfile
        image = self.node_config.image
        if container_file is None and image is None:
            raise ValueError(f"Either containerfile or image must be specified for {self.__class__.__name__}.")
        if not ((container_file is None) ^ (image is None)):
            raise ValueError(f"Both containerfile and image are set for {self.__class__.__name__}. Choose only one.")
        
        if container_file:
            container_file = os.path.join(self.definition_directory, container_file)
            self.image = f"lab_builder/{self.__class__.__name__.lower()}:latest"
            self.lab.adapter.build(container_file, tag=self.image)

    def started(self):
        pass

    def stopped(self):
        pass

    def destroyed(self):
        shutil.rmtree(self.state_directory)

    @property
    def state_directory(self):
        return os.path.join(os.path.abspath(self.service.state_directory), self.name)


class NetworkNode(Node):
    """A containerlab network device node."""

class LinuxNode(Node):
    """A container lab linux node."""
    node_config = config.NodeConfig(
        kind = "linux"
    )

    def list_dir(self, path):
        """Retrieve the contents of a path within a node.

        Args:
            path (str): The directory path to list

        Returns:
            list[str]: The contents of the node's directory
        """
        output = self.lab.adapter.exec(self, config.Command(["ls", path], log_errors=False))
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
        output = self.lab.adapter.exec(self, config.Command(["ls", path]))
        return output["return-code"] == 0

def _merge_config(cls: type, attr_name, config) -> config.Config:
    ancestry = cls.mro()
    ancestry.reverse()
    # remove the top-level `object`
    ancestry.pop(0)
    for ancestor in ancestry:
        value = getattr(ancestor, attr_name, None)
        if value:
            config.update(value)
    return config

class Service:
    """A Service is a collection of related nodes."""
    name: str
    lab: "Lab"
    children: typing.List[Node]

    def __init__(self, name, lab, service_config: config.ServiceConfig=None):
        if service_config is None:
            service_config = config.ServiceConfig()
        self.name = name
        self.lab = lab
        self.children = []
        service_config.bind(self)
        annotations = typing.get_type_hints(self.__class__)
        # setup service environment
        self.environment = _merge_config(self.__class__, "environment", config.Environment())
        self.environment.update(service_config.environment)

        for node_name, node_type in annotations.items():
            if isclass(node_type) and issubclass(node_type, Node):
                # Get base node config from node's class attributes
                if hasattr(node_type, "node_config"):
                    node_config: config.NodeConfig = _merge_config(node_type, "node_config", config.NodeConfig())
                else:
                    node_config = config.NodeConfig()
                node_config.environment.update(self.environment)

                # Merge base config with anything provided in the local
                # service config
                if hasattr(self.__class__, node_name):
                    node_config.update(getattr(self.__class__, node_name))

                # Merge with overrides
                if hasattr(service_config, node_name):
                    node_config.update(getattr(service_config, node_name))

                setattr(self, node_name, node_type(name=node_name, service=self, node_config=node_config))
                node = getattr(self, node_name)
                emit(INITIALIZED, node)
                self.children.append(node)
        emit(INITIALIZED, self)

    def resolve_environment(self, environment):
        """Format any templat strings contained in the given environment."""
        service_environment = {
            **getattr(self, "shared_environment", {}),
            **environment,
        }
        for key, value in service_environment.items():
            if isinstance(value, str):
                service_environment[key] = value.format(**service_environment)
        return service_environment

    @property
    def state_directory(self):
        return os.path.join(os.path.abspath(self.lab.state_directory), self.name)

    def initialized(self):
        os.makedirs(self.state_directory, exist_ok=True)

class Lab:
    """A lab is a collection of services."""

    name: str = "Basic Lab"
    description: str = "A Simple lab with nothing in it."
    children: typing.List[Service]

    def __init__(self, adapter: Adapter, base_dir):
        self.adapter = adapter
        self.base_dir = base_dir
        self.children = []
        annotations = typing.get_type_hints(self)
        for service_name, service_type in annotations.items():
            if issubclass(service_type, Service):
                service_config = config.ServiceConfig()
                if hasattr(self.__class__, service_name):
                    service_config = _merge_config(self.__class__, service_name, config.ServiceConfig())
                setattr(self, service_name, service_type(name=service_name, lab=self, service_config=service_config))
                service = getattr(self, service_name)
                emit(INITIALIZED, service)
                self.children.append(service)
        emit(INITIALIZED, self)

    @property
    def commands(self):
        """Get a list of commands that the definition provides.
        
        Any method starting with `do_` is considered a command that is
        provided to the lab CLI for user interaction. This method
        finds those methods and returns their names. This is mostly used
        for tab-completion.
        """
        members = []
        for name, _ in inspect.getmembers(self.__class__):
            if name.startswith("do_") and inspect.ismethod(getattr(self, name)):
                members.append(name.removeprefix("do_"))
        return members

    def get_command(self, commands: list[str]):
        if len(commands) == 0:
            return None
        if commands[0] in self.children:
            return self.children[commands[0]].get_command(commands[1:])
        if hasattr(self, f"do_{commands[0]}"):
            return (getattr(self, f"do_{commands[0]}"), commands[1:])
        raise Exception(f"Unknown command {commands[0]}")

    def complete(self, commands: list[str], command: str, text: str):
        """Perform the tab-completion.

        Args:
            commands (list[str]): commands split from the command line by spaces.
            command (str): The trailing command, to be looked up.
            text (str): The completion text.

        Returns:
            list[str]: List of possible completions
        """
        if len(commands) > 0:
            if hasattr(self, f"do_{commands[0]}"):
                if hasattr(self, f"complete_{commands[0]}"):
                    return getattr(self, f"complete_{commands[0]}")(commands[1:], command, text)
                return []
            if commands[0] in self.services:
                return self.services[commands[0]].complete(commands[1:], command, text)
        children = [child for child in self.services.keys()]
        return [text + match[len(command):] for match in [*self.commands, *children] if match.startswith(command)]


    def start(self):
        """Start the current lab."""

    @property
    def state_directory(self):
        """Get the labs's state directory.
        
        Each component (lab, service and node) in a lab is assigned an
        ephemeral directory, this property will return the absolute path
        to the lab's assigned state directory.
        """
        return os.path.join(os.path.abspath(self.base_dir), self.name)

    @property
    def nodes(self):
        """Retrieve all of the nodes in the lab.

        The `nodes` property is a generator that yields
        nodes from the combined services of the lab.

        Yields:
            Node: Nodes belonging to services in the lab.
        """
        for service in self.children:
            yield from service.children
