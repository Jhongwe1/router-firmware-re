# 8. The config blob: `COMPCS` decoded

CVE-2019-19823 says the administrator password is stored in plaintext. This
chapter is that sentence turned into an offset.

## The format, read from the binary that writes it

Flash `0x00C000` holds a region tagged `COMPCS` — the live configuration. A
second region, `COMPDS`, holds the factory defaults. Both have the same shape:

* a **12-byte header** — tag, declared length, and a checksum byte that appears
  nowhere in the payload;
* an **LZSS-compressed** body;
* which decompresses to a **TLV table**: id, length, value.

The format was recovered twice, and the order matters. First it was **inferred
from the data** — ring-buffer fill behaviour, entry counts, a checksum whose
rule was guessed and then tested against both regions. Then it was **read out of
`libapmib.so`'s own `Decode`**, which confirmed the inference and supplied one
thing the data alone could never have given: **the checksum byte's rule**, which
is invisible in a blob that already passes it.

That is the difference between "my parser reproduces the bytes" and "my parser
agrees with the code that produced them", and this project had already been
burned once by trusting a leaked SDK header (chapter 6). The public SDK is used
here as a *second* source and never as the first.

## Two independent confirmations from the vendor's own binaries

The parser is checked against the vendor's tools running over the same bytes:

* `flash extr /web` writes **143 files whose SHA-256s all match** what
  `fwrecon web` declared from a container format that carries **no checksum and
  no entry count**;
* `flash all` agrees with `fwrecon compcs` on **249 of 316 shared names**, with
  66 more explained by four rendering rules and **exactly one** left over.

The "exactly one" is the useful number. A parser that agreed on everything would
be suspicious; one that disagrees on 67 and explains 66 of them by rule has a
model, and the one it cannot explain is written down rather than absorbed.

## The finding

`USER_PASSWORD` is an ordinary TLV entry. Its value is the ASCII string.

There is **no hashing step anywhere on that path** — not in the writer, not in
the reader, not in the comparison. `USER_NAME` sits beside it. Both decode from
this unit's own flash to `admin`.

And a third credential system nobody had counted: `SSH_PASSWORD`, a
factory-default `xa.zioncom`. W04 had found two credential systems; there are
three.

`TELNET_ENABLED` reads `0`, **confirmed by the code that reads it** rather than
by the field alone — which downgrades the `root:123456` account from an entry
point to the second stage of a chain. Calling it an entry point overstates it by
one step, and that correction is the sort this document exists to make against
itself.

## The arithmetic that proves a back-reference

The string `admin` appears **once** in the compressed region, literally, at
flash `0x00C0D1`. `USER_PASSWORD` is a back-reference to it.

That is not an inference from the decoder. It is arithmetic:

* replace those five bytes with `zzzzz` and the payload's 8-bit checksum moves
  by **178**;
* 178 = 2 × 89, and 89 is the byte-sum delta of `admin` → `zzzzz`;
* **the factor of two is the proof that the literal is referenced twice** —
  `USER_NAME` and `USER_PASSWORD`.

And the complementary experiment: replace them with `nimda` — the same five
characters reordered — and the checksum does not move at all, the region still
decodes, and **exactly two** fields change value.

Five bytes, no code executed, and this unit's administrator account is
different. Whether the *running* device reads that region is the one thing left
for a chip clip, and chapter 14 says so.

## The disclosure decision, column by column

Decoding a device's configuration produces per-unit identifiers, and what gets
published is a decision that has to be made field by field rather than in one
gesture. The register is [`docs/disclosure.md`](../docs/disclosure.md).

Two of its judgements are worth reproducing because both are cases where a
reason that sounded general turned out not to transfer:

**EXIF GPS is redacted from photographs, and the reason does not extend to the
flash dump.** GPS locates *a person*; a MAC address identifies *a device*. Those
are different exposures and the same rule does not cover both — the photographs
are redacted for a reason the dump does not share, and the dump is withheld for
two reasons of its own.

**One of the dump's two reasons has since disappeared.** It was withheld
because it contains per-unit secrets *and* because releasing it would let a
reader verify claims this project had not yet verified itself. The second reason
went away when the claims were verified. The first did not. A withheld artefact
whose stated reason has expired is a withheld artefact with one reason, not
zero, and the register now says which.

> **Where this chapter stops:** the decode is measured against this unit's own
> flash and against the vendor's own tools reading the same bytes. Whether the
> **running** system serves that region — as opposed to a copy — is chapter 10's
> question, and the answer there is more interesting than a simple yes.
