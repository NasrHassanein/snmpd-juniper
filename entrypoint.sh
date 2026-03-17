#!/bin/bash
set -e

echo "=== Juniper SNMP Simulator (MX240) ==="
echo "  sysDescr    : JUNOS 21.4R3.5"
echo "  sysObjectID : .1.3.6.1.4.1.2636.1.1.1.2.29 (jnxProductNameMX240)"
echo "  Community   : public"
echo "  Port        : 161/udp"
echo "==========================================="

# Start snmpd in foreground, log to stderr
exec /usr/sbin/snmpd -f -Lo -C -c /etc/snmp/snmpd.conf
