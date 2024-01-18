import os
from lab_builder import Lab
from .services import NautobotWithLDAPService


class LDAPAuthLab(Lab):
    name = "LDAPAuth"
    description = "A lab to demonstrate LDAP authentication in Nautobot"
    services = {
        "nautobot": NautobotWithLDAPService,
    }

    binds = {
        "ldap": ["./ldifs:/ldifs"],
        "nautobot": ["./fixtures:/fixtures"],
    }

    def started(self):
        super().created()
        for fixture_file in ["10_organization.yaml", "20_permissions.yaml", "30_devices.yaml"]:
            self.services["nautobot"].nodes["nautobot"].load_fixture(f"/fixtures/{fixture_file}")


lab = LDAPAuthLab
