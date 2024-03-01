"""The config contexts lab definition."""
from lab_builder.lab import Lab
from lab_builder.labs.config_contexts.services import NautobotWithGitService

from .services import LeafSpineNetwork, SuzieqService

class GoldenConfigLab(Lab):
    """A lab demonstrating how config contexts are applied."""
    name = "GoldenConfigLab"
    description = "A lab to demonstrate git-based config contexts."
    ipv4_subnet = "172.100.100.0/24"

    services = {
        "nautobot": NautobotWithGitService,
        "suzieq": SuzieqService,
        "leaf-spine-network": LeafSpineNetwork,
    }

    binds = {
        "db": ["./nautobot.sql:/tmp/nautobot.sql"],
        "suzieq": ["./inventory.yml:/home/suzieq/inventory.yml"],
        "git-server": [],
    }

    def started(self):
        super().started()
        self.services["nautobot"].restore_db("/tmp/nautobot.sql")
    
lab = GoldenConfigLab
