#!/bin/sh



LABS_DIR="/opt/nautobot/labs"
for LAB in `ls $LABS_DIR` ; do
  if [ -e "${LABS_DIR}/${LAB}/bin" ] ; then
    export PATH="$PATH:${LABS_DIR}/${LAB}/bin"
  fi
done

