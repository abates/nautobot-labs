
from lab_builder.labs.common import GitServer
from lab_builder.labs.nautobot.services import NautobotService


class NautobotWithGitService(NautobotService):
    nodes = {
        "git-server": GitServer,
    }
