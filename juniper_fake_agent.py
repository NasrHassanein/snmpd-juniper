#!/usr/bin/env python3
"""
pass_persist script for faking Juniper JUNOS proprietary SNMP OIDs.
Handles GET, GETNEXT, and PING requests from snmpd.

Simulates a Juniper MX240 router running JUNOS 21.4R3.5 with:
  - JUNIPER-MIB / jnxBoxAnatomy (chassis info)
  - JUNIPER-MIB / jnxOperatingTable (RE/FPC CPU, memory, temp)
  - JUNIPER-MIB / jnxFruTable (FRU inventory & status)
  - JUNIPER-MIB / jnxAlarmTable (alarm status)
  - JUNIPER-CHASSIS-DEFINES-MIB (product identification)
  - ENTITY-MIB entPhysicalTable (chassis/module/port inventory)
  - HOST-RESOURCES-MIB hrSWInstalledTable (JUNOS version)

Juniper OID tree:
  enterprises.2636           = juniperMIB
  enterprises.2636.1         = jnxProducts
  enterprises.2636.1.1.1.2   = jnxProductName
  enterprises.2636.1.1.1.2.29 = jnxProductNameMX240
  enterprises.2636.3         = jnxMibs
  enterprises.2636.3.1       = jnxBoxAnatomy (chassis MIB)
"""

import sys
import time
import random

# ---------------------------------------------------------------------------
# Dynamic value generators
# ---------------------------------------------------------------------------
_start = time.time()

def _uptime():
    return str(int((time.time() - _start) * 100))

def _cpu_re0():
    return str(random.randint(5, 18))

def _cpu_fpc0():
    return str(random.randint(8, 25))

def _cpu_fpc1():
    return str(random.randint(6, 20))

def _mem_re0():
    """Memory utilisation percentage for RE0."""
    return str(random.randint(35, 55))

def _mem_fpc0():
    return str(random.randint(20, 40))

def _mem_fpc1():
    return str(random.randint(18, 38))

def _temp_re0():
    return str(random.randint(35, 48))

def _temp_fpc0():
    return str(random.randint(38, 52))

def _temp_fpc1():
    return str(random.randint(36, 50))

def _buf_re0():
    return str(random.randint(60, 85))

def _buf_fpc0():
    return str(random.randint(70, 90))


# ---------------------------------------------------------------------------
# OID table
# ---------------------------------------------------------------------------
# Juniper enterprise root: .1.3.6.1.4.1.2636
# jnxMibs:                 .1.3.6.1.4.1.2636.3
# jnxBoxAnatomy:           .1.3.6.1.4.1.2636.3.1
#
# jnxBoxAnatomy scalars:
#   jnxBoxDescr.0           = .1.3.6.1.4.1.2636.3.1.2.0
#   jnxBoxSerialNo.0        = .1.3.6.1.4.1.2636.3.1.3.0
#   jnxBoxRevision.0        = .1.3.6.1.4.1.2636.3.1.4.0
#   jnxBoxInstalled.0       = .1.3.6.1.4.1.2636.3.1.5.0
#   jnxBoxClass.0           = .1.3.6.1.4.1.2636.3.1.6.0
#
# jnxOperatingTable:        .1.3.6.1.4.1.2636.3.1.13
#   Index: jnxOperatingContentsType.L1.L2.L3.L4
#     Type 9 = Routing Engine, 7 = FPC, 8 = PIC, 2 = Power Supply, 4 = Fan Tray
#   Columns:
#     .1  = jnxOperatingContentsType (not accessible)
#     .2  = jnxOperatingDescr
#     .5  = jnxOperatingState        (1=unknown,2=running,3=ready,6=standby)
#     .6  = jnxOperatingTemp
#     .7  = jnxOperatingCPU
#     .8  = jnxOperatingISR (not used much)
#     .9  = jnxOperatingDRAMSize
#     .11 = jnxOperatingBuffer
#     .15 = jnxOperatingMemory
#
# jnxFruTable:              .1.3.6.1.4.1.2636.3.1.15
#   Same index scheme
#   Columns:
#     .1  = jnxFruName
#     .5  = jnxFruType    (1=other,2=clockgen,3=flexPIC,6=PIC,7=power,8=fan,
#                           9=sensor,10=RE,11=CB,12=FPC)
#     .6  = jnxFruSlot
#     .8  = jnxFruState   (1=unknown,2=empty,3=present,4=ready,5=announce-online,
#                           6=online,7=announce-offline,8=offline,9=diagnostic)
#     .10 = jnxFruTemp
#     .11 = jnxFruOfflineReason
#     .12 = jnxFruLastPowerOff (DateAndTime)
#     .13 = jnxFruLastPowerOn  (DateAndTime)

