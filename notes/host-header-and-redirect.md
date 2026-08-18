# `check_host` is present, correct, and unreachable

**The answer, with addresses.** This build has a host validator. It is
`check_host` at **`0x00410470`**, 272 bytes, and it is strict: first character
alphanumeric, length under 64, every later character alphanumeric or `-` or `.`,
no leading dot, no doubled dot, last character alphanumeric. Its verdict is
enforced — `process_header_end` tests it at **`0x0040bca4`** and a failure goes
to `fputs("host invalid!\n")` and **`send_r_bad_request`** at `0x0040bccc`,
which is a 400.

**None of it runs.** Six instructions earlier:

```
0040bbdc  lw v0, PTR_vhost_root
0040bbe4  lw v0, 0x0(v0)                 ; vhost_root
0040bbec  beq v0, zero, 0x0040bcd8       ; NULL -> skip the whole host block
```

`0x0040bcd8` is where the *successful* path lands — the `apmib_get(0xb6)` /
`apmib_get(0xb7)` credential compare. So when `vhost_root` is NULL, the
`strdup`, the `strlower`, the port truncation and `check_host` are all jumped
over, and the request proceeds exactly as if the host had been valid.

`vhost_root` comes from `VHostRoot` in `boa.conf`. In this build it is
**commented out**, in the shipped template `/etc/boa/boa.conf.bak` line 150 and
in the runtime `/var/boa.conf` the same line. So `vhost_root` is NULL on every
boot and `check_host` has never executed on this device.

Register: **`P8-5` confirmed** (emulated + static). Measured on `/bin/boa` from
this unit's flash dump, `sha256 19fe29d7…`.

---

## 1. Seventeen hosts, seventeen 200s

Static reading is not what settles this. `tools/qemu-env.sh serve` on the
`unit-2018` profile, `GET /login.htm`, one header changed:

| Host | expected under `check_host` | actual |
|---|---|---|
| `evil.example` | accept | 200 |
| `1evil.example` | accept | 200 |
| `-evil.example` | **reject** (first char) | 200 |
| `.evil.example` | **reject** (leading dot) | 200 |
| `evil..example` | **reject** (doubled dot) | 200 |
| `evil.example.` | **reject** (trailing dot) | 200 |
| `evil_example` | **reject** (underscore) | 200 |
| `a"><script>` | **reject** (punctuation) | 200 |
| `evil example` | **reject** (space) | 200 |
| `evil.example:8080` | accept (port truncated first) | 200 |
| 63 × `a` | accept | 200 |
| 64 × `a` | **reject** (length) | 200 |
| 300 × `a` | **reject** (length) | 200 |
| *(empty)* | **reject** | 200 |
| `evil.example/x` | **reject** | 200 |
| `evil@example` | **reject** | 200 |

Nine of the seventeen should have been 400. None was. Two sources disagreeing
is what sent this back to the listing, and the listing had the answer six
instructions above the call.

Controls in the same run: `/login.htm` 200 (exempt), `/blank.htm` 302 (gated),
so the server was serving and the gate was working while every host was
accepted.

## 2. The Host is reflected into the redirect

The gate's redirect builds an absolute URL from the client's Host — the value
`process_option_line` stored at `req+0x60` (`0x0040b948`), which is a *different
field* from the `req+0x70` that `check_host` would have validated:

```
GET /blank.htm            Host: <the socket's own address>
  -> Location: http://127.0.0.1:8099/login.htm

GET /blank.htm            Host: evil.example
  -> Location: http://evil.example/login.htm
```

**That is an unauthenticated open redirect**, on every gated path, which is
every `.htm` page. It needs no credentials because the redirect *is* the
unauthenticated response — the gate produces it precisely when the client has
not authenticated.

### And it is not XSS, which is worth saying as plainly as the finding

The same value reaches two sinks and **both encode it correctly**:

```
Host: a"><script>alert(1)</script>

Location: http://a%22%3e%3cscript%3ealert(1)%3c/script%3e/login.htm
<A HREF="http://a&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;/login.htm">here</A>.
```

URL-encoded in the header, HTML-entity-encoded in the body. Whoever wrote that
redirect page did the right thing in both places. A reflected value is not a
vulnerability by itself, and this is the case that shows the difference.

## 3. What this does and does not do for `P8-6`

`P8-6` (DNS rebinding) is blocked on exactly one precondition — that an
arbitrary `Host` is accepted — and that precondition now holds, measured rather
than assumed.

**But the value rebinding adds on this device is small, and this project already
measured why.** `P2-7` established that authorisation here is per-request HTTP
Basic and the device never sends `Set-Cookie`; `P2-1` established that
`POST /boafrm/*` is outside the gate. So an attacker who can make a victim's
browser send requests already gets the *actions* — that is `P8-3`, plain CSRF,
no rebinding needed. Rebinding buys one thing: **reading the response body**,
which is how `/config.dat` leaves the network.

> ⚠️ **Scope.** Everything above is measured on the `unit-2018` emulation
> profile — this unit's own `/bin/boa` and its own flash image, under
> `qemu-user`, not on the device. The header path is pure string handling with
> no MIB or flash access, which is the part of `boa` emulation reproduces most
> faithfully, but "most faithfully" is not "identically". What would confirm it
> on silicon: the same seventeen hosts against the device, and one `GET` of a
> gated page with an arbitrary `Host` to see the `Location` come back. That is
> two minutes of the next bench visit and needs no power cycle.

## 4. How the first version of this was wrong

**Twice, and the second one is the reason this note exists as its own file.**

The first reading looked for host validation in `process_option_line` — where
the `HOST` string literally is, at `0x0040b918` — found that the value is stored
at `req+0x60` and nothing else happens to it, and concluded there is no host
check in this build. That conclusion is *true of that function* and false of the
binary. `check_host` is a separate function at `0x00410470` with no string
constants of its own, so a string-driven search cannot find it.

What caught it was not a tool. It was
[`auth-flow-2018.md`](auth-flow-2018.md), written in W04-2, whose §"the whole
path" line already read `check_host` → `apmib_get(0xb6)` → `apmib_get(0xb7)` →
credential compare. Writing "there is no `check_host`" would have contradicted a
note in the same repository, in a file about the same function.

Then, with `check_host` found and read, the second version said the Host **is**
validated and the emulated 200s must be a mistake in the test. They were not.
The reading was right about `check_host` and wrong about whether anything calls
it under this configuration, and the branch that decides is `beq v0,zero` on a
global six instructions above the call. **A function that is correct and
unreachable reads exactly like a function that is correct**, unless you check
the caller.
