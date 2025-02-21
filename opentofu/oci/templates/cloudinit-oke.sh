#!/bin/bash
## https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/gettingmetadata.htm
oke_init_url='http://169.254.169.254/opc/v2/instance/metadata/oke_init_script'
curl --fail -H "Authorization: Bearer Oracle" -L0 "${oke_init_url}" | base64 --decode >/var/run/oke-init.sh
bash /var/run/oke-init.sh