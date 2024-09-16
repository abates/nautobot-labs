from os import path

from lab_builder import config
from lab_builder.lab import LinuxNode
from ..nautobot.services import NautobotService


class LDAPServer(LinuxNode):
    node_config = config.NodeConfig(
        image="docker.io/bitnami/openldap:2.6",
        binds=config.Binds(
            *config.GlobBinds(
                local_path=path.join(path.dirname(__file__), "bin", "*"),
                mount_point="/usr/local/bin",
                read_only=True,
            )
        ),
    )


class NautobotWithLDAPService(NautobotService):
    ldap: LDAPServer

    environment = config.Environment({
        "LDAP_ADMIN_USERNAME": "admin",
        "LDAP_ADMIN_PASSWORD": "adminpassword",
        "BIND_DN": "cn={LDAP_ADMIN_USERNAME},dc=example,dc=org",
        "BIND_PASSWORD": "{LDAP_ADMIN_PASSWORD}",
        "SEARCH_BASE": "dc=example,dc=org",
    })
    extra_nautobot_config = "extra_nautobot_config.py.j2"
