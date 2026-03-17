# Juniper JUNOS SNMP Simulator

Docker container running Net-SNMP's `snmpd` configured to impersonate a **Juniper MX240** router running **JUNOS 21.4R3.5**.

Uses MIBs from [librenms/librenms-mibs](https://github.com/librenms/librenms-mibs) (the most comprehensive open collection of Juniper MIBs) and a `pass_persist` Python script to serve Juniper-proprietary OID subtrees with realistic, partially dynamic values.

## What it simulates

| MIB / Area                   | OID Subtree                     | Data                                                |
|------------------------------|---------------------------------|-----------------------------------------------------|
| MIB-II System                | `.1.3.6.1.2.1.1`               | sysDescr, sysObjectID, sysName (Junos format)       |
| IF-MIB                       | `.1.3.6.1.2.1.2`               | Linux interfaces renamed to Juniper style (xe-0/0/0)|
| ENTITY-MIB                   | `.1.3.6.1.2.1.47`              | Chassis, RE, FPC, port inventory                    |
| HOST-RESOURCES-MIB           | `.1.3.6.1.2.1.25.6`            | JUNOS software packages (version detection)         |
| JUNIPER-MIB jnxBoxAnatomy   | `.1.3.6.1.4.1.2636.3.1`        | Chassis description, serial, class                  |
| JUNIPER-MIB jnxOperatingTable| `.1.3.6.1.4.1.2636.3.1.13`     | RE/FPC CPU%, memory%, temp (dynamic)                |
| JUNIPER-MIB jnxFruTable     | `.1.3.6.1.4.1.2636.3.1.15`     | FRU inventory: RE, FPC, PSU, Fan, CB                |
| JUNIPER-MIB jnxAlarm        | `.1.3.6.1.4.1.2636.3.4`        | Yellow/Red alarm counters                           |

CPU, memory, and temperature values fluctuate on each poll to simulate a live device.

## Juniper OID hierarchy

```
.1.3.6.1.4.1.2636                    = juniperMIB (enterprise 2636)
.1.3.6.1.4.1.2636.1                  = jnxProducts
.1.3.6.1.4.1.2636.1.1.1.1            = jnxProductLine
.1.3.6.1.4.1.2636.1.1.1.2            = jnxProductName
.1.3.6.1.4.1.2636.1.1.1.2.29         = jnxProductNameMX240  ← sysObjectID
.1.3.6.1.4.1.2636.3                  = jnxMibs
.1.3.6.1.4.1.2636.3.1                = jnxBoxAnatomy
.1.3.6.1.4.1.2636.3.1.13             = jnxOperatingTable
.1.3.6.1.4.1.2636.3.1.15             = jnxFruTable
.1.3.6.1.4.1.2636.3.4                = jnxAlarm
```

## Quick start

```bash
# Build
docker build -t juniper-snmp-sim .

# Run
docker run -d --name juniper-router -p 10161:161/udp juniper-snmp-sim

# Test system identity
snmpget  -v2c -c public localhost:10161 sysDescr.0
snmpget  -v2c -c public localhost:10161 sysObjectID.0

# Test Juniper chassis MIB
snmpwalk -v2c -c public localhost:10161 .1.3.6.1.4.1.2636.3.1.2   # jnxBoxDescr
snmpwalk -v2c -c public localhost:10161 .1.3.6.1.4.1.2636.3.1.13  # jnxOperating (CPU/mem/temp)
snmpwalk -v2c -c public localhost:10161 .1.3.6.1.4.1.2636.3.1.15  # jnxFru (FRU inventory)
snmpwalk -v2c -c public localhost:10161 .1.3.6.1.4.1.2636.3.4     # Alarms

# Test ENTITY-MIB and host resources
snmpwalk -v2c -c public localhost:10161 .1.3.6.1.2.1.47           # Physical entities
snmpwalk -v2c -c public localhost:10161 .1.3.6.1.2.1.25.6.3       # JUNOS packages
```

Or with docker compose:

```bash
docker compose up -d
```

## Customising the device identity

Edit `snmpd.conf` and change:

- **sysDescr** — the JUNOS version banner (format: `Juniper Networks, Inc. <model> internet router, kernel JUNOS <version>...`)
- **sysObjectID** — look up your target device index in `JUNIPER-CHASSIS-DEFINES-MIB`:

  | Product       | Index | sysObjectID                           |
  |---------------|-------|---------------------------------------|
  | MX240         | 29    | `.1.3.6.1.4.1.2636.1.1.1.2.29`       |
  | MX480         | 25    | `.1.3.6.1.4.1.2636.1.1.1.2.25`       |
  | MX960         | 26    | `.1.3.6.1.4.1.2636.1.1.1.2.26`       |
  | MX204         | 120   | `.1.3.6.1.4.1.2636.1.1.1.2.120`      |
  | SRX340        | 96    | `.1.3.6.1.4.1.2636.1.1.1.2.96`       |
  | EX4300        | 91    | `.1.3.6.1.4.1.2636.1.1.1.2.91`       |
  | QFX5100       | 87    | `.1.3.6.1.4.1.2636.1.1.1.2.87`       |

- **sysName / sysLocation / sysContact** — whatever you need

## jnxOperatingTable index convention

Juniper uses a 4-level index: `ContentsType.L1.L2.L3.L4`

| Type | Value | Example Index |
|------|-------|---------------|
| Routing Engine | 9 | `9.1.0.0` (RE0), `9.2.0.0` (RE1) |
| FPC | 7 | `7.1.0.0` (FPC0), `7.2.0.0` (FPC1) |
| PIC | 8 | `8.1.1.0` (PIC0/0), `8.2.1.0` (PIC1/0) |
| Power Supply | 2 | `2.1.0.0` (PSU0), `2.2.0.0` (PSU1) |
| Fan Tray | 4 | `4.1.0.0` (Fan0), `4.2.0.0` (Fan1) |

To simulate more FPCs/PICs, add entries in the `OID_MAP` dictionary in `juniper_fake_agent.py` following this pattern.

## Architecture

```
┌────────────┐         ┌───────────────────────────────────────┐
│  NMS / CLI │  SNMP   │  Docker Container                     │
│  snmpget   │ ──────► │                                       │
│  snmpwalk  │  :161   │  snmpd                                │
│  LibreNMS  │ ◄────── │   ├─ override: sysDescr, sysObjID     │
│  Zabbix    │         │   ├─ IF-MIB (Linux real ifaces)       │
│  Oxidized  │         │   └─ pass_persist ──► python3         │
└────────────┘         │       juniper_fake_agent.py           │
                       │       (Juniper enterprise .2636 OIDs) │
                       │       (ENTITY-MIB .47)                │
                       │       (HOST-RESOURCES .25)            │
                       └───────────────────────────────────────┘
```

## MIB source

Unlike Cisco (which has an official GitHub repo), Juniper distributes MIBs through their [SNMP MIB Explorer](https://apps.juniper.net/mib-explorer/) download page. This Dockerfile pulls from [librenms/librenms-mibs](https://github.com/librenms/librenms-mibs) which aggregates Juniper MIBs from official releases and is actively maintained.

If you have access to the official Juniper MIB package (`.tar` from the MIB Explorer), you can extract and mount it instead:

```bash
docker run -d --name juniper-router \
  -v /path/to/juniper-mibs:/usr/share/snmp/mibs/juniper:ro \
  -p 10161:161/udp juniper-snmp-sim
```
