#!/bin/sh

set -e

for fixture in `ls /opt/nautobot/fixtures` ; do
  echo -n "Loading fixture $fixture: "
  /usr/local/bin/nautobot-server loaddata /opt/nautobot/fixtures/$fixture
done

echo "Starting Nautobot Server"
/usr/local/bin/nautobot-server runserver 0.0.0.0:8080