OID_MAP = {

    # =========================================================================
    # jnxBoxAnatomy scalars (.1.3.6.1.4.1.2636.3.1)
    # =========================================================================
    ".1.3.6.1.4.1.2636.3.1.2.0": ("string",   "Juniper MX240 Internet Backbone Router"),
    ".1.3.6.1.4.1.2636.3.1.3.0": ("string",   "JN1234567890"),                       # jnxBoxSerialNo
    ".1.3.6.1.4.1.2636.3.1.4.0": ("string",   "REV 01"),                              # jnxBoxRevision
    ".1.3.6.1.4.1.2636.3.1.5.0": ("timeticks", _uptime),                               # jnxBoxInstalled
    # jnxBoxClass.0 — points to jnxProductLineMX240 = .1.3.6.1.4.1.2636.1.1.1.1.29
    ".1.3.6.1.4.1.2636.3.1.6.0": ("objectid", ".1.3.6.1.4.1.2636.1.1.1.1.29"),

    # =========================================================================
    # jnxOperatingTable (.1.3.6.1.4.1.2636.3.1.13)
    # Index convention: ContentsType.L1.L2.L3.L4
    #   RE0 = 9.1.0.0, FPC0 = 7.1.0.0, FPC1 = 7.2.0.0
    #   PIC0/0 = 8.1.1.0, PIC1/0 = 8.2.1.0
    #   PSU0 = 2.1.0.0, PSU1 = 2.2.0.0
    #   Fan0 = 4.1.0.0, Fan1 = 4.2.0.0
    # =========================================================================

    # --- Routing Engine 0 (index 9.1.0.0) ---
    ".1.3.6.1.4.1.2636.3.1.13.1.2.9.1.0.0":  ("string",    "Routing Engine 0"),
    ".1.3.6.1.4.1.2636.3.1.13.1.5.9.1.0.0":  ("integer",   "2"),        # running
    ".1.3.6.1.4.1.2636.3.1.13.1.6.9.1.0.0":  ("gauge",     _temp_re0),  # temp °C
    ".1.3.6.1.4.1.2636.3.1.13.1.7.9.1.0.0":  ("gauge",     _cpu_re0),   # CPU %
    ".1.3.6.1.4.1.2636.3.1.13.1.9.9.1.0.0":  ("integer",   "16384"),    # DRAM MB
    ".1.3.6.1.4.1.2636.3.1.13.1.11.9.1.0.0": ("gauge",     _buf_re0),   # buffer %
    ".1.3.6.1.4.1.2636.3.1.13.1.15.9.1.0.0": ("gauge",     _mem_re0),   # memory %

    # --- FPC 0 (index 7.1.0.0) ---
    ".1.3.6.1.4.1.2636.3.1.13.1.2.7.1.0.0":  ("string",    "FPC: MPC7E 3D 40XGE"),
    ".1.3.6.1.4.1.2636.3.1.13.1.5.7.1.0.0":  ("integer",   "2"),
    ".1.3.6.1.4.1.2636.3.1.13.1.6.7.1.0.0":  ("gauge",     _temp_fpc0),
    ".1.3.6.1.4.1.2636.3.1.13.1.7.7.1.0.0":  ("gauge",     _cpu_fpc0),
    ".1.3.6.1.4.1.2636.3.1.13.1.15.7.1.0.0": ("gauge",     _mem_fpc0),

    # --- FPC 1 (index 7.2.0.0) ---
    ".1.3.6.1.4.1.2636.3.1.13.1.2.7.2.0.0":  ("string",    "FPC: MPC7E 3D 40XGE"),
    ".1.3.6.1.4.1.2636.3.1.13.1.5.7.2.0.0":  ("integer",   "2"),
    ".1.3.6.1.4.1.2636.3.1.13.1.6.7.2.0.0":  ("gauge",     _temp_fpc1),
    ".1.3.6.1.4.1.2636.3.1.13.1.7.7.2.0.0":  ("gauge",     _cpu_fpc1),
    ".1.3.6.1.4.1.2636.3.1.13.1.15.7.2.0.0": ("gauge",     _mem_fpc1),

    # --- PIC 0/0 (index 8.1.1.0) ---
    ".1.3.6.1.4.1.2636.3.1.13.1.2.8.1.1.0":  ("string",    "PIC: 10x10GE(LAN/WAN) SFP+"),
    ".1.3.6.1.4.1.2636.3.1.13.1.5.8.1.1.0":  ("integer",   "2"),

    # --- PIC 1/0 (index 8.2.1.0) ---
    ".1.3.6.1.4.1.2636.3.1.13.1.2.8.2.1.0":  ("string",    "PIC: 10x10GE(LAN/WAN) SFP+"),
    ".1.3.6.1.4.1.2636.3.1.13.1.5.8.2.1.0":  ("integer",   "2"),

    # --- Power Supply 0 (index 2.1.0.0) ---
    ".1.3.6.1.4.1.2636.3.1.13.1.2.2.1.0.0":  ("string",    "PSU: AC 2000W"),
    ".1.3.6.1.4.1.2636.3.1.13.1.5.2.1.0.0":  ("integer",   "2"),  # running
    ".1.3.6.1.4.1.2636.3.1.13.1.6.2.1.0.0":  ("gauge",     "0"),

    # --- Power Supply 1 (index 2.2.0.0) ---
    ".1.3.6.1.4.1.2636.3.1.13.1.2.2.2.0.0":  ("string",    "PSU: AC 2000W"),
    ".1.3.6.1.4.1.2636.3.1.13.1.5.2.2.0.0":  ("integer",   "2"),
    ".1.3.6.1.4.1.2636.3.1.13.1.6.2.2.0.0":  ("gauge",     "0"),

    # --- Fan Tray 0 (index 4.1.0.0) ---
    ".1.3.6.1.4.1.2636.3.1.13.1.2.4.1.0.0":  ("string",    "Fan Tray 0"),
    ".1.3.6.1.4.1.2636.3.1.13.1.5.4.1.0.0":  ("integer",   "2"),

    # --- Fan Tray 1 (index 4.2.0.0) ---
    ".1.3.6.1.4.1.2636.3.1.13.1.2.4.2.0.0":  ("string",    "Fan Tray 1"),
    ".1.3.6.1.4.1.2636.3.1.13.1.5.4.2.0.0":  ("integer",   "2"),

    # =========================================================================
    # jnxFruTable (.1.3.6.1.4.1.2636.3.1.15)
    # Same index scheme as jnxOperatingTable
    # =========================================================================

    # RE0
    ".1.3.6.1.4.1.2636.3.1.15.1.1.9.1.0.0":  ("string",   "Routing Engine 0"),       # jnxFruName
    ".1.3.6.1.4.1.2636.3.1.15.1.5.9.1.0.0":  ("integer",  "10"),                     # jnxFruType: RE
    ".1.3.6.1.4.1.2636.3.1.15.1.6.9.1.0.0":  ("integer",  "0"),                      # jnxFruSlot
    ".1.3.6.1.4.1.2636.3.1.15.1.8.9.1.0.0":  ("integer",  "6"),                      # jnxFruState: online
    ".1.3.6.1.4.1.2636.3.1.15.1.10.9.1.0.0": ("gauge",    _temp_re0),                # jnxFruTemp

    # FPC0
    ".1.3.6.1.4.1.2636.3.1.15.1.1.7.1.0.0":  ("string",   "FPC 0"),
    ".1.3.6.1.4.1.2636.3.1.15.1.5.7.1.0.0":  ("integer",  "12"),                     # jnxFruType: FPC
    ".1.3.6.1.4.1.2636.3.1.15.1.6.7.1.0.0":  ("integer",  "0"),
    ".1.3.6.1.4.1.2636.3.1.15.1.8.7.1.0.0":  ("integer",  "6"),
    ".1.3.6.1.4.1.2636.3.1.15.1.10.7.1.0.0": ("gauge",    _temp_fpc0),

    # FPC1
    ".1.3.6.1.4.1.2636.3.1.15.1.1.7.2.0.0":  ("string",   "FPC 1"),
    ".1.3.6.1.4.1.2636.3.1.15.1.5.7.2.0.0":  ("integer",  "12"),
    ".1.3.6.1.4.1.2636.3.1.15.1.6.7.2.0.0":  ("integer",  "1"),
    ".1.3.6.1.4.1.2636.3.1.15.1.8.7.2.0.0":  ("integer",  "6"),
    ".1.3.6.1.4.1.2636.3.1.15.1.10.7.2.0.0": ("gauge",    _temp_fpc1),

    # PSU0
    ".1.3.6.1.4.1.2636.3.1.15.1.1.2.1.0.0":  ("string",   "Power Supply 0"),
    ".1.3.6.1.4.1.2636.3.1.15.1.5.2.1.0.0":  ("integer",  "7"),                      # jnxFruType: power
    ".1.3.6.1.4.1.2636.3.1.15.1.6.2.1.0.0":  ("integer",  "0"),
    ".1.3.6.1.4.1.2636.3.1.15.1.8.2.1.0.0":  ("integer",  "6"),

    # PSU1
    ".1.3.6.1.4.1.2636.3.1.15.1.1.2.2.0.0":  ("string",   "Power Supply 1"),
    ".1.3.6.1.4.1.2636.3.1.15.1.5.2.2.0.0":  ("integer",  "7"),
    ".1.3.6.1.4.1.2636.3.1.15.1.6.2.2.0.0":  ("integer",  "1"),
    ".1.3.6.1.4.1.2636.3.1.15.1.8.2.2.0.0":  ("integer",  "6"),

    # Fan Tray 0
    ".1.3.6.1.4.1.2636.3.1.15.1.1.4.1.0.0":  ("string",   "Fan Tray 0"),
    ".1.3.6.1.4.1.2636.3.1.15.1.5.4.1.0.0":  ("integer",  "8"),                      # jnxFruType: fan
    ".1.3.6.1.4.1.2636.3.1.15.1.8.4.1.0.0":  ("integer",  "6"),

    # Fan Tray 1
    ".1.3.6.1.4.1.2636.3.1.15.1.1.4.2.0.0":  ("string",   "Fan Tray 1"),
    ".1.3.6.1.4.1.2636.3.1.15.1.5.4.2.0.0":  ("integer",  "8"),
    ".1.3.6.1.4.1.2636.3.1.15.1.8.4.2.0.0":  ("integer",  "6"),

    # CB0 (Control Board / SCB)
    ".1.3.6.1.4.1.2636.3.1.15.1.1.6.1.0.0":  ("string",   "CB 0"),
    ".1.3.6.1.4.1.2636.3.1.15.1.5.6.1.0.0":  ("integer",  "11"),                     # jnxFruType: CB
    ".1.3.6.1.4.1.2636.3.1.15.1.6.6.1.0.0":  ("integer",  "0"),
    ".1.3.6.1.4.1.2636.3.1.15.1.8.6.1.0.0":  ("integer",  "6"),

    # =========================================================================
    # jnxAlarm (.1.3.6.1.4.1.2636.3.4)
    # =========================================================================
    # jnxYellowAlarmCount.0
    ".1.3.6.1.4.1.2636.3.4.1.1.0": ("gauge",   "0"),
    # jnxYellowAlarmLastChange.0
    ".1.3.6.1.4.1.2636.3.4.1.2.0": ("timeticks", "0"),
    # jnxRedAlarmCount.0
    ".1.3.6.1.4.1.2636.3.4.2.1.0": ("gauge",   "0"),
    # jnxRedAlarmLastChange.0
    ".1.3.6.1.4.1.2636.3.4.2.2.0": ("timeticks", "0"),

    # =========================================================================
    # ENTITY-MIB entPhysicalTable (.1.3.6.1.2.1.47.1.1.1)
    # =========================================================================

    # Chassis (index 1)
    ".1.3.6.1.2.1.47.1.1.1.1.2.1":   ("string",   "Juniper MX240"),               # entPhysicalDescr
    ".1.3.6.1.2.1.47.1.1.1.1.4.1":   ("integer",  "0"),                            # containedIn (root)
    ".1.3.6.1.2.1.47.1.1.1.1.5.1":   ("integer",  "3"),                            # class: chassis
    ".1.3.6.1.2.1.47.1.1.1.1.7.1":   ("string",   "MX240"),                        # entPhysicalName
    ".1.3.6.1.2.1.47.1.1.1.1.9.1":   ("string",   "21.4R3.5"),                     # firmware rev
    ".1.3.6.1.2.1.47.1.1.1.1.10.1":  ("string",   "21.4R3.5"),                     # software rev
    ".1.3.6.1.2.1.47.1.1.1.1.11.1":  ("string",   "JN1234567890"),                 # serial
    ".1.3.6.1.2.1.47.1.1.1.1.12.1":  ("string",   "Juniper Networks, Inc."),        # mfg
    ".1.3.6.1.2.1.47.1.1.1.1.13.1":  ("string",   "MX240"),                        # model

    # Routing Engine 0 (index 2)
    ".1.3.6.1.2.1.47.1.1.1.1.2.2":   ("string",   "RE-S-2X00x6"),
    ".1.3.6.1.2.1.47.1.1.1.1.4.2":   ("integer",  "1"),
    ".1.3.6.1.2.1.47.1.1.1.1.5.2":   ("integer",  "9"),                            # class: module
    ".1.3.6.1.2.1.47.1.1.1.1.7.2":   ("string",   "Routing Engine 0"),
    ".1.3.6.1.2.1.47.1.1.1.1.11.2":  ("string",   "JN1234567891"),
    ".1.3.6.1.2.1.47.1.1.1.1.13.2":  ("string",   "RE-S-2X00x6"),

    # FPC 0 (index 3)
    ".1.3.6.1.2.1.47.1.1.1.1.2.3":   ("string",   "MPC7E 3D 40XGE"),
    ".1.3.6.1.2.1.47.1.1.1.1.4.3":   ("integer",  "1"),
    ".1.3.6.1.2.1.47.1.1.1.1.5.3":   ("integer",  "9"),
    ".1.3.6.1.2.1.47.1.1.1.1.7.3":   ("string",   "FPC 0"),
    ".1.3.6.1.2.1.47.1.1.1.1.11.3":  ("string",   "JN1234567892"),
    ".1.3.6.1.2.1.47.1.1.1.1.13.3":  ("string",   "MPC7E-MRATE"),

    # xe-0/0/0 port (index 4)
    ".1.3.6.1.2.1.47.1.1.1.1.2.4":   ("string",   "xe-0/0/0"),
    ".1.3.6.1.2.1.47.1.1.1.1.4.4":   ("integer",  "3"),
    ".1.3.6.1.2.1.47.1.1.1.1.5.4":   ("integer",  "10"),                           # class: port
    ".1.3.6.1.2.1.47.1.1.1.1.7.4":   ("string",   "xe-0/0/0"),

    # =========================================================================
    # HOST-RESOURCES-MIB hrSWInstalledTable (.1.3.6.1.2.1.25.6.3.1)
    # This is where NMS tools find the JUNOS version
    # =========================================================================
    ".1.3.6.1.2.1.25.6.3.1.2.1": ("string",  "JUNOS Base OS boot [21.4R3.5]"),
    ".1.3.6.1.2.1.25.6.3.1.2.2": ("string",  "JUNOS Base OS Software Suite [21.4R3.5]"),
    ".1.3.6.1.2.1.25.6.3.1.2.3": ("string",  "JUNOS Crypto Software Suite [21.4R3.5]"),
    ".1.3.6.1.2.1.25.6.3.1.2.4": ("string",  "JUNOS Kernel Software Suite [21.4R3.5]"),
    ".1.3.6.1.2.1.25.6.3.1.2.5": ("string",  "JUNOS Packet Forwarding Engine Support (MX240) [21.4R3.5]"),
    ".1.3.6.1.2.1.25.6.3.1.2.6": ("string",  "JUNOS Routing Software Suite [21.4R3.5]"),
    ".1.3.6.1.2.1.25.6.3.1.2.7": ("string",  "JUNOS Online Documentation [21.4R3.5]"),
    # hrSWInstalledType — operatingSystem(2)
    ".1.3.6.1.2.1.25.6.3.1.4.1": ("objectid", ".1.3.6.1.6.1.1"),
    ".1.3.6.1.2.1.25.6.3.1.4.2": ("objectid", ".1.3.6.1.6.1.1"),
    ".1.3.6.1.2.1.25.6.3.1.4.3": ("objectid", ".1.3.6.1.6.1.1"),
    ".1.3.6.1.2.1.25.6.3.1.4.4": ("objectid", ".1.3.6.1.6.1.1"),
    ".1.3.6.1.2.1.25.6.3.1.4.5": ("objectid", ".1.3.6.1.6.1.1"),
    ".1.3.6.1.2.1.25.6.3.1.4.6": ("objectid", ".1.3.6.1.6.1.1"),
    ".1.3.6.1.2.1.25.6.3.1.4.7": ("objectid", ".1.3.6.1.6.1.1"),
}


