"""The config contexts lab definition."""
from os import path

from lab_builder.lab import Lab
from lab_builder.labs.config_contexts.services import NautobotWithGitService
from lab_builder import config

from .services import LeafSpineNetwork, SuzieqService

class GoldenConfigLab(Lab):
    """A lab demonstrating how config contexts are applied."""
    name = "GoldenConfigLab"
    description = "A lab to demonstrate git-based config contexts."
    ipv4_subnet = "172.100.100.0/24"

    nautobot: NautobotWithGitService = config.ServiceConfig(
        db=config.NodeConfig(
            binds=config.Binds(config.FilesystemBind(
                mount_point="/tmp/nautobot.sql",
                local_path=path.join(path.dirname(__file__), "nautobot.sql"),
                read_only=True,
            )),
        ),
        suzieq=config.NodeConfig(
            binds=config.Binds(config.FilesystemBind(
                mount_point="/home/suzieq/inventory.yml",
                local_path=path.join(path.dirname(__file__), "inventory.yml"),
                read_only=True,
            )),
        ),
    )

    suzieq: SuzieqService
    leaf_spine_network: LeafSpineNetwork

    def started(self):
        super().started()
        self.nautobot.restore_db("/tmp/nautobot.sql")
    
lab = GoldenConfigLab
