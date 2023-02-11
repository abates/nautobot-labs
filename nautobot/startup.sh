#!/bin/sh

set -e

# Load any lab fixtures
for LAB in `ls $LABS_DIR` ; do
  if [ -d $LABS_DIR/$LAB/fixtures ] ; then
    for fixture in `ls $LABS_DIR/$LAB/fixtures` ; do
      echo -n "Loading fixture $LAB/fixtures/$fixture: "
      /usr/local/bin/nautobot-server loaddata $LABS_DIR/$LAB/fixtures/$fixture
    done
  fi
done

echo "Starting Nautobot Server"
/usr/local/bin/nautobot-server runserver 0.0.0.0:8080