# ---------------------------------------------------------------------------
# Sorted OID list for GETNEXT
# ---------------------------------------------------------------------------
def _oid_sort_key(oid):
    return tuple(int(p) for p in oid.strip('.').split('.'))

SORTED_OIDS = sorted(OID_MAP.keys(), key=_oid_sort_key)


def find_next_oid(requested):
    req_tuple = _oid_sort_key(requested)
    for oid in SORTED_OIDS:
        if _oid_sort_key(oid) > req_tuple:
            return oid
    return None


def resolve_value(entry):
    t, v = entry
    if callable(v):
        return t, v()
    return t, v


def respond(oid, snmp_type, value):
    print(oid)
    print(snmp_type)
    print(value)
    sys.stdout.flush()


def main():
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
        except EOFError:
            break

        if not line:
            continue

        if line == "PING":
            print("PONG")
            sys.stdout.flush()
            continue

        command = line.lower()

        try:
            oid = sys.stdin.readline().strip()
        except EOFError:
            break

        if command == "get":
            if oid in OID_MAP:
                t, v = resolve_value(OID_MAP[oid])
                respond(oid, t, v)
            else:
                print("NONE")
                sys.stdout.flush()

        elif command == "getnext":
            next_oid = find_next_oid(oid)
            if next_oid:
                t, v = resolve_value(OID_MAP[next_oid])
                respond(next_oid, t, v)
            else:
                print("NONE")
                sys.stdout.flush()

        elif command == "set":
            sys.stdin.readline()
            sys.stdin.readline()
            print("not-writable")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
