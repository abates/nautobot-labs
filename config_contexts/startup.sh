#!/bin/sh

set -e

DEFAULT_BRANCH=main

if [ ! -e /repos/config-contexts.git ] ; then
  cd /repos
  git init --bare config-contexts.git --initial-branch=$DEFAULT_BRANCH
  cp -r /configs /tmp/configs
  cd /tmp/configs
  git init

  git config user.email "operator@company.com"
  git config user.name "Operator"

  git add .

  git commit -m "Initial Commit"
  git branch -M $DEFAULT_BRANCH
  git remote add origin /repos/config-contexts.git
  git push -u origin $DEFAULT_BRANCH

  cd /.
  rm -rf /tmp/configs
fi

# Continue normal startup
/entrypoint.sh
