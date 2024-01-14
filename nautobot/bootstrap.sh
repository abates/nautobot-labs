#!/bin/sh

set -e

APPS_DIR="/opt/nautobot/apps"

# Install any local apps
for APP_DIR in `ls $APPS_DIR` ; do
  if [ -d $APPS_DIR/$APP_DIR ] ; then
    wd=$(pwd)
    cd $APPS_DIR/$APP_DIR
    pip install -e .
    cd $wd
  fi
done

# Install other requirements
if [ -e $APPS_DIR/requirements.txt ] ; then
  wd=$(pwd)
  cd $APPS_DIR
  pip install -r requirements.txt
  cd $wd
fi

# Create the nautobot config
cat /opt/nautobot/default_nautobot_config.py > /opt/nautobot/nautobot_config.py
if [ -e $APPS_DIR/nautobot_config.py ] ; then
  cat $APPS_DIR/nautobot_config.py >> /opt/nautobot/nautobot_config.py
fi

LABS_DIR="/opt/nautobot/labs"
# make sure the labs directory actually exists
mkdir -p $LABS_DIR

for LAB in `ls $LABS_DIR` ; do
  if [ -e $LABS_DIR/$LAB/nautobot_config.py ] ; then
    cat $LABS_DIR/$LAB/nautobot_config.py >> /opt/nautobot/nautobot_config.py
  fi
done

