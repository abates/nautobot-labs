"""This module provides the basic framework for lab definitions."""
import glob
import inspect
import json
import os
import shutil
import subprocess
from types import NoneType
import typing

import cmd2

if typing.TYPE_CHECKING:
    from lab_builder.node import Node, Dependency, Service


class Definition:
    """Definition is a top-level lab configuration/definition class."""

    def __init__(
            self,
            name: str,
            parent: "Definition" = None,
            base_dir: str = None,
            **kwargs,
        ):
        """Initialize a definition.

        Args:
            name (str): Name of the definition. This could be a lab name, service name
                        or node name.
            parent (Definition, optional): The parent definition to which this belongs.
            base_dir (str, optional): The base directory to use for storing state. Defaults to None.

        Raises:
            TypeError: Raise if an unknown keyword argument has been provided.
        """
        self.name = name
        self.parent = parent
        type_hints = {}
        self.base_dir = base_dir
        if self.base_dir is None:
            self.base_dir = os.getcwd()
        for _class in reversed(self.__class__.__mro__):
            type_hints.update(typing.get_type_hints(_class))

        for attr_name, type_hint in type_hints.items():
            attr_value = kwargs.pop(attr_name, None)
            if (
                getattr(self, attr_name, None) is None
                or getattr(self, attr_name) is getattr(self.__class__, attr_name, None)
            ):
                setattr(self, attr_name, type_hint())
            
            self._update_attribute(attr_name, attr_value)

            # Reverse the MRO so that we always start
            # from the top most level first. This allows
            # Layers that extend a layer to do overrides
            for _class in reversed(self.__class__.__mro__):
                if hasattr(_class, attr_name):
                    self._update_attribute(attr_name, getattr(_class, attr_name))
        keys = list(kwargs.keys())

        if keys:
            raise TypeError(f"{self.__class__.__name__}.__init__() got an unexpected keyword argument '{keys[0]}'")

    def _resolve_binds(self, binds):
        """Resolve compute absolute paths for the local directory in a list of binds.

        The input binds can have the following formats:
            * absolute - An absolute path is not changed, however if the path itself
            is not within the layer's state directory, then the bind is marked read-only

            * relative - A bind can be relative if the local part begins with `./`. The
            bind is then joined with the layer's definition directory and marked read-only.

            * named - A bind that is neither relative nor absolute is considered "named". The
            named bind will be rooted in the layer's state directory and will be read-write.

        Args:
            layer (Layer): The layer where the binds need to be calculated
            binds (list[str]): The list of volume binds (in `local:remote` format)

        Returns:
            list[str]: A copy of the original list where the local side of each bind
            has been converted to an absolute path.
        """
        resolved_binds = []
        if binds:
            for bind in binds:
                read_only = ""
                if bind.endswith(":ro"):
                    bind = bind[:-3]
                    read_only = ":ro"
                local, remote = bind.split(":", 1)
                if not os.path.isabs(local):
                    # If the local path starts with a ./ then treat
                    # it as a local path, otherwise treat it as a
                    # "named" path and put it in the corresponding
                    # node directory
                    if local.startswith("./"):
                        local = os.path.join(self.definition_directory, local[2:])
                        read_only = ":ro"
                    else:
                        local = os.path.join(self.state_directory, local)
                        # the local path won't match the glob, since this
                        # directory hasn't been created yet, so just add it
                        # and let later handlers create the directory
                        resolved_binds.append(f"{local}:{remote}")
                elif not local.startswith(self.state_directory):
                    read_only = ":ro"
                
                matches = glob.glob(local)
                if len(matches) == 1 and matches[0] == local:
                    resolved_binds.append(f"{local}:{remote}{read_only}")
                else:
                    for match in matches:
                        match_remote = os.path.join(remote, os.path.basename(match))
                        resolved_binds.append(f"{match}:{match_remote}{read_only}")
        return resolved_binds

    def _update_attribute(self, attr_name: str, value: typing.Union[dict, list, NoneType]):
        """Update a layer instance's config attribute.

        This method examine's the class hierarchy's type hinting
        and will initialize a config attribute instance to the proper
        type and will then update the attribute based on the input
        value.

        Args:
            attr_name (str): The layer's config attribute to update.
            value (typing.Union[dict, list, NoneType]): The value that should be updated
            into the layer attribute.

        Raises:
            ValueError: If the input value type does not match the attribute value type.
        """
        if value is None:
            return

        self_value = getattr(self, attr_name)

        if type(self_value) != type(value):
            raise ValueError(f"{attr_name}: Mismatch type {type(self_value)} != {type(value)}")

        if hasattr(self_value, "update"):
            self_value.update(value)
        elif hasattr(self_value, "extend"):
            self_value.extend(value)
        else:
            setattr(self, attr_name, value)

    def _emit(self, signal):
        for child in self.children.values():
            getattr(child, signal)()

    @property
    def children(self) -> dict[str, typing.Any]:
        """Get the children of this layer."""
        return {}

    @property
    def commands(self):
        """Get a list of commands that the definition provides.
        
        Any method starting with `do_` is considered a command that is
        provided to the lab CLI for user interaction. This method
        finds those methods and returns their names. This is mostly used
        for tab-completion.
        """
        members = []
        for name, member in inspect.getmembers(self.__class__):
            if name.startswith("do_") and inspect.ismethod(getattr(self, name)):
                members.append(name.removeprefix("do_"))
        return members

    def complete(self, commands: list[str], command: str, text: str):
        if len(commands) > 0:
            if hasattr(self, f"do_{commands[0]}"):
                if hasattr(self, f"complete_{commands[0]}"):
                    return getattr(self, f"complete_{commands[0]}")(commands[1:], command, text)
                return []
            if commands[0] in self.children:
                return self.children[commands[0]].complete(commands[1:], command, text)
        children = [child for child in self.children.keys()]
        # print(self, "POSSIBLE: ", [*self.commands, *children])
        return [text + match[len(command):] for match in [*self.commands, *children] if match.startswith(command)]

    def created(self):
        """Create this layer's directory and then signal."""
        self._emit("created")

    @property
    def definition_directory(self):
        """Get the directory where the class definition is located."""
        return os.path.dirname(inspect.getfile(self.__class__))

    def destroyed(self):
        """Signal all of the children of this layer that the layer has been destroyed."""
        self._emit("stopped")
        shutil.rmtree(self.state_directory)

    @property
    def lab(self) -> "Lab":
        """The `lab` is the top most layer."""
        if self.parent is None:
            return self
        return self.parent.lab

    def start(self):
        try:
            os.mkdir(self.state_directory)
        except FileExistsError:
            pass
        for child in self.children.values():
            child.start()

    def started(self):
        """Signal all of the children of this layer that the layer has started."""
        self._emit("started")

    @property
    def state_directory(self):
        """Get the layer's directory.
        
        Each layer is assigned an ephemeral directory, this property will
        return the absolute path to the current layer's directory.
        """
        if self.parent is None:
            return os.path.join(os.path.abspath(self.base_dir), self.name)
        return os.path.join(self.parent.state_directory, self.name)

    def stopped(self):
        """Signal all of the children of this layer that the layer has stopped."""
        self._emit("stopped")

