"""Lab definition for Nautobot lab"""

import os
import shutil
from string import Template

def find_link(path):
   try:
        link = os.readlink(path)
        return find_link(link)
   except OSError: # if the last is not symbolic file will throw OSError
        return path

volume_template_str = '      - "$src:$dst"'

volume_template = Template(volume_template_str)

compose_template_str = """
version: "3.8"
services:
  nautobot:
    volumes:
$volumes
  nautobot-worker:
    volumes:
$volumes
"""

compose_template = Template(compose_template_str)

class NautobotLab:
    def __init__(self):
        self.dir = os.path.dirname(__file__)
        self.tempdir = os.path.join(self.dir, ".tmp")
        self.tempfile = os.path.join(self.tempdir, "docker-compose.nautobot-apps.yaml")
        if not os.path.exists(self.tempdir):
            os.mkdir(self.tempdir)

    @property
    def compose_files(self):
        if os.path.exists(self.tempfile):
            return ["docker-compose.nautobot.yml", self.tempfile]
        return ["docker-compose.nautobot.yml"]

    def pre_start(self):
        volumes = []
        for filename in os.listdir(os.path.join(self.dir, "apps")):
            if filename.startswith("."):
                continue

            volumes.append(volume_template.substitute(src=find_link(os.path.join(self.dir, "apps", filename)), dst=f"/opt/nautobot/apps/{filename}"))
        
        if volumes:
            with open(self.tempfile, "w") as file:
                print(compose_template.substitute(volumes="\n".join(volumes)), file=file)

    def post_stop(self):
        if os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir)

lab = NautobotLab
