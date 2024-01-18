from lab_builder.node import LinuxNode
from ..nautobot.services import NautobotService


class LDAPServer(LinuxNode):
    image = "docker.io/bitnami/openldap:2.6"
    binds = [
        "./bin/*:/usr/local/bin"
    ]
    env = {
        "LDAP_ADMIN_USERNAME": "admin",
        "LDAP_ADMIN_PASSWORD": "adminpassword",
    }


class NautobotWithLDAPService(NautobotService):
    nodes = {
        "ldap": LDAPServer,
    }
    extra_nautobot_config = "nautobot_config.py.j2"
