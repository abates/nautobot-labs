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
        "nautobot": ["./fixtures/*:/fixtures"],
    }

lab = LDAPAuthLab
