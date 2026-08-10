# Where the credentials actually are

**Question carried out of W01:** W01 recorded, as a correction to the project
plan, that "**There is no `/etc/passwd`** in either image. The credential check is
inside a binary." That was used to justify deferring the backdoor-account
question to W03, and then to W04.

**Answer: the premise was false.** Both images have `/etc/passwd`. It is a
symlink into a runtime tmpfs, `/bin/sysconf` populates it at boot from a template
that ships in the image, and the template contains
**Pierre Kim's 2015 backdoor account, in the build the vendor released after his
disclosure.**

```
$ ls -l etc/passwd
lrwxrwxrwx  etc/passwd -> /var/passwd          # both builds

$ strings -a bin/sysconf | grep passwd
cp /etc/passwd.org /var/passwd 2> /dev/null    # V2.1.2
cp /etc/passwd_orig /var/passwd                # V3.4.0
```

> **Scope.** Static. The hashes below were cracked offline from the shipped
> files; no device has been powered on and no login has been attempted. Whether
> any login service is actually reachable is a separate question, addressed at
> the end.

## The accounts

`/etc/passwd.org`, V2.1.2 (built **2015-08-25**):

```
root:zhxPr1e7Npazg:0:0:root:/:/bin/sh
onlime_r:$1$01OyWDBw$Hrxb2t.LtmiiJD49OBsCU/:0:0:root:/:/bin/sh
nobody:x:0:0:nobody:/:/dev/null
ftpshare:x:501:501:ftpshare:/:/bin/sh
sambashare:x:502:502:sambashare:/:/bin/sh
```

`/etc/passwd_orig`, V3.4.0 (built **2020-10-30**):

```
root:zhxPr1e7Npazg:0:0:root:/:/bin/sh
nobody:x:0:0:nobody:/:/dev/null
```

All three hashes fall to a candidate list of twenty common strings:

| account | hash | algorithm | password | in |
|---|---|---|---|---|
| `root` | `zhxPr1e7Npazg` | DES crypt | **`123456`** | **both builds** |
| `onlime_r` | `$1$01OyWDBw$Hrxb2t.LtmiiJD49OBsCU/` | MD5-crypt | **`12345`** | V2.1.2 only |
| `root` (in `/etc/shadow.sample`) | `$1$KEKJV2R0$TFJ4jy7waGKrjdNHwPGzV.` | MD5-crypt | **`root`** | both builds |

Three separate observations, in descending order of how much they matter:

1. **`onlime_r` is Pierre Kim's account, and the hash is his hash.** His
   2015-07-16 advisory publishes `$1$01OyWDBw$Hrxb2t.LtmiiJD49OBsCU/` for
   `onlime_r`, and names **N150RT-V2** as affected "until last firmware
   `TOTOLINK-N150RT-V2.1.1-B20150708.1548.web`". Our V2.1.2 image is dated
   **2015-08-25** — after that. The account survived the disclosure.
2. **`nobody` has UID 0 and GID 0** in both builds. Its shell is `/dev/null` and
   its shadow entry is `*`, so it is not a login. But any daemon that drops
   privilege by resolving the *name* `nobody` gets uid 0 and drops nothing.
3. **`root`'s password is `123456` in the 2020 build too**, five years and one
   full-disclosure event later, and it is a DES hash — 8 significant characters,
   56-bit key, seconds to crack. Pierre Kim's advisory gives `root:12345`; this
   image has `123456`. The vendor's response to a published root password was to
   add a digit.

`/etc/shadow.sample` is copied to `/var/shadow` by `rcS` line 51 (V2.1.2) and 63
(V3.4.0) in both builds. It does not matter for `root`, whose `/var/passwd` field
is a real hash rather than `x`, so that is the one consulted — but it is a third
credential store shipping a fourth weak password, and nothing removes it.

## This is not the web password

The web interface does not read `/etc/passwd` at all. It compares against APMIB
entries, and W04 recovered their names from the configuration table
([`mib-and-config-dat.md`](mib-and-config-dat.md)):

| id | name | used by |
|---|---|---|
| `0xb6` | `USER_NAME` | `process_header_end`, `formLogin` |
| `0xb7` | `USER_PASSWORD` | `process_header_end`, `formLogin` |

So W01's conclusion — "the credential check lives inside a binary" — is true of
the **web** login and was reached from a false premise about `/etc/passwd`. Two
independent credential systems exist on this device and W01 collapsed them into
one. The `/etc/passwd` accounts belong to whatever consumes them: telnet,
dropbear, FTP, Samba.

## Which of those is actually running

Not established, and it decides how much any of this is worth. What is on the
image:

| | V2.1.2 | V3.4.0 |
|---|---|---|
| `/bin/sysconf` copies a dropbear host key | yes | — |
| `formSSH` in the dispatch table | yes | removed |
| MIB `SSH_ENABLED` / `SSH_PORT` / `TELNET_ENABLED` | present | present |
| `telnetd` (busybox applet) | present | present, init line commented |

`sysconf` also runs `cp /etc/dropbear_rsa_host_key /var/dropbear/…`, which is
only worth doing if dropbear can start. **Next step: read the `SSH_ENABLED` and
`TELNET_ENABLED` defaults out of the shipped default-settings blob, and read
`formSSH`.** Until then the honest statement is: the accounts exist with these
passwords; whether anything answers on 22 or 23 by default is unknown.

## Two shipped private keys

Found while looking for the passwd template, in the same directory.

**V3.4.0 — `/etc/privateKey.key`, a 2048-bit RSA private key**, with its
certificate in `/etc/certificate.crt`:

```
subject= C=CN, ST=JS, L=SZ, O=RS, OU=WN, CN=192.168.1.254,
         emailAddress=patrick_cai_rs@163.com
issuer=  (same — self-signed)
notBefore= Dec 19 10:21:01 2013 GMT
notAfter=  Dec 19 10:21:01 2014 GMT
```

`O=RS`, `OU=WN`, `CN=192.168.1.254`: a Realtek-SDK sample key, not something
generated per device. Every unit running this firmware holds the same private
key, and the certificate **expired in 2014 — six years before this image was
built**.

**V2.1.2 — `/etc/dropbear_rsa_host_key`**, 282 bytes, copied to
`/var/dropbear/` by `sysconf`. Same property: a host key baked into the image is
a host key shared by every unit, so the SSH host-key check protects nobody.

Neither has a CVE against this model. Neither is exotic — a shared key in a
firmware image is a well-worn finding — but both were sitting in `/etc` while
W01 concluded that directory had no credential material in it.

## How the first version of this note was wrong

It was wrong before it was written, which is worse. W01's rootfs inventory asked
whether `/etc/passwd` existed, got "no" from a `stat` on a symlink pointing into
a tmpfs that does not exist in an unpacked image, and reported **absent** in
[`anatomy-n150rt.md`](anatomy-n150rt.md)'s file table. Nothing was broken; the
question was wrong. A dangling symlink is not an absent file, it is a file whose
content arrives at boot, and in an unpacked firmware image that is the normal
case for everything under `/var`.

That single false negative is why the backdoor-account question was carried
through W01, W03 and most of W04 as "the credential check must be inside a
binary" — when the answer was a `cat` away for three weeks. The check
`fwrecon rootfs` now needs is not "does this path resolve" but "does this path
resolve, and if not, does something in the image write it".
