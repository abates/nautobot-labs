"""The config contexts lab definition."""
from lab_builder.lab import Lab
from lab_builder.labs.common import CEOS
from lab_builder.labs.config_contexts.services import NautobotWithGitService

from .services import LeafSpineNetwork, SuzieqService

class GoldenConfigLab(Lab):
    """A lab demonstrating how config contexts are applied."""
    name = "GoldenConfigLab"
    description = "A lab to demonstrate git-based config contexts."

    services = {
        "nautobot": NautobotWithGitService,
        "suzieq": SuzieqService,
        "leaf-spine-network": LeafSpineNetwork,
    }

    binds = {
        "nautobot": ["./fixtures/*:/fixtures"],
        "suzieq": ["./inventory.yml:/home/suzieq/inventory.yml"],
        "git-server": [],
    }

lab = GoldenConfigLab
