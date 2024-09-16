"""The config contexts lab definition."""
from os import path

from lab_builder import config
from lab_builder.lab import Lab
from .services import NautobotWithGitService


class ConfigContextLab(Lab):
    """A lab demonstrating how config contexts are applied."""
    name = "ConfigContextLab"
    description = "A lab to demonstrate git-based config contexts."
    nautobot: NautobotWithGitService = config.ServiceConfig(
        nautobot=config.NodeConfig(
            binds=config.Binds(config.FilesystemBind(
                mount_point="/fixtures",
                local_path=path.join(path.dirname(__file__), "fixtures"),
                read_only=True,
            )),
        ),
        git_server=config.NodeConfig(
            binds=config.Binds(config.FilesystemBind(
                mount_point="/respos/config-contexts",
                local_path=path.join(path.dirname(__file__), "config-contexts"),
                read_only=True,
            )),
        )
    )


lab = ConfigContextLab
