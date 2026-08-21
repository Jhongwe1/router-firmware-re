# 6. Inside `boa`: the dispatch table and the substring gate

Boa 0.94.14rc21, running as root, with the vendor's handlers bolted on. Two
structures decide everything: the table that maps a URL to a function, and the
three-line test that decides whether to ask for a password.

## Recovering `root_form[]` without the leaked header

The dispatch table is an array of `{name, handler}` pairs. Leaked Realtek SDK
headers exist and say what the record looks like, and this project used one
early and got burned: the header declares `char name[80]`, and this build uses
`char *name`. A structure recovered from someone else's source tree is a
hypothesis about your binary.

So the table is recovered from **the dispatcher's own arithmetic**. The loop
that walks it advances by a fixed stride and loads two words per record; the
stride is read off the increment instruction, the record start from where the
first comparison lands, and the table's extent from where the loop's bound comes
from. [`BoaFormTable.java`](../ghidra/scripts/BoaFormTable.java) does that and
emits JSON; the result for each build carries the SHA-256 of the binary it read.

The counts, all three builds, from
[`reports/ghidra-formtable-*.json`](../reports/):

| build | `root_form[]` entries |
|---|---|
| V2.1.2 (2015) | 57 |
| this unit (2018) | 58 — including `formSysCmd` at `0x004838a8` |
| V3.4.0 (2020) | 57 |

`grep -aoc formSysCmd` on the three raw binaries gives **0 / 1 / 0**.

**Absent → present → absent is a build-time option, not a vendor fix.** W04 had
recorded the string's absence from the published images as the vendor repairing
CVE-2019-19824; a fix does not reappear two and a half years later. That reading
is withdrawn, and the withdrawal is in the record next to the original.

## The gate, and why the advisory understates it

The published advisory for CVE-2019-19822 says, in effect, *`.dat` files are not
access-controlled*. That is a symptom. The cause is broader and it is three
lines.

`process_header_end` decides whether to run the authorisation check at all, and
the test is a **substring** test on the request URI:

* **2015:** `strstr(uri, "htm")` — if the URI does not contain `htm`, no
  authorisation runs;
* **2018 (this unit):** `.htm` or `.asp`, and nothing else;
* **2020:** the 2015 test plus a POST arm.

So `/config.dat` is unauthenticated not because `.dat` is special, but because
**every path that does not contain the magic substring is unauthenticated**.
That is a much larger statement than the advisory's, and it is checkable: it
predicts which of the shipped pages are reachable without credentials, in
advance, from the code.

## The prediction it made, and the three pages nobody had looked at

Eleven exemption strings were read out of `process_header_end` at instruction
level. Five name pages this firmware does not ship. Applying the unanchored
substring test to the remaining six against the 76 `.htm` files the device
actually serves predicts **exactly seven exempt pages** — including
`wan_status.htm` and `Connect_status.htm`, which are exempt for no reason other
than that **`status.htm` is a substring of both of them**.

Measured on the device: seven exempt, sixty-nine redirected to the login page,
**no error in either direction across all 76.**

Then a bonus the prediction did not ask for: `/boafrm/formLogin.htm` answers
`404` where the other fifty-six `/boafrm/` paths answer `302`, because
`formLogin` is on the exemption list too.

## Why it is still not a bypass

The obvious next move is to decorate a blocked path until it contains an exempt
substring — `/password.htm?login`, `/login.htm/../password.htm`, and ten more
shapes. Twelve were tried. None bypassed anything.

The reason is sharper than "it did not work": **the exemption test and the file
lookup read the same normalised path.** Any path decorated enough to become
exempt is a path the server then fails to open. The two tests are wrong in the
same direction, which is what makes them consistent.

That prediction — that the substring gate implies a bypass — was written down
before the requests were sent, and it was **refuted**. It stays in the register
with the refutation recorded against it.

## Where the decompiler lost the argument

Ghidra raised three warnings on the function containing the gate. This project's
rule is that a warning costs the decompiler the last word, so the branch was
read at instruction level with
[`BoaListing.java`](../ghidra/scripts/BoaListing.java) and the note records the
instruction addresses rather than the decompiled C.

That is not decompiler-bashing. It is that a decompiler which tells you it is
unsure and is then quoted anyway has been used as an oracle rather than as a
tool.

> **Where this chapter stops:** the gate's behaviour is measured on this unit
> for `GET` against the 76 shipped `.htm` pages. The POST half of the surface is
> chapter 10's; the 2015 and 2020 readings in the table are static, from images
> this device has never run.
