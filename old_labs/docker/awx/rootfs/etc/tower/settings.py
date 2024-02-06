import os
import socket

ADMINS = ()
STATIC_ROOT = '/var/lib/awx/public/static'
PROJECTS_ROOT = '/var/lib/awx/projects'
JOBOUTPUT_ROOT = '/var/lib/awx/job_status'

#IS_K8S = True

SECRET_KEY = "MbADUwynaTnmODjtCosz"

ALLOWED_HOSTS = ['*']

#INTERNAL_API_URL = 'http://127.0.0.1:8013'

# Sets Ansible Collection path
AWX_ANSIBLE_COLLECTIONS_PATHS = '/var/lib/awx/vendor/awx_ansible_collections'

# Container environments don't like chroots
AWX_PROOT_ENABLED = False

# Automatically deprovision pods that go offline
AWX_AUTO_DEPROVISION_INSTANCES = True

CLUSTER_HOST_ID = socket.gethostname()
SYSTEM_UUID = os.environ.get('MY_POD_UID', '00000000-0000-0000-0000-000000000000')

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

SERVER_EMAIL = 'root@localhost'
DEFAULT_FROM_EMAIL = 'webmaster@localhost'
EMAIL_SUBJECT_PREFIX = '[AWX] '

EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = False

LOGGING['handlers']['console'] = {
    '()': 'logging.StreamHandler',
    'level': 'INFO',
    'formatter': 'simple',
    'filters': ['guid'],
}

LOGGING['loggers']['django.request']['handlers'] = ['console']
LOGGING['loggers']['rest_framework.request']['handlers'] = ['console']
LOGGING['loggers']['awx']['handlers'] = ['console', 'external_logger']
LOGGING['loggers']['awx.main.commands.run_callback_receiver']['handlers'] = ['console']
LOGGING['loggers']['awx.main.tasks']['handlers'] = ['console', 'external_logger']
LOGGING['loggers']['awx.main.scheduler']['handlers'] = ['console', 'external_logger']
LOGGING['loggers']['django_auth_ldap']['handlers'] = ['console']
LOGGING['loggers']['social']['handlers'] = ['console']
LOGGING['loggers']['system_tracking_migrations']['handlers'] = ['console']
LOGGING['loggers']['rbac_migrations']['handlers'] = ['console']
LOGGING['handlers']['callback_receiver'] = {'class': 'logging.NullHandler'}
LOGGING['handlers']['task_system'] = {'class': 'logging.NullHandler'}
LOGGING['handlers']['tower_warnings'] = {'class': 'logging.NullHandler'}
LOGGING['handlers']['rbac_migrations'] = {'class': 'logging.NullHandler'}
LOGGING['handlers']['system_tracking_migrations'] = {'class': 'logging.NullHandler'}
LOGGING['handlers']['management_playbooks'] = {'class': 'logging.NullHandler'}

USE_X_FORWARDED_PORT = True
BROADCAST_WEBSOCKET_PORT = 8052
#BROADCAST_WEBSOCKET_PORT = 8013
#BROADCAST_WEBSOCKET_VERIFY_CERT = False
BROADCAST_WEBSOCKET_PROTOCOL = 'http'
#BROADCAST_WEBSOCKET_SECRET = "eWpDbkV1ZG91ek9vYXZSa050ZHo="

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("awx-redis", 6379)],
        },
    },
}

BROKER_URL="redis://awx-redis:6379/"
DATABASES = {
    'default': {
        'ATOMIC_REQUESTS': True,
        'ENGINE': 'awx.main.db.profiled_pg',
        'NAME': "awx",
        'USER': "awx",
        'PASSWORD': "shuOKNHPUwtxdxjNjMoZ",
        'HOST': "awx-db",
        'PORT': "5432",
    }
}

AWX_ISOLATION_SHOW_PATHS = [
    '/etc/pki/ca-trust:/etc/pki/ca-trust',
    '/usr/share/pki:/usr/share/pki',
]
