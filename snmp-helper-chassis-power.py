#!/usr/bin/env python

#
# Copyright 2022 Yudai Yamagishi <yyamagishi@juniper.net>

# Disclaimer: Use at your own risk!
#
# How to use:
# 1. Copy this script to /var/db/scripts/snmp/ on the routing engine (both routing engines in dual RE configuration)
# 2. Set this script to provide data for OID .1.3.6.1.4.1.2636.3.58.1.2.1.9.0
# set system scripts language python3
# set system scripts snmp file snmp-helper-chassis-power.py oid .1.3.6.1.4.1.2636.3.58.1.2.1.9.0
# set system scripts snmp file snmp-helper-chassis-power.py python-script-user lab
# set snmp community public <-- needed for script to load (community name can be any)
# 3. Check if the script is working
# > show snmp mib get .1.3.6.1.4.1.2636.3.58.1.2.1.9.0
# jnxPsuChassisPowerConsumed.0 = 576
#

import jnpr.junos
import jcs
from lxml import etree

def main():
    # check query
    action = jcs.get_snmp_action()
    oid = jcs.get_snmp_oid()
    if action != 'get' and action != 'get-next':
        return
    elif oid.startswith('.1.3.6.1.4.1.2636.3.58.1.2.1') == False:
        return

    # gather data
    dev = jnpr.junos.Device(gather_facts=False)
    dev.open()

    res = dev.rpc.get_environment_pem_information()
    # print(etreem.dump(res))
    chassis_pwr_consumed = 0
    for item in res.iter('environment-component-item'):
        pem_name = item.findtext('./name')
        pem_state = item.findtext('./state')
        if pem_name == None or pem_state == None:
            continue

        pem_dc_info = item.find('./dc-information/dc-detail')
        if pem_state == 'Online' and pem_dc_info != None:
            chassis_pwr_consumed = chassis_pwr_consumed + int(pem_dc_info.findtext('./dc-power', default=0))

    dev.close()

    # return data
    if oid == '.1.3.6.1.4.1.2636.3.58.1.2.1.9.0': #jnxPsuChassisPowerConsumed
        jcs.emit_snmp_attributes('1.3.6.1.4.1.2636.3.58.1.2.1.9.0', 'Integer32', f'{chassis_pwr_consumed}')
    else:
        jcs.syslog('external.notice', f'failed to provide data for OID {oid}')

    return

if __name__ == '__main__':
    main()

