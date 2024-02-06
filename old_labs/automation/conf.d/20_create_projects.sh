#!/bin/bash

function add_project() {
  project_name=$1

  awx projects create --name "$project_name" \
                      --organization "Automation Team" \
                      --scm_type git \
                      --scm_url "$GIT_SERVER/$project_name"
}

function add_template() {
  playbook=$1
  
}

for project in /projects/* ; do
  if [ -d $project ] ; then
    project_name=$(basename $project)
    add_project $project_name
    for playbook in $(find $project -name "pb_*") ; do
      add_template $(basename $playbook)
    done
  fi
done
