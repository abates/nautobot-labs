"""Golden config lab services."""
from lab_builder.lab import Service
from lab_builder.node import LinuxNode
from lab_builder.labs.common import CEOS

class Suzieq(LinuxNode):
    """Suzieq Poller Node."""
    name = "suzieq-poller"
    image = "netenglabs/suzieq:latest"
    entrypoint = "/usr/local/bin/sq-poller -I /home/suzieq/inventory.yml"

class SuzieqService(Service):
    """Lab service to start the suzieq service and analyzer."""
    nodes = {
        "suzieq": Suzieq,
    }

    binds = {
        "suzieq": [
            "suzieq:/home/suzieq/parquet",
        ],
    }

    def do_cli(self):
        """Start the SuzieQ CLI."""
        self.nodes["suzieq"].run_cmd("/usr/local/bin/suzieq-cli", working_directory="/home/suzieq", interactive=True)

class LeafSpineNetwork(Service):
    """A simple leaf/spine network of CEOS switches."""

    nodes = {
        "dc1-spine-1": CEOS,
        "dc1-spine-2": CEOS,
        "dc1-leaf-1": CEOS,
        "dc1-leaf-2": CEOS,
        "dc1-leaf-3": CEOS,
    }

    links = {
        "dc1-spine-1": {
            "eth1": "dc1-leaf-1:eth1",
            "eth2": "dc1-leaf-2:eth1",
            "eth3": "dc1-leaf-3:eth1",
        },
        "dc1-spine-2": {
            "eth1": "dc1-leaf-1:eth2",
            "eth2": "dc1-leaf-2:eth2",
            "eth3": "dc1-leaf-3:eth2",
        },
    }
