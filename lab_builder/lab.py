
from abc import ABC, abstractmethod
import json
import os
import shutil
import subprocess
import typing

from lab_builder.util import resolve_attribute, resolve_binds

if typing.TYPE_CHECKING:
    from lab_builder.node import Node


class Layer(ABC):
    def __init__(
            self,
            name: str,
            parent: "Layer" = None,
            dependencies: dict = None,
            binds: dict = None,
            ports: dict = None,
        ):
        self.name = name
        self.parent = parent
        self.dependencies = resolve_attribute(self.__class__, "dependencies", dependencies or {})
        self.ports = resolve_attribute(self.__class__, "ports", ports or {})
        self.binds = resolve_attribute(self.__class__, "binds", binds or {})
        for node_name, node_binds in self.binds.items():
            self.binds[node_name] = resolve_binds(self, node_binds)

    def _emit(self, signal):
        for child in self.children:
            getattr(child, signal)()

    @property
    @abstractmethod
    def children(self):
        """Get the children of this layer."""

    @property
    def lab(self):
        """The `lab` is the top most layer."""
        if self.parent is None:
            return self
        return self.parent.lab

    @property
    def directory(self):
        """Get the layer's directory.
        
        Each layer is assigned an ephemeral directory, this property will
        return the absolute path to the current layer's directory.
        """
        if self.parent is None:
            return os.path.join(os.path.abspath(os.getcwd()), self.name)
        return os.path.join(self.parent.directory, self.name)

    def created(self):
        """Create this layer's directory and then signal."""
        try:
            os.mkdir(self.directory)
        except FileExistsError:
            pass
        self._emit("created")

    def started(self):
        """Signal all of the children of this layer that the layer has started."""
        self._emit("started")

    def stopped(self):
        """Signal all of the children of this layer that the layer has stopped."""
        self._emit("stopped")

    def destroyed(self):
        """Signal all of the children of this layer that the layer has been destroyed."""
        self._emit("stopped")
        shutil.rmtree(self.directory)

class Service(Layer):
    """A Service is a collection of related nodes."""

    name: str
    lab: "Lab"
    nodes: dict[str, "Node"]

    @property
    def children(self):
        return self.nodes.values()

    def created(self):
        self.nodes = {}
        nodes = resolve_attribute(self.__class__, "nodes", {})
        for node_name, node in nodes.items():
            extra_kwargs = {}
            for varname in ["dependencies", "binds", "ports"]:
                extra_kwargs[varname] = getattr(self, varname).get(node_name, None)

            self.nodes[node_name] = node(
                name=node_name,
                service=self,
                **extra_kwargs,
            )
        super().created()

    def resolve_environment(self, environment):
        """Format any templat strings contained in the given environment."""
        service_environment = {
            **getattr(self, "environment", {}),
            **environment,
        }
        for key, value in environment.items():
            if isinstance(value, str):
                environment[key] = value.format(**service_environment)
        return environment

    @property
    def default_environment(self):
        """The default environment is the service class's environment."""
        return self.resolve_environment(getattr(self, "environment", {}))


class Lab(Layer):
    name: str = "Basic Lab"
    description: str = "A Simple lab with nothing in it."
    services: dict[str, Service]

    def __init__(self):
        super().__init__(name=self.__class__.name)
        self.services = {}

        for service_name, service_class in getattr(self.__class__, "services", {}).items():
            dependencies = getattr(self, "dependencies", None)
            binds = getattr(self.__class__, "binds", None)
            service = service_class(
                name=service_name,
                parent=self,
                dependencies=dependencies,
                binds=binds,
            )
            self.services[service_name] = service
        self.created()

    def _run_cmd(self, cmd, **process_kwargs):
        process_kwargs["stdout"] = subprocess.PIPE
        if "cmd_input" in process_kwargs:
            if process_kwargs["cmd_input"] is not None:
                process_kwargs["input"] = process_kwargs.pop("cmd_input")
                process_kwargs["text"] = True
            else:
                process_kwargs.pop("cmd_input")
        return subprocess.run(cmd, check=True, **process_kwargs)


    def run_clab_cmd(self, cmd, cmd_input=None):
        cmd = [
            "sudo",
            "-E",
            shutil.which("containerlab"),
            *cmd,
        ]
        env = {
            "CLAB_LABDIR_BASE": self.directory,
        }
        return self._run_cmd(cmd, cmd_input=cmd_input, env=env)

    def start(self):
        """Start the current lab."""
        cmd = ["deploy", "--topo", self.topology_file]
        reconfigure = self.needs_reconfigure
        if reconfigure:
            cmd.extend(["--reconfigure"])

        if reconfigure or not os.path.exists(self.topology_file):
            with open(self.topology_file, "w", encoding="utf-8") as file:
                file.write(self.topology_str)

        self.run_clab_cmd(cmd)
        self.started()

    def stop(self):
        """If running, stop the current lab."""
        if self.running:
            topology = self.inspect().get("topology_file", None)
            if topology:
                self.run_clab_cmd(["--topo", topology, "destroy", "--graceful"])
        self.stopped()

    def destroy(self):
        self.destroyed()

    def inspect(self) -> dict:
        """Run the containerlab inspect command and return the parsed result."""
        proc = self.run_clab_cmd([
            "inspect",
            "--name",
            self.name,
            "--format",
            "json",
        ])
        if proc.stdout:
            stdout = json.loads(proc.stdout)
            if stdout["containers"]:
                stdout["topology_file"] = stdout["containers"][0]["labPath"]
            return stdout
        return {}

    @property
    def topology_file(self):
        """Get the path to the lab's topology file."""
        return os.path.join(self.directory, f"{self.name.lower()}.json")

    @property
    def running(self):
        """Determine if any part of this lab is currently running."""
        return len(self.running_containers) > 0

    @property
    def running_containers(self):
        """Get a list of container names that are currently running for this lab."""
        containers = []
        for container in self.inspect().get("containers", []):
            # remove clab- and lab name
            name = container["name"][5+len(container["lab_name"]):]
            containers.append(name)
        return containers

    @property
    def needs_reconfigure(self):
        """Determine if the lab needs to be reconfigured."""
        if os.path.exists(self.topology_file):
            with open(self.topology_file, encoding="utf-8") as topology_file:
                existing_topology = topology_file.read()
                if existing_topology == self.topology_str:
                    return True
                running_containers = set(self.running_containers)
                for node in self.nodes:
                    if node.name not in running_containers:
                        return True
        return False

    @property
    def children(self):
        return self.services.values()

    @property
    def nodes(self):
        for service in self.services.values():
            yield from service.nodes.values()

    @property
    def topology_str(self):
        """Get a string representation of the containerlab topology for this lab."""
        return json.dumps(self.topology, indent=2)

    @property
    def topology(self):
        """Generate the containerlab topology for this lab."""
        links = []

        return {
            "name": self.name,
            "topology": {
              "nodes": {node.name: node.as_dict() for node in self.nodes},
              "links": links,
            }
        }
