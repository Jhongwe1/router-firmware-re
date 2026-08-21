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
