#!/bin/bash

awx organizations create --name "Automation Team" > /dev/null 2>&1
awx credentials create --credential_type "Ansible Galaxy/Automation Hub API Token" --name "Galaxy Credentials" --organization "Automation Team" --inputs '{"url": "https://galaxy.ansible.com/"}' > /dev/null 2>&1
awx organizations associate --galaxy_credential "Galaxy Credentials" "Automation Team" > /dev/null 2>&1

INPUTS=$(cat << END
---
fields:
  - id: token
    type: string
    label: NAUTOBOT_TOKEN
    secret: true
  - id: url
    type: string
    label: NAUTOBOT_URL
END
)

INJECTORS=$(cat <<END
---
env:
  NAUTOBOT_TOKEN: '{{ token }}'
  NAUTOBOT_URL: '{{ url }}'
END
)

awx credential_types create --kind cloud --name "Nautobot" --description "Nautobot API Credentials" --inputs="$INPUTS" --injectors="$INJECTORS" > /dev/null 2>&1

