# 14. What this does not prove

This chapter should be uncomfortable to read. If it is not, it has not been
written hard enough.

## No second instrument has read that flash

Every byte-level claim in this document about this unit's firmware comes through
**one path**: the boot loader's `FLR` command, over this device's own UART, into
its own RAM, out through `DB`.

Two full reads produced an identical SHA-256. That proves the transfer and the
SPI read are **stable**. It does not prove they are **correct**. A systematic
error in `FLR` — a wrong stride, an off-by-one in a chunk boundary, a bank
selection this project does not know about — is invisible to both reads.

The instrument that would settle it is a SOIC-8 clip on `U19` and a programmer.
It has been attempted across three power supplies and the part sits at ~1.70 V
against a 3.3 V supply; the reads fail. Whether that is a clamp on the board or
resistance in the clip path **is not resolved**, and separating them needs
either a current measurement the clip's fixed header makes impossible or the
part off the board.

**The JEDEC id has never been read.** "Eon EN25QH32B" still has exactly one
source: the ink on the package.

I keep this paragraph in the document because deleting it would mean remembering
that I deleted it.

## Six measurements were cut rather than run, and three kinds of cut are not one kind

Twenty-three of this register's rows were never executed. Six of them were cut in
the last session, and the ledger keeps three kinds apart on purpose, because
collapsing them turns *I chose not to* into *I could not* — which is the
flattering direction and therefore the one to watch.

**Out of scope by consent.** A malformed beacon is a broadcast; it reaches the
scan path of every device in radio range. That is a different consent situation
from a cable between two ports, and **no purchase changes it**. Rows cut for this
reason should not come back even when the equipment exists, and saying so is the
conclusion rather than an apology for it.

**Blocked on an instrument.** The SPI-clip trio — a second reader for the flash,
a direct write, and the JEDEC id — stopped because the part measures **1.70 V
against a 3.3 V supply** through the clip, across three different supplies. A
read taken at 1.70 V that *looks* correct is worse than one that fails, because
those rows exist to remove the confound "two instruments disagree about one die"
and undervoltage manufactures exactly that confound. **These would have produced
checkable facts**, and their absence is the first section of this chapter rather
than a footnote.

Whether the 1.70 V is the board clamping the net or resistance in the clip path
**was never separated**, and the register says so in those words. The reasons say
*not doing this*, not *cannot, because X*.

**Traded away on purpose.** One row — writing a modified image back to flash —
was cut *after* its preconditions were met, not before. The write-back path and
the boot loader's TFTP rescue had both been rehearsed. It was cut because a
cheaper row had already bought most of what it was for: `J 80500000` handed this
SoC 156 bytes of code it had never seen, with the payload printing a nonce that
occurs zero times in the 4 MiB dump, and **no flash byte written**. What the
reflash adds on top of that is *persistence across a power cycle* — and that is
the part paid for with the only unit in existence.

The cost of that trade is stated rather than left for the reader to find: the
chain in chapter 10 ends at a flash byte changed by an HTTP request and does not
extend to a modified image booting, and the outbound plain-HTTP upgrade path with
its checksum-only acceptance stays a **static reading for good**. It is a
supply-chain class named and never executed.

## A claim this project's own tool makes and never measured

When `fwrecon compcs` rejects a blob whose checksum does not verify, it prints:

```
The device itself would reject this blob.
```

That is an assertion about **device behaviour**, and the only test that would
have measured it was the direct-write row above — the one that deliberately
corrupts the checksum by a computed 178 and watches what the device does with it.
That row is cut, so the sentence has no measurement behind it and will not get
one under this project.

It is left in the tool by decision, and listed here instead of quietly kept. A
tool that says *the device would reject this*, with zero device measurements
behind it, is the same shape as the fifty-five entries in chapter 12 — and the
only thing separating a recorded limitation from an instrument bug is whether
somebody wrote it down before a reader found it.

## Inferences about other N150RT units are inferences

There is one unit. Every result about *this build* is a result about *this
chip*. The three-step timeline in chapter 5 compares three images; it does not
establish what any other unit shipped in the same window, and the vendor's
version-to-build mapping is not public.

## Everything the emulator was given, and what each distorts

Chapter 9's table, restated as limits:

* the emulated server is handed **a real flash image**, so nothing it shows
  transfers to a device with different configuration;
* `/web/config.dat` is a **directory** there, so links 1 and 2 of chapter 10's
  chain **cannot** be reproduced under emulation at all;
