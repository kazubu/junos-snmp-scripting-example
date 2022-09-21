#!/usr/bin/env python

#
# Copyright 2022 Yudai Yamagishi <yyamagishi@juniper.net>
#
# Disclaimer: Use at your own risk!
# 
# How to use:
# 1. Copy this script to /var/db/scripts/event/ on the routing engine (both routing engines in dual RE configuration)
# 2. Set this script to run every 1 minute
# set event-options generate-event utility-mib-update-timer time-interval 60
# set event-options policy update-utility-mib events utility-mib-update-timer
# set event-options policy update-utility-mib then event-script umib-helper-chassis-power.py
# set event-options event-script file umib-helper-chassis-power.py
# set system scripts language python3
# 3. Check if the script is working
# > show snmp mib walk jnxUtil ascii | match pem | match value
# jnxUtilIntegerValue."pem_0_dc_current" = 12
# > show log messages|match "MIB Update"
# Sep 21 16:48:00.227 2022  Gundam-re0 cscript: %EXTERNAL-5: MIB Update pem_1_dc_load=>0 (successfully populated utility mib database)
#
# How to do a test run:
# 1. Copy this script to /var/db/scripts/op/ on the routing engine
# 2. Allow this script to be run
# set system scripts language python3
# set system scripts op file umib-helper-chassis-power.py
# 3. Run the script
# > op umib-helper-chassis-power.py
# 4. Check if the script is working
# > show snmp mib walk jnxUtil ascii | match pem | match value
# jnxUtilIntegerValue."pem_0_dc_current" = 12
# > show log messages|match "MIB Update"
# Sep 21 16:48:00.227 2022  Gundam-re0 cscript: %EXTERNAL-5: MIB Update pem_1_dc_load=>0 (successfully populated utility mib database)
#

import jnpr.junos
import jcs
from lxml import etree

# MAIN
def update_snmp_val(dev, instance, val_type, value):
    res = dev.rpc.request_snmp_utility_mib_set(object_type=val_type, instance=instance, object_value=value)
    res_str = res.findtext('./snmp-utility-mib-result', default='empty rpc response error')
    jcs.syslog('external.notice', f'MIB Update {instance}=>{value} ({res_str})')
    return

def main():
    dev = jnpr.junos.Device(gather_facts=False)
    dev.open()

    res = dev.rpc.get_environment_pem_information()
    # print(etreem.dump(res))
    for item in res.iter('environment-component-item'):
        pem_name = item.findtext('./name')
        pem_state = item.findtext('./state')
        if pem_name == None or pem_state == None:
            continue

        pem_dc_voltage = '0'
        pem_dc_current = '0'
        pem_dc_power = '0'
        pem_dc_load = '0'
        pem_dc_info = item.find('./dc-information/dc-detail')
        if pem_state == 'Online' and pem_dc_info != None:
            pem_dc_voltage = pem_dc_info.findtext('./dc-voltage', default=0)
            pem_dc_current = pem_dc_info.findtext('./dc-current', default=0)
            pem_dc_power = pem_dc_info.findtext('./dc-power', default=0)
            pem_dc_load = pem_dc_info.findtext('./dc-load', default=0)

        name_pfx = pem_name.replace(' ', '_').lower()
        update_snmp_val(dev, f'{name_pfx}_state', 'string', pem_state)
        update_snmp_val(dev, f'{name_pfx}_dc_voltage', 'integer', pem_dc_voltage)
        update_snmp_val(dev, f'{name_pfx}_dc_current', 'integer', pem_dc_current)
        update_snmp_val(dev, f'{name_pfx}_dc_power', 'integer', pem_dc_power)
        update_snmp_val(dev, f'{name_pfx}_dc_load', 'integer', pem_dc_load)

    dev.close()

    return

if __name__ == '__main__':
    main()

