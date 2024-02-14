"""Golden config lab services."""
from lab_builder.lab import Service
from lab_builder.node import LinuxNode
from lab_builder.labs.common import CEOS

class SuzieqPoller(LinuxNode):
    """Suzieq Poller Node."""
    name = "suzieq-poller"
    image = "netenglabs/suzieq:latest"


class SuzieqAnalyzer(LinuxNode):
    """Suzieq Analyzer Node."""
    name = "suzieq-analyzer"
    image = "netenglabs/suzieq:latest"


class SuzieqService(Service):
    """Lab service to start the suzieq service and analyzer."""
    nodes = {
        "sq-poller": SuzieqPoller,
        "sq-analyzer": SuzieqAnalyzer
    }

    binds = {
        "sq-poller": [
            "suzieq:/home/suzieq/parquet",
        ],
        "sq-analyzer": [
            "suzieq:/home/suzieq/parquet",
        ]
    }

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
