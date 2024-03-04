from lab_builder.lab import Lab

from .services import NautobotService

class BasicNautobotLab(Lab):
    """A lab that contains a simple Nautobot application stack."""
    name = "Nautobot"
    nautobot: NautobotService

lab = BasicNautobotLab
