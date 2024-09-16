"""Golden config lab services."""
from lab_builder.lab import Service, LinuxNode
from lab_builder.labs.common import CEOS
from lab_builder import config

class Suzieq(LinuxNode):
    """Suzieq Poller Node."""
    node_config = config.NodeConfig(
        name = "suzieq-poller",
        image = "netenglabs/suzieq:latest",
        entrypoint = "/usr/local/bin/sq-poller -I /home/suzieq/inventory.yml",
        shell = config.Command("/bin/bash", True),
        cli = config.Command("/usr/local/bin/suzieq-cli", True, working_directory="/home/suzieq"),
    )

class SuzieqService(Service):
    """Lab service to start the suzieq service and analyzer."""
    suzieq: Suzieq = config.NodeConfig(
        binds=config.Binds(config.NamedBind(name="suzieq", mount_point="/home/suzieq/parquet")),
    )

class LeafSpineNetwork(Service):
    """A simple leaf/spine network of CEOS switches."""

    dc1_spine_1: CEOS = config.NodeConfig(
        links=config.Links(
            config.Link(interface="eth1", to_device="dc1_leaf_1", to_interface="eth1"),
            config.Link(interface="eth2", to_device="dc1_leaf_2", to_interface="eth1"),
            config.Link(interface="eth3", to_device="dc1_leaf_3", to_interface="eth1"),
        )
    )

    dc1_spine_2: CEOS = config.NodeConfig(
        links=config.Links(
            config.Link(interface="eth1", to_device="dc1_leaf_1", to_interface="eth2"),
            config.Link(interface="eth2", to_device="dc1_leaf_2", to_interface="eth2"),
            config.Link(interface="eth3", to_device="dc1_leaf_3", to_interface="eth2"),
        )
    )

    dc1_leaf_1: CEOS
    dc1_leaf_2: CEOS
    dc1_leaf_3: CEOS

    def created(self):
        super().created()
        self.dc1_spine_1.mgmt_ipv4 = "172.100.100.2"
        self.dc1_spine_2.mgmt_ipv4 = "172.100.100.3"
        self.dc1_leaf_1.mgmt_ipv4 = "172.100.100.10"
        self.dc1_leaf_2.mgmt_ipv4 = "172.100.100.11"
        self.dc1_leaf_3.mgmt_ipv4 = "172.100.100.12"
