#!/bin/sh

set -e

LABS_DIR="/opt/nautobot/labs"
# make sure the labs directory actually exists
mkdir -p $LABS_DIR

# Create the nautobot config
cat /opt/nautobot/default_nautobot_config.py > /opt/nautobot/nautobot_config.py
for LAB in `ls $LABS_DIR` ; do
  if [ -e $LABS_DIR/$LAB/nautobot_config.py ] ; then
    cat $LABS_DIR/$LAB/nautobot_config.py >> /opt/nautobot/nautobot_config.py
  fi
done

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
