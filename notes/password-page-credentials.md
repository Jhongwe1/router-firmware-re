# `password.htm` hands the client the plaintext credentials — and only this build does

**The answer first.** `/password.htm` inlines the stored administrator username
**and password**, in plaintext, into two JavaScript variables in the page body.
The substitution is server-side SSI in the template shipped in this unit's own
rootfs:

```
/var/web/password.htm, lines 18-19

    var orgusername='<% getInfo("userName"); %>';
    var orgpassword='<% getInfo("passWord"); %>';
```

and the two comparisons immediately below them are the *entire* check that the
person changing the password knows the current one:

```
    if (document.password.Cusername.value != orgusername) { ... return false; }
    if (document.password.Cpassword.value != orgpassword) { ... return false; }
```

**That check runs in the browser.** It is the client-side half of the defect
CVE-2018-13315 describes as missing on the server, and the way it is implemented
is by sending the secret to the client so the client can compare it.

This answers the question `docs/report-draft-2.md` left open when it said `D-15`
adds *"reading: pages, and what they contain"* and never said what they contain.

## Two sources, because one is a template and one is a response

| | artefact | what it shows |
|---|---|---|
| **template** | `$FWRE_WORK/qemu-env-2018/var/web/password.htm`, 4,865 B — this unit's own rootfs | the two `getInfo` directives, unexpanded |
| **rendered** | `$FWRE_WORK/dumps/w05-password-page.html`, **5,332 B** | `getInfo` appears **0 times** — every directive expanded — and `orgusername` / `orgpassword` are present at lines 28-29 **carrying values** |

5,332 bytes is also what `BENCH-LOG.md` `T-43` measured on the device when the
`D-15` bypass turned `/password.htm` from `302 / 132` into `200 / 5332`.

> ⚠️ **Provenance gap, and it is this note's weakest point.**
> `dumps/w05-password-page.html` is named in **no committed file** — not
> `BENCH-LOG.md`, not `RUNBOOK.md`, not `runsheet.md`, not `PROGRESS.md`, not any
> other note. Whether it came off the device or out of the emulator, and in which
> run, is not recorded; the byte count is the only thing tying it to `T-43`.
> By this repository's own rule — *name the binary a claim was measured on, or do
> not make the claim* — **the template is load-bearing here and the rendered file
> is corroboration.** Closing it costs one capture: re-run `A3.13`'s bypass
> request with the body saved, and `cmp` it against this file.

A second unreconciled number, recorded rather than smoothed: the same page
measured **5,322** B in `P10-4` (stored password emptied) and **5,332** B in
`T-43` (credentials set, five characters each). The page length moving with the
credentials is consistent with them being inlined, but ten bytes is not five, and
**the arithmetic has not been made to come out.** Do not use the difference as
evidence until it does.

## Three builds, and this one is the only intersection

| build | `D-15`'s second credential pair | `password.htm` inlines the password |
|---|---|---|
| V2.1.2-B20150825 (2015, **published**) | **present** | **no** — only the username, and as an `<input value=…>` rather than a JS variable |
| **`TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002` (2018, this unit, unpublished)** | **present** | **yes — both halves** |
| V3.4.0-B20201030 (2020, **published**) | absent | **no** — `orgusername` survives, the `orgpassword` line is gone |

Read across rather than down, which is what makes it worth writing: **the 2020
build removed the credential pair *and* the password from the page**, and the
2015 build never put the password in the page at all. The unlockable door and the
thing behind it line up on exactly one of the three builds, and it is the one on
no download page.

## What this does and does not do to `D-15`'s severity

**What it does.** It settles what the bypass is worth reading. An unauthenticated
request whose username and password are both empty returns this page, and this
page contains the administrator's credentials — after which an attacker
authenticates legitimately and the bypass is no longer needed.

**What it does not do — and this is the half that stops it being a headline.**
Those two values have been obtainable with **no bypass at all** since 2019:

```
GET /config.dat        ->  200, 7,507 bytes, no credentials sent
```

`USER_NAME` and `USER_PASSWORD` are plaintext inside it — CVE-2019-19822 with
CVE-2019-19823, reproduced on this unit in `poc/01-config-disclosure.md`, and
still present in a build dated 2020-10-30. **So this is a second route to
something a five-year-public one-liner already gives, on a device that also
carries public unauthenticated root.** It raises what `D-15` *reads*; it does not
raise what an attacker *gets*.

## Prior art, and it is closer than expected

The sibling A3002RU has **three** 2018 CVEs on this one page, and all three exist
because of the mechanism above:

| | |
|---|---|
| CVE-2018-13317 | plaintext password disclosure by `GET /password.htm` |
| CVE-2018-13309 | XSS via the user's **password** — it is rendered into the page |
| CVE-2018-13310 | XSS via the user's **username** — likewise |

So *"this page carries the credentials"* is published, on a sibling, since 2018.
What is not published is that on this build the page is **gated**, so reaching it
takes `D-15`. The mechanism is old; the route is not.

## How the first version of this note was wrong

It did not exist, and what stood in its place was worse than nothing: a sentence
in `docs/report-draft-2.md` saying `D-15` adds *"reading: pages, and what they
contain"*, which is true, unfalsifiable, and reads as *"not much"*. On 2026-08-23
the author read that sentence and concluded the finding was unimportant — a
correct inference from an incomplete document.

The first draft of **this** note then over-corrected in the opposite direction
and called `D-15` an unauthenticated credential disclosure leading to full
takeover, which is mechanically true and was written **before** checking whether
those credentials were already unauthenticated by another route. They were, and
had been since 2019. Both errors are the same error: a claim about impact written
without asking what the attacker already had.
