#!/bin/sh

set -e

/opt/nautobot/bootstrap.sh
/docker-entrypoint.sh $@
