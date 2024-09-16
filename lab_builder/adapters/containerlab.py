
import json
import os
import shlex
import shutil
import subprocess
import sys

from lab_builder.adapters import Adapter
from lab_builder.lab import Lab, Node
from lab_builder import config, signal

def _remove_none(data: dict):
    keys = list(data.keys())
    for key in keys:
        value = data[key]
        if isinstance(value, dict):
            _remove_none(value)
            if len(value) == 0:
                value = None
        if isinstance(value, list) and len(value) == 0:
            value = None
        
        if value is None:
            data.pop(key)

        
def _node_topology(node: Node):
    node_config = node.node_config

    health_check = {}
    if node_config.health_check:
        health_check = {
            "test": node_config.health_check.test,
            "start-period": node_config.health_check.start_period,
            "retries": node_config.health_check.retries,
            "interval": node_config.health_check.interval,
            "timeout": node_config.health_check.timeout,
        }

    stages = {}
    if node_config.dependencies:
        dependencies = []
        for dependency in node_config.dependencies.values():
            dependencies.append({"node": dependency.name, "stage": dependency.stage.value})
        stages = {
            "create": {
                "wait-for": dependencies,
            }
        }

    topology = {
        "kind": node_config.kind,
        "image": node_config.image,
        "entrypoint": node_config.entrypoint,
        "healthcheck": health_check,
        "network-mode": node_config.network_mode,
        "mgmt-ipv4": node_config.mgmt_ipv4,
        "stages": stages,
        "cmd": node_config.command,
        "binds": [str(bind) for bind in node_config.binds],
        "ports": node_config.ports,
        "env": {key: value for key, value in node_config.environment.items()},
    }
    _remove_none(topology)
    return topology


