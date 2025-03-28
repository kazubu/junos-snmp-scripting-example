#!/usr/bin/env python

#
# Copyright 2022 Yudai Yamagishi <yyamagishi@juniper.net>
# Copyright 2024 Kazuki Shimizu <kshimizu@juniper.net>
#
# Disclaimer: Use at your own risk!
# 
# How to use:
# 1. Copy this script to /var/db/scripts/event/ on the routing engine
# 2. Set this script to run every 1 minute
# set event-options generate-event utility-mib-update-timer time-interval 60
# set event-options policy update-utility-mib events utility-mib-update-timer
# set event-options policy update-utility-mib then event-script umib-helper-qfx-hwtables.py
# set event-options event-script file umib-helper-qfx-hwtables.py
# set system scripts language python3
# 3. Check if the script is working
# > show snmp mib walk jnxUtil ascii | match hwtables | match value
# jnxUtilIntegerValue."hwtables_egr_ip_tunnel_free" = 4096
# jnxUtilIntegerValue."hwtables_egr_ip_tunnel_max" = 4096
# jnxUtilIntegerValue."hwtables_egr_ip_tunnel_used" = 0
# jnxUtilIntegerValue."hwtables_egr_l3_intf_free" = 16376
# jnxUtilIntegerValue."hwtables_egr_l3_intf_max" = 16383
# jnxUtilIntegerValue."hwtables_egr_l3_intf_used" = 7
# jnxUtilIntegerValue."hwtables_egr_l3_next_hop_free" = 65525
# jnxUtilIntegerValue."hwtables_egr_l3_next_hop_max" = 65536
# jnxUtilIntegerValue."hwtables_egr_l3_next_hop_used" = 11
# jnxUtilIntegerValue."hwtables_l3_ecmp_free" = 32768
# jnxUtilIntegerValue."hwtables_l3_ecmp_group_free" = 4096
# jnxUtilIntegerValue."hwtables_l3_ecmp_group_max" = 4096
# jnxUtilIntegerValue."hwtables_l3_ecmp_group_used" = 0
# jnxUtilIntegerValue."hwtables_l3_ecmp_max" = 32768
# jnxUtilIntegerValue."hwtables_l3_ecmp_used" = 0
# jnxUtilIntegerValue."hwtables_mpls_entry_free" = 16384
# jnxUtilIntegerValue."hwtables_mpls_entry_max" = 16384
# jnxUtilIntegerValue."hwtables_mpls_entry_used" = 0
# > show log messages | match "MIB Update"
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_egr_l3_intf_max=>16383 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_egr_l3_intf_used=>7 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_egr_l3_intf_free=>16376 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_egr_l3_next_hop_max=>65536 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_egr_l3_next_hop_used=>11 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_egr_l3_next_hop_free=>65525 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_egr_ip_tunnel_max=>4096 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_egr_ip_tunnel_used=>0 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_egr_ip_tunnel_free=>4096 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_l3_ecmp_max=>32768 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_l3_ecmp_used=>0 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_l3_ecmp_free=>32768 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_l3_ecmp_group_max=>4096 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_l3_ecmp_group_used=>0 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_l3_ecmp_group_free=>4096 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_mpls_entry_max=>16384 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_mpls_entry_used=>0 (successfully populated utility mib database)
# Mar 27 10:42:02  ex4650 cscript[92547]: MIB Update hwtables_mpls_entry_free=>16384 (successfully populated utility mib database)
#
# How to do a test run:
# 1. Copy this script to /var/db/scripts/op/ on the routing engine
# 2. Allow this script to be run
# set system scripts language python3
# set system scripts op file umib-helper-qfx-hwtables.py
# 3. Run the script
# > op umib-helper-qfx-hwtables.py
# 4. Check if the script is working
# (same as above)

import jnpr.junos
import jcs
import re
from lxml import etree

def update_snmp_val(dev, instance, val_type, value):
    res = dev.rpc.request_snmp_utility_mib_set(object_type=val_type, instance=instance, object_value=value)
    res_str = res.findtext('./snmp-utility-mib-result', default='empty rpc response error')
    jcs.syslog('external.notice', f'MIB Update {instance}=>{value} ({res_str})')
    return

def main():
    pattern = re.compile('^([^ ]+)\s+(\d+)\s+(\d+)\s+(\d+)$')
    dev = jnpr.junos.Device(gather_facts=False)
    dev.open()

    res = dev.rpc.request_pfe_execute(target='fpc0', command='show hw tables summary', timeout='1')
    #print(res.text)

    for line in res.text.splitlines():
        #print(line)
        entry = re.match(pattern, line)

        if entry:
            entry_name = entry.group(1).lower()
            entry_max = entry.group(2)
            entry_used = entry.group(3)
            entry_free = entry.group(4)
        
            update_snmp_val(dev, f'hwtables_{entry_name}_max', 'integer', entry_max)
            update_snmp_val(dev, f'hwtables_{entry_name}_used', 'integer', entry_used)
            update_snmp_val(dev, f'hwtables_{entry_name}_free', 'integer', entry_free)

    dev.close()

    return

if __name__ == '__main__':
    main()

