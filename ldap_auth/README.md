# Nautobot LDAP Auth Lab

This lab provides an environment that includes a full Nautobot stack as well
as an Open LDAP server. Using LDAP authentication combined with permissions,
this lab demonstrates limiting access to Nautobot objects using LDAP groups.

## Users
When the lab is run, several users are created. In addition to the standard
admin user, four additional users are created (`user01`, `user02`, `user03` and
`user04`). The first three users are included in the `loginusers` group,
`user01` is also included in the `tenant1` group and `user02` is also included
in the `tenant2` group. With these groups, the following Nautobot configuration
is used:


```python
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
```

This configuration requires that anyone attempting to login to Nautobot must be
in the `loginusers` group. Anyone in that group will also be marked `active` and
`staff`. Since `user04` is not assigned to the `loginusers` group, that account
will not even be able to login.

## Permissions

Permissions are defined for any user within either the `tenant1` or `tenant2`
groups. See the [permissions fixture](fixtures/20_permissions.yaml) file for
the details of the permissions. Login using either the `user01` or the `user02`
user accounts to see that access to the sample devices is limited based on
tenancy.
