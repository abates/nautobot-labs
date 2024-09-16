from os import path

from lab_builder.lab import Lab
from lab_builder import config
from .services import NautobotWithLDAPService


class LDAPAuthLab(Lab):
    name = "LDAPAuth"
    description = "A lab to demonstrate LDAP authentication in Nautobot"
    nautobot: NautobotWithLDAPService = config.ServiceConfig(
        ldap=config.NodeConfig(
            binds=config.Binds(config.FilesystemBind(
                mount_point="/ldifs",
                local_path=path.join(path.dirname(__file__), "ldifs"),
                read_only=True,
            )),
        ),
        nautobot=config.NodeConfig(
            binds=config.Binds(*config.GlobBinds(
                local_path=path.join(path.dirname(__file__), "fixtures", "*"),
                mount_point="/fixtures",
                read_only=True),
            ),
        )
    )

lab = LDAPAuthLab
