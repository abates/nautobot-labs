#!/bin/sh

set -e

/opt/nautobot/bootstrap.sh
nautobot-server celery worker -l $NAUTOBOT_LOG_LEVEL
