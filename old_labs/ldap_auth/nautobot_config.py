
AUTHENTICATION_BACKENDS = [
    'django_auth_ldap.backend.LDAPBackend',
    'nautobot.core.authentication.ObjectPermissionBackend',
]

import ldap
from django_auth_ldap.config import LDAPSearch,GroupOfNamesType

# Server URI
AUTH_LDAP_SERVER_URI = "ldap://ldap:1389"

# The following may be needed if you are binding to Active Directory.
AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_REFERRALS: 0
}

# Set the DN and password for the Nautobot service account.
AUTH_LDAP_BIND_DN = f"cn={os.environ.get('LDAP_ADMIN_USERNAME')},dc=example,dc=org"
AUTH_LDAP_BIND_PASSWORD = os.environ.get("LDAP_ADMIN_PASSWORD")
AUTH_LDAP_USER_DN_TEMPLATE = "cn=%(user)s,ou=users,dc=example,dc=org"
AUTH_LDAP_REQUIRE_GROUP = "CN=loginusers,ou=groups,DC=example,DC=org"
AUTH_LDAP_GROUP_SEARCH = LDAPSearch("ou=groups,dc=example,dc=org", ldap.SCOPE_SUBTREE, "(objectClass=groupOfNames)")
AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()
AUTH_LDAP_USER_FLAGS_BY_GROUP = {
    "is_active": "CN=loginusers,ou=groups,DC=example,DC=org",
    "is_staff": "CN=loginusers,ou=groups,DC=example,DC=org",
    "is_superuser": "cn=superusers,ou=groups,dc=example,dc=org"
}
AUTH_LDAP_FIND_GROUP_PERMS = True
AUTH_LDAP_ALWAYS_UPDATE_USER = True
AUTH_LDAP_MIRROR_GROUPS = ["loginusers", "tenant1", "tenant2"]
