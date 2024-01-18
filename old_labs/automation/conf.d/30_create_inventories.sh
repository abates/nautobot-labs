#!/bin/bash

awx inventory create --name "Inventory" --organization "Automation Team" > /dev/null 2>&1

awx credentials create --credential_type "Nautobot" \
                       --name "Nautobot" \
                       --organization "Automation Team" \
                       --inputs "{\"token\": \"$NAUTOBOT_TOKEN\", \"url\": \"$NAUTOBOT_URL\"}" >/dev/null 2>&1

id=$(awx credential get "Nautobot" -f human --filter id | tail -n 1)
awx inventory_sources create --name "Nautobot Inventory" \
                             --inventory "Inventory" \
                             --credential "$id" \
                             --source scm \
                             --source_project "Automation" \
                             --source_path "inventory.yml" \
                             --overwrite "true" \
                             --overwrite_vars "true" > /dev/null 2>&1