class Layer(Definition):
    dependencies: dict[str, "Dependency"]
    # TODO: Convert the value to a formal class/model
    binds: dict[str, str]
    ports: dict[str, str]
    environment: dict[str, str]
    shared_environment: dict[str, str]
    # TODO: Convert this to a formal class/model
    links: dict[str, dict[str, str]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for node_name, node_binds in self.binds.items():
            self.binds[node_name] = self._resolve_binds(node_binds)

class Service(Layer):
    """A Service is a collection of related nodes."""

    nodes: dict[str, "Node"]

    @property
    def children(self) -> dict[str, "Node"]:
        return self.nodes

    def created(self):
        nodes = self.nodes
        self.nodes = {}
        for node_name, node in nodes.items():
            extra_kwargs = {}
            for varname in ["dependencies", "binds", "ports", "environment", "links"]:
                extra_kwargs[varname] = getattr(self, varname, {}).get(node_name, None)

            self.nodes[node_name] = node(
                name=node_name,
                parent=self,
                **extra_kwargs,
            )
        super().created()

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


class Lab(Layer):
    name: str = "Basic Lab"
    description: str = "A Simple lab with nothing in it."
    services: dict[str, Service]

    def __init__(self, base_dir=None):
        super().__init__(self.__class__.name, base_dir=base_dir)
        self.services = {}

        for service_name, service_class in getattr(self.__class__, "services", {}).items():
            dependencies = getattr(self, "dependencies", None)
            binds = getattr(self.__class__, "binds", None)
            links = getattr(self.__class__, "links", None)
            service = service_class(
                name=service_name,
                parent=self,
                dependencies=dependencies,
                binds=binds,
                links=links,
            )
            self.services[service_name] = service
        self.created()

    def run_cmd(self, cmd: list[str], **process_kwargs) -> subprocess.CompletedProcess:
        """Run a command using `subprocess.run`.

        Args:
            cmd (list[str]): The command to run. The command itself should be the first item
                in the list, and the command's arguments should be the remaining items.

        Returns:
            subprocess.CompletedProcess: The result of the command's execution.
        """
        process_kwargs["stdout"] = subprocess.PIPE
        if "cmd_input" in process_kwargs:
            if process_kwargs["cmd_input"] is not None:
                process_kwargs["input"] = process_kwargs.pop("cmd_input")
                process_kwargs["text"] = True
            else:
                process_kwargs.pop("cmd_input")
        return subprocess.run(cmd, check=True, **process_kwargs)


    def run_clab_cmd(self, cmd: list[str], cmd_input=None) -> subprocess.CompletedProcess:
        """Run a containerlab sub-command.

        This method will execute `sudo -E containerlab ...` with the given command
        argumnets.

        Args:
            cmd (list[str]): The command (first item) and its arguments to provide to
                to the `containerlab` executable.
            cmd_input (str, optional): Any input to provide to the processes `stdin.
                Defaults to None.

        Returns:
            subprocess.CompletedProcess: The result of the command/process completion.
        """
        cmd = [
            "sudo",
            "-E",
            shutil.which("containerlab"),
            *cmd,
        ]
        env = {
            "CLAB_LABDIR_BASE": self.state_directory,
        }
        return self.run_cmd(cmd, cmd_input=cmd_input, env=env)

    def start(self):
        """Start the current lab."""
        super().start()
        cmd = ["deploy", "--topo", self.topology_file]
        reconfigure = self.needs_reconfigure
        if reconfigure:
            cmd.extend(["--reconfigure"])

        if reconfigure or not os.path.exists(self.topology_file):
            with open(self.topology_file, "w", encoding="utf-8") as file:
                file.write(self.topology_str)

        if reconfigure or not self.running:
            print("Starting", self.lab.name)
            self.run_clab_cmd(cmd)
            self.started()
        else:
            print(self.lab.name, "is already running")

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
        return os.path.join(self.state_directory, f"{self.name.lower()}.json")

    @property
    def running(self):
        """Determine if all of the nodes of this lab are running."""
        running_containers = set(self.running_containers)
        for node in self.nodes:
            if node.name not in running_containers:
                return False
        return True

    @property
    def running_containers(self):
        """Get a list of container names that are currently running for this lab."""
        containers = []
        for container in self.inspect().get("containers", []):
            # remove clab- and lab name
            name = container["name"][6+len(container["lab_name"]):]
            containers.append(name)
        return containers

    @property
    def needs_reconfigure(self):
        """Determine if the lab needs to be reconfigured."""
        if os.path.exists(self.topology_file):
            with open(self.topology_file, encoding="utf-8") as topology_file:
                existing_topology = topology_file.read()
                if existing_topology != self.topology_str:
                    return True
        return False

    @property
    def children(self) -> dict[str, typing.Any]:
        return self.services

    @property
    def nodes(self):
        """Retrieve all of the nodes in the lab.

        The `nodes` property is a generator that yields
        nodes from the combined services of the lab.

        Yields:
            Node: Nodes belonging to services in the lab.
        """
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
        for node in self.nodes:
            for interface_name, connection in node.links.items():
                links.append({
                    "endpoints": [f"{node.name}:{interface_name}", connection],
                })

        return {
            "name": self.name,
            "topology": {
              "nodes": {node.name: node.as_dict() for node in self.nodes},
              "links": links,
            }
        }
