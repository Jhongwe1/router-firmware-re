# Version diff: N150RT V2.1.2-B20150825 -> N150RT V3.4.0-B20201030

- older: `06e5fbffb38f919a71336605faf5d5c0656b3f8d5ba4684746f917c395ecff88`
- newer: `a73f5bcf8b1d406a3db03abd57a3a0a43ad360aefbea3ab5cb279a9b357900d2`

## web handlers

_handlers reachable as /boafrm/<name>_

**Added (6)**

```
+ formAjaxGet
+ formAjaxSet
+ formAlgSip
+ formIPTV
+ formUploadFile
+ formWanStatus
```

**Removed (16)**

```
- formBufferMemory
- formDhcpv6s
- formDnsv6
- formIPv6Addr
- formIpv6Setup
- formNotice
- formOpMode1
- formOpMode2
- formQuickSetup
- formRadvd
- formSSH
- formSelLang
- formTunnel6
- formWizards
- formWlSiteSurveys
- formWlanRedirect2
```

## binaries

**Added (14)**

```
+ /bin/UDPserver
+ /bin/batchUpgrade
+ /bin/main_lc5761
+ /bin/reset
+ /bin/traceroute
+ /bin/wget
+ /lib/ld-uClibc-0.9.33.so
+ /lib/libcjson.so
+ /lib/libcrypt-0.9.33.so
+ /lib/libdl-0.9.33.so
+ /lib/libm-0.9.33.so
+ /lib/libmtdapi.so
+ /lib/libpthread-0.9.33.so
+ /lib/libuClibc-0.9.33.so
```

**Removed (28)**

```
- /bin/buffermemory
- /bin/default_sw
- /bin/dhcp6c
- /bin/dhcp6ctl
- /bin/dhcp6s
- /bin/dns_protocl
- /bin/dnsmasq
- /bin/ecmh
- /bin/flatfsd
- /bin/ip6tables
- /bin/mldproxy
- /bin/ndppd
- /bin/notice
- /bin/radvd
- /bin/radvdump
- /bin/rtk_cmd
- /bin/skt
- /lib/ld-uClibc-0.9.30.3.so
- /lib/libcrypt-0.9.30.3.so
- /lib/libdl-0.9.30.3.so
- /lib/libm-0.9.30.3.so
- /lib/libnsl-0.9.30.3.so
- /lib/libpthread-0.9.30.3.so
- /lib/libresolv-0.9.30.3.so
- /lib/librt-0.9.30.3.so
- /lib/libstdc++.so.6.0.13
- /lib/libuClibc-0.9.30.3.so
- /lib/libutil-0.9.30.3.so
```

## binaries reaching a command-execution sink

**Added (1)**

```
+ /lib/libmtdapi.so
```

**Removed (17)**

```
- /bin/buffermemory
- /bin/ddns_inet
- /bin/default_sw
- /bin/dhcp6c
- /bin/dnsmasq
- /bin/iapp
- /bin/igmpproxy
- /bin/ip6tables
- /bin/mldproxy
- /bin/notice
- /bin/ntp_inet
- /bin/ntpclient
- /bin/ppp_inet
- /bin/rebootschedule
- /bin/rebootschedules
- /bin/reload
- /bin/skt
```

## symlinks exposing runtime state inside the web document root

_a link surviving across versions means the exposure path was not closed_

**Added (3)**

```
+ /web/ca.cer -> /var/ca.cer
+ /web/config.dat -> /var/config.dat
+ /web/user.cer -> /var/user.cer
```

## other symlinks into runtime-writable storage

_ordinary read-only-rootfs plumbing; listed for completeness_

**Added (9)**

```
+ /dev/oprofile -> /var/oprofile
+ /etc/boa -> /var/boa
+ /etc/group -> /var/group
+ /root -> /var/root
+ /usr/share/udhcpc/eth1.1.deconfig -> /var/udhcpc/eth1.1.deconfig
+ /usr/share/udhcpc/eth1.2.deconfig -> /var/udhcpc/eth1.2.deconfig
+ /usr/share/udhcpc/eth1.3.deconfig -> /var/udhcpc/eth1.3.deconfig
+ /usr/share/udhcpc/eth1.4.deconfig -> /var/udhcpc/eth1.4.deconfig
+ /usr/share/udhcpc/usb0.deconfig -> /var/udhcpc/usb0.deconfig
```

**Removed (3)**

```
- /etc/boa/boa.conf -> /var/boa.conf
- /etc/dropbear -> /var/dropbear
- /web -> /var/web
```

## shared libraries needed by the web server

**Added (2)**

```
+ libcjson.so
+ libmtdapi.so
```

## services referenced by init scripts

**Added (7)**

```
+ /etc/init.d/rcS:#telnetd &
+ /etc/init.d/rcS:cp -rf /etc/boa.org /var/boa
+ /etc/init.d/rcS_32M:###for tr069
+ /etc/init.d/rcS_32M:##For miniigd
+ /etc/init.d/rcS_32M:#snmpd
+ /etc/init.d/rcS_32M:#telnetd &
+ /etc/init.d/rcS_32M:cp -rf /etc/boa.org /var/boa
```

**Removed (1)**

```
- /etc/init.d/rcS:#skt&
```