class Containerlab(Adapter):
    def start(self, lab: Lab):
        signal.emit(signal.START, lab)
        cmd = ["deploy", "--topo", self.topology_file(lab)]
        reconfigure = (
            self.needs_reconfigure(lab) or
            (not self.running(lab) and self.containers(lab))
        )
        if reconfigure:
            cmd.extend(["--reconfigure"])

        if reconfigure or not os.path.exists(self.topology_file(lab)):
            with open(self.topology_file(lab), "w", encoding="utf-8") as file:
                file.write(self.topology_str(lab))

        if reconfigure or not self.running(lab):
            print("Starting", lab.name)
            self._run_clab_cmd(lab, cmd)
            signal.emit(signal.STARTED, lab)
        else:
            print(lab.name, "is already running")

    def stop(self, lab: Lab):
        if self.running(lab):
            signal.emit(signal.STOP, lab)
            topology = self.inspect(lab).get("topology_file", None)
            if topology:
                self._run_clab_cmd(lab, ["--topo", topology, "destroy", "--graceful"])
                signal.emit(signal.STOPPED, lab)

    def destroy(self, lab: Lab):
        signal.emit(signal.DESTROY, lab)


    def build(self, lab: Lab, container_file, tag=None):
        cmd = [
            "docker",
            "image",
            "build",
        ]

        if tag:
            cmd.extend(["--tag", tag])

        cmd.extend([
            "--file",
            container_file,
            os.path.dirname(container_file),
        ])

        self._run_cmd(cmd)

    def exec(self, node: Node, command: config.Command):
        cmd = command.path
        if isinstance(cmd, str):
            cmd = [cmd]
        shell_command = shlex.join(cmd)

        if command.interactive:
            cmd = [
                "exec",
                "-it",
            ]
            if command.working_directory:
                cmd.extend(["-w", command.working_directory])
            cmd.extend([
                f"clab-{node.lab.name}-{node.name}",
                shell_command,
            ])
            self._run_docker_cmd(node.lab, cmd, stdout=sys.stdout)
            return None

        if command.working_directory:
            shell_command = " ".join([
                "sh",
                "-c",
                shlex.quote(" ".join(["cd", command.working_directory, "&&", shell_command])),
            ])

        cmd = [
            "exec",
            "--label", f"clab-node-name={node.name}",
            "--format", "json",
            "--cmd", shell_command,
        ]
        process = self._run_clab_cmd(node.lab, cmd)
        output = json.loads(process.stdout)
        output = next(iter(output.values())).pop()
        if output["return-code"] != 0 and command.log_errors:
            print(f"{node.name} Command Failed:", shell_command, file=sys.stderr)
            print(output["stderr"], file=sys.stderr)
            print(output["stdout"], file=sys.stderr)
        return output

    def _run_cmd(self, cmd: list[str], **process_kwargs) -> subprocess.CompletedProcess:
        """Run a command using `subprocess.run`.

        Args:
            cmd (list[str]): The command to run. The command itself should be the first item
                in the list, and the command's arguments should be the remaining items.

        Returns:
            subprocess.CompletedProcess: The result of the command's execution.
        """
        process_kwargs.setdefault("stdout", subprocess.PIPE)
        if "cmd_input" in process_kwargs:
            if process_kwargs["cmd_input"] is not None:
                process_kwargs["input"] = process_kwargs.pop("cmd_input")
                process_kwargs["text"] = True
            else:
                process_kwargs.pop("cmd_input")
        return subprocess.run(cmd, check=True, **process_kwargs)


    def _run_clab_cmd(self, lab: Lab, cmd: list[str], cmd_input=None) -> subprocess.CompletedProcess:
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
            "CLAB_LABDIR_BASE": lab.state_directory,
        }
        return self._run_cmd(cmd, cmd_input=cmd_input, env=env)

    def _run_docker_cmd(self, lab: Lab, cmd: list[str], **process_kwargs) -> subprocess.CompletedProcess:
        """Run a command using the docker utility."""
        cmd = [
            shutil.which("docker"),
            *cmd,
        ]
        return self._run_cmd(cmd, **process_kwargs)

    def inspect(self, lab: Lab) -> dict:
        """Run the containerlab inspect command and return the parsed result."""
        proc = self._run_clab_cmd(lab, [
            "inspect",
            "--name",
            lab.name,
            "--format",
            "json",
        ])
        if proc.stdout:
            stdout = json.loads(proc.stdout)
            if stdout["containers"]:
                stdout["topology_file"] = stdout["containers"][0]["labPath"]
            return stdout
        return {}

    def topology_file(self, lab: Lab):
        """Get the path to the lab's topology file."""
        return os.path.join(lab.state_directory, f"{lab.name.lower()}.json")

    def running(self, lab: Lab):
        """Determine if all of the nodes of this lab are running."""
        running_containers = set(self.containers(lab))
        for node in lab.nodes:
            if node.name not in running_containers:
                return False
        return True

    def containers(self, lab: Lab):
        """Get a list of containers that are currently running for this lab."""
        containers = []
        for container in self.inspect(lab).get("containers", []):
            # remove clab- and lab name
            name = container["name"][6+len(container["lab_name"]):]
            containers.append(name)
        return containers

    def needs_reconfigure(self, lab: Lab):
        """Determine if the lab needs to be reconfigured."""
        if os.path.exists(self.topology_file(lab)):
            with open(self.topology_file(lab), encoding="utf-8") as topology_file:
                existing_topology = topology_file.read()
                if existing_topology != self.topology_str(lab):
                    return True
        return False

    def topology_str(self, lab: Lab):
        """Get a string representation of the containerlab topology for this lab."""
        return json.dumps(self.topology(lab), indent=2)

    def topology(self, lab: Lab):
        """Generate the containerlab topology for this lab."""
        links = []
        for node in lab.nodes:
            for link in node.node_config.links:
                links.append({
                    "endpoints": [f"{node.name}:{link.interface}", f"{link.to_device}:{link.to_interface}"],
                })

        topology = {
            "name": lab.name,
            "topology": {
              "nodes": {node.name: _node_topology(node) for node in lab.nodes},
              "links": links,
            }
        }
        if getattr(lab, "ipv4_subnet", None):
            topology["mgmt"] = {
                "network": "custom_mgmt",
                "ipv4-subnet": getattr(lab, "ipv4_subnet"),
            }
        return topology
