###############################################################################
# Dockerfile — Juniper JUNOS SNMP Simulator (MX240)
#
# Builds a container running Net-SNMP's snmpd configured to impersonate
# a Juniper MX240 router running JUNOS 21.4R3.5.
#
# Since Juniper doesn't have a single official MIB GitHub repo like Cisco,
# we pull MIBs from the librenms/librenms-mibs repository which contains
# a comprehensive, maintained collection of Juniper MIB files.
#
# Build:
#   docker build -t juniper-snmp-sim .
#
# Run:
#   docker run -d --name juniper-router -p 10161:161/udp juniper-snmp-sim
#
# Test:
#   snmpget  -v2c -c public localhost:10161 sysDescr.0
#   snmpget  -v2c -c public localhost:10161 sysObjectID.0
#   snmpwalk -v2c -c public localhost:10161 .1.3.6.1.4.1.2636.3.1      # chassis
#   snmpwalk -v2c -c public localhost:10161 .1.3.6.1.4.1.2636.3.1.13   # operating
#   snmpwalk -v2c -c public localhost:10161 .1.3.6.1.4.1.2636.3.1.15   # FRU
#   snmpwalk -v2c -c public localhost:10161 .1.3.6.1.2.1.47            # entity
#   snmpwalk -v2c -c public localhost:10161 .1.3.6.1.2.1.25.6          # JUNOS pkgs
###############################################################################

FROM ubuntu:24.04

LABEL maintainer="snmp-sim"
LABEL description="Juniper JUNOS MX240 SNMP simulator using Net-SNMP + Juniper MIBs"

ENV DEBIAN_FRONTEND=noninteractive

# ─── 1. Install packages ────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        snmpd \
        snmp \
        libsnmp-dev \
        snmp-mibs-downloader \
        python3 \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download standard IETF/IANA MIBs
RUN download-mibs 2>/dev/null || true

# ─── 2. Clone Juniper MIBs from librenms-mibs (comprehensive collection) ────
#     Juniper has no single official GitHub MIB repo. The librenms-mibs repo
#     contains all Juniper MIBs extracted from official Junos MIB packages.
#     We use sparse checkout to only pull the juniper/ directory.
RUN git clone --depth 1 --filter=blob:none --sparse \
        https://github.com/librenms/librenms-mibs.git /tmp/librenms-mibs \
    && cd /tmp/librenms-mibs \
    && git sparse-checkout set juniper \
    && mkdir -p /usr/share/snmp/mibs/juniper \
    && cp /tmp/librenms-mibs/juniper/* /usr/share/snmp/mibs/juniper/ 2>/dev/null || true \
    && rm -rf /tmp/librenms-mibs

# Also grab top-level JUNIPER-* MIBs (SMI, chassis defines, etc.)
RUN git clone --depth 1 --filter=blob:none --sparse \
        https://github.com/librenms/librenms-mibs.git /tmp/librenms-top \
    && cd /tmp/librenms-top \
    && git sparse-checkout init --no-cone \
    && git sparse-checkout set 'JUNIPER-*' 'JNX-*' \
    && cp /tmp/librenms-top/JUNIPER-* /usr/share/snmp/mibs/juniper/ 2>/dev/null || true \
    && cp /tmp/librenms-top/JNX-* /usr/share/snmp/mibs/juniper/ 2>/dev/null || true \
    && rm -rf /tmp/librenms-top

# ─── 3. Client-side MIB config ──────────────────────────────────────────────
COPY snmp.conf /etc/snmp/snmp.conf

# ─── 4. snmpd configuration with Juniper identity overrides ─────────────────
COPY snmpd.conf /etc/snmp/snmpd.conf

# ─── 5. pass_persist agent script ───────────────────────────────────────────
COPY juniper_fake_agent.py /usr/local/bin/juniper_fake_agent.py
RUN chmod +x /usr/local/bin/juniper_fake_agent.py

# ─── 6. Entrypoint ─────────────────────────────────────────────────────────
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 161/udp

CMD ["/entrypoint.sh"]
