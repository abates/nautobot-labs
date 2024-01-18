from lab_builder.node import LinuxNode
from ..nautobot.services import NautobotService


class LDAPServer(LinuxNode):
    image = "docker.io/bitnami/openldap:2.6"
    binds = [
        "./bin/*:/usr/local/bin"
    ]
    environment = {
        "LDAP_ADMIN_USERNAME": "admin",
        "LDAP_ADMIN_PASSWORD": "adminpassword",
        "BIND_DN": "cn={LDAP_ADMIN_USERNAME},dc=example,dc=org",
        "BIND_PASSWORD": "{LDAP_ADMIN_PASSWORD}",
        "SEARCH_BASE": "dc=example,dc=org",
    }


class NautobotWithLDAPService(NautobotService):
    nodes = {
        "ldap": LDAPServer,
    }
    extra_nautobot_config = "nautobot_config.py.j2"
