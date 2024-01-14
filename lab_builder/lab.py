
import json
import os
import shutil
import subprocess

from lab_builder.node import ApplicationNode

class Application:
    """An application is a collection of related nodes.
    
    An application is (usually) a collection of related containers for delivering
    some application or service. For instance, Nautobot requires an application
    instance, a database and a message queue (minimum). It may also include
    a worker instance and scheduler. All of these containers are required
    to deliver the Nautobot application.

    When an application is created all the nodes will be on the same network.
    """
    nodes: list[ApplicationNode]
    dependencies: dict[str, dict[str, str]]
    networks: dict[str, list[str]]

    def __init__(self, lab):
        self.lab = lab
        self.nodes = []
        for node_class, config in self.__class__.nodes.items():
            self.nodes.append(
                node_class(
                    lab=lab,
                    application=self,
                    **config,
                )
            )

    @property
    def resolved_environment(self):
        environment = {**getattr(self, "environment", {})}
        for key, value in environment.items():
            if isinstance(value, str):
                environment[key] = value.format(**environment)
        return environment
    
    @property
    def network_name(self):
        return f"{self.lab.name}_{self.name}".lower()


class Lab:
    name: str = "Lab"
    description: str = "A Simple lab with nothing in it."
    applications: list[Application]

    def __init__(self):
        applications: list[Application] = []
        for application in self.__class__.applications:
            applications.append(application(self))
        self.applications = applications

    def _run_cmd(self, *cmd, **process_kwargs):
        process_kwargs["stdout"] = subprocess.PIPE
        if "input" in process_kwargs:
            if process_kwargs["input"] is not None:
                process_kwargs["text"] = True
            else:
                process_kwargs.pop("input")
        return subprocess.run(cmd, **process_kwargs)


    def _run_docker_cmd(self, *args, input=None):
        cmd = [
            "sudo",
            "docker",
            *args,
        ]
        return self._run_cmd(*cmd, input=input)

    def _run_clab_cmd(self, *args, input=None):
        cmd = [
            "sudo",
            "-E",
            shutil.which("containerlab"),
            *args,
        ]
        env = {
            "CLAB_LABDIR_BASE": self.lab_dir,
        }
        return self._run_cmd(*cmd, input=input, env=env)

    def start(self):
        try:
            os.mkdir(self.lab_dir)
        except FileExistsError:
            pass
        
        cmd = ["deploy", "--topo", self.topology_file]
        reconfigure = self.needs_reconfigure
        if reconfigure:
            cmd.extend(["--reconfigure"])

        if reconfigure or not os.path.exists(self.topology_file):
            with open(self.topology_file, "w") as file:
                file.write(self.topology_str)

        self._run_clab_cmd(*cmd)

    def stop(self):
        topology = self.inspect().get("topology_file", None)
        if topology:
            self._run_clab_cmd("--topo", topology, "destroy", "--graceful")

        # for bridge in self.application_bridges:
        #     self._run_docker_cmd(
        #         "network",
        #         "remove",
        #         bridge,
        #     )

    def inspect(self) -> dict:
        proc = self._run_clab_cmd(
            "inspect",
            "--name",
            self.name,
            "--format",
            "json",
        )
        if proc.stdout:
            stdout = json.loads(proc.stdout)
            if stdout["containers"]:
                stdout["topology_file"] = stdout["containers"][0]["labPath"]
            return stdout
        return {}

    @property
    def lab_dir(self):
        return os.path.join(os.path.abspath(os.getcwd()), f"lab-builder-{self.name.lower()}")

    @property
    def topology_file(self):
        return os.path.join(self.lab_dir, f"{self.name.lower()}.json")

    @property
    def running(self):
        containers = self.inspect().get("containers", [])
        return len(containers) > 0

    @property
    def needs_reconfigure(self):
        if os.path.exists(self.topology_file):
            with open(self.topology_file) as topology_file:
                existing_topology = topology_file.read()
                return existing_topology != self.topology_str
        return False

    @property
    def application_bridges(self):
        return [f"br-{application.network_name}" for application in self.applications]

    # @property
    # def bridge_ids(self):
    #     bridges: dict[str, str] = {}
    #     proc = self._run_docker_cmd(
    #         "network",
    #         "ls",
    #         "--format",
    #         "json",
    #     )
    #     for line in proc.stdout.splitlines():
    #         network = json.loads(line)
    #         bridges[network["Name"]] = f"br-{network['ID'][0:12]}"
    #     return bridges

    @property
    def topology_str(self):
        return json.dumps(self.topology, indent=2)

    @property
    def topology(self):
        nodes = {}
        links = []
        # bridges = self.bridge_ids
        for application in self.applications:
            environment = application.resolved_environment
            # bridge_name = bridges[f"br-{application.network_name}"]
            # nodes[bridge_name] = {
            #     "kind": "bridge",
            # }
            for node in application.nodes:
                nodes[node.name] = node.as_dict()
                if environment:
                    nodes[node.name]["env"] = environment
                # links.append({
                #     "endpoints": [
                #         f"{node.name}:eth0",
                #         f"{bridge_name}:eth{i}",
                #     ],
                # })

        return {
            "name": self.name,
            "topology": {
              "nodes": nodes,
              "links": links,
            }
        }
