"""The config contexts lab definition."""
from lab_builder.lab import Lab
from .services import NautobotWithGitService


class ConfigContextLab(Lab):
    """A lab demonstrating how config contexts are applied."""
    name = "ConfigContextLab"
    description = "A lab to demonstrate git-based config contexts."
    services = {
        "nautobot": NautobotWithGitService,
    }

    binds = {
        "nautobot": ["./fixtures/*:/fixtures"],
        "git-server": [
            "./config-contexts:/repos/config-contexts",
        ]
    }

lab = ConfigContextLab
