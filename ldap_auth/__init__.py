"""Lab definition for LDAP authentication lab"""

class LDAPAuthLab:
    compose_files = ["docker-compose.ldap_auth.yml"]
    components = ["nautobot", "ldap"]

lab = LDAPAuthLab
