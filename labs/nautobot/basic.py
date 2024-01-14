from lab_builder.lab import Lab

from .nautobot import Nautobot

class BasicNautobotLab(Lab):
    name = "Nautobot"
    applications = [
        Nautobot
    ]

lab = BasicNautobotLab
