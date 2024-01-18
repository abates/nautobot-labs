#!/bin/bash
set +x

source /var/lib/awx/venv/awx/bin/activate

bootstrap_development.sh

# Start the services
exec supervisord --pidfile=/tmp/supervisor_pid -n
