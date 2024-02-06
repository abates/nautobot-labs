from lab_builder import Lab
from .services import NautobotWithGitService


class ConfigContextLab(Lab):
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