* the published-image build synthesises three regions with **zeroed payloads**,
  so nothing about MACs, radio calibration or credentials transfers;
* `flash default` SIGBUSes under `qemu-user` on an alignment the real kernel's
  trap handler fixes — so any conclusion about the factory-reset path from the
  emulator is void.

## The claims that are static only

Marked throughout as *"the code reads as"*, and collected here:

* the 2015 and 2020 columns of every table — those are downloaded files, and
  this device has never run either;
* the boot loader's **interrupt wiring** — that its TFTP is interrupt-driven,
  that `J` masking interrupts is what stops it, that the `eth0` handler carries
  the packet input path. Three registered tests are frozen against it and
  **none has been run**;
* the auto-burn path and the two filenames that make an upload self-execute.
  Nothing has sent either;
* `formSysCmd`'s absence from the two published builds is `grep` on three
  binaries, which is a strong reading and still a reading.

## The wireless surface was not measured, and the reason is an instrument

Two registered tests — a malicious beacon against the site-survey table, and a
WPS information element with a two-byte length field — require monitor mode and
frame injection. The only wireless interface in this lab is an Intel AX201:
it is on **PCIe**, so `usbipd-win` cannot forward it to WSL under any
configuration, and `iwlwifi` does not implement injection.

That reason is **falsifiable**: buy an AR9271, get `aireplay-ng --test` to pass,
and those rows come back. What was cut is the measurement, not the question.

There is a second reason and it is not about equipment: beacon and deauthary
injection reach every device in range. That is a different consent situation
from a cable between two ports, and three other rows were cut for it.

## No new exploitable vulnerability was found

Everything in chapters 6, 8 and 10 is a **located** and independently derived
version of something already disclosed. Chapter 11's `miniigd` termination is a
denial of service, not code execution — and this document says so, having first
drafted it as the CVE-2014-8361 injection and then refuted itself with a
control.

Three of this project's own findings were **withdrawn** after being written up,
and one turned out to have a CVE against it already. One item in the disclosure
register has had **no prior-art search**, so it is not reportable and has not
been reported. *"Nobody published it"* is a claim that needs a search behind it.

## The SoC core is not identified

RLX4181 against RLX5281. An instruction census can show that an instruction is
**supported**; it cannot show that one is **absent**, because absence in the
binaries that happen to be on this chip is not absence in the ISA.

## What the reader cannot reproduce

Three tiers, and this is stated on page one of
[`REPRODUCE.md`](../REPRODUCE.md) rather than discovered at step 40:

* **T1 — a clone and an internet connection.** The two published images, every
  report derived from them, and 592 checks that prove this project's own
  instruments can fail.
* **T2 — plus a flash dump.** Not obtainable unless you own one of these
  routers.
* **T3 — plus the device.** Everything else.

Chapter 5's headline result and chapter 10's whole chain are **T2 and T3**. A
reader at T1 can check the method and cannot check the finding, and no amount of
writing changes that.

## And the prediction that was simply wrong

Before one bench session, the register predicted the live configuration would
differ from the factory baseline in **20 of 343** entries. The measurement read
**4 of 343**, because `flash default-sw` had rewritten both regions in between.

It is still in the register, as written, with the refutation firing against it.
**A register whose predictions get edited after the fact predicts nothing.**

## The last measurement of the project refuted its own prediction, and that is where it stops

The final bench session asked whether restoring the boot loader's interrupt state
brings its TFTP server back after a jump into RAM. The control — restore the
interrupt mask only — stayed dead, as designed. The full version restored the
mask and the CPU's interrupt enable, and on the wire the loader answered ARP in
0.9 ms and **ignored three TFTP read requests**.

So the reading is confirmed one layer *below* where the prediction placed it:
interrupts are what packet **reception** was missing. And the prediction's own
success criterion — that TFTP comes back — is **refuted**.

The negative half narrowed the question instead of widening it, which is unusual
enough to be worth the space: the ARP round trip excludes both candidates the
register was holding in reserve, leaving the TFTP service's own state, with two
independent readings agreeing that a transfer started and never completed.

**But that is a candidate and not a conclusion, and this chapter is where the
difference gets stated.** Nothing measured why the service stops answering. The
row is recorded `partial`. Two of the other rows closed the same night are
`partial` as well, each for a clause its own frozen prediction got wrong — and
recording three confirmations was available, because every main conclusion holds.

**A register that rounds up when the headline survives is a register that decides
after the fact which half counted.**
