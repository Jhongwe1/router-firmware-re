# 3. The board — and four things the spec sheet got wrong

![TOTOLINK N150RT PCB, annotated](../notes/img/05-pcb-top-annotated.jpg)

Five ICs, photographed and identified from the ink on the package:

| ref | part | what it is |
|---|---|---|
| — | **Realtek RTL8196E** | the SoC: MIPS-compatible core, integrated switch |
| `U19` | **Eon EN25QH32B** | 32 Mbit = **4 MiB** SPI NOR — the entire firmware |
| — | **Winbond W9825G6KH** | 32 MiB SDRAM |
| — | **Realtek RTL8188ER** | the 2.4 GHz radio |
| — | **LSP5526** | the regulator |

The annotation is rendered from [`pcb-top-annotations.json`](../notes/img/pcb-top-annotations.json)
by a script, not drawn in an image editor, so a moved callout shows up in
`git diff` as a changed number and anybody can re-render it against the source
photograph. The unit's MAC barcode and serial QR are painted out with the
coordinates recorded — a filled rectangle, never a blur, because **a blur is a
reversible transform on a known font and a barcode is decoded by machine.**

## The prediction, three weeks early

The published specification for this model says **2 MB** of flash.

In week 1, three weeks before the hardware arrived, the vendor firmware
containers were parsed and each section's declared burn address read out:
`w6cg` at `0x010000`, `cr6c` at `0x060000`, the root filesystem at `0x180000`.
The last section's offset plus its length comes to **3.57 MiB**. A 2 MB part
cannot hold it. The note written that week says **"≥ 4 MB, to be settled
physically in W02"**.

`U19` is 4 MiB.

This is the first falsifiable claim this project made about the physical world,
and it was made from a file format rather than from a datasheet — which is the
whole point. The specification is marketing; the container is what the vendor's
own flashing tool believes.

## Three more things the paper got wrong

**The SoC is an RTL8196E, not the RTL8196C** the week plan asserted. That is a
different CPU core, and it matters: it turns week 1's reading of the ELF header
as MIPS-I from an assumption into a testable hypothesis about which toolchain
the SDK used.

**The RAM is 32 MiB fitted, not 16 MB.** *Fitted* is not *usable* — the kernel
banner decides the second number — and both are recorded rather than merged.

**The radio is an RTL8188ER**, which fixes the driver and therefore the set of
wireless CVEs that could possibly apply.

## One source, and saying so

Every reading in the table above has **exactly one source: the ink on the
package.** That column stayed empty on purpose for four days, and it is worth
looking at how it was eventually filled, because the first attempt was wrong.

An early version of this chapter argued that `flashrom` agreeing on 4096 KiB is
*not* an independent source, "because its database is keyed on the same part
name". **That is false.** flashrom matches on `manufacture_id` and `model_id`;
the name is the lookup's *output*, not its index. Told to emulate a
`W25Q128FV` it answers `W25Q128.V` — a different string comes out than went in,
which a name-keyed lookup cannot do.

So flashrom **is** a second source for *which part an id denotes*. It is still
not a second source for *what the id bytes are*, because that is the same clip
on the same bus. Those are different claims and this project had merged them.

The JEDEC id itself has still never been read. Chapter 14 says so.

## The RTL8196E identification, and the source that disagrees

Three sources say RTL8196E: the package marking, the boot loader banner
(`---RealTek(RTL8196E)at 2014.04.22-16:22+0800 v1.3 [16bit](400MHz)`), and the
kernel's own probe. One source in the firmware disagrees and says RTL8186 — and
it is discounted for a reason that is checkable rather than a judgement call:
**two lines earlier that same driver announces it is probing for an RTL8186**,
so the string is the question, not the answer.

> **Where this chapter stops:** these are identifications from markings and
> firmware strings. The CPU *core* inside the RTL8196E — RLX4181 against
> RLX5281 — is not settled here. An instruction census can show that an
> instruction is supported; it cannot show that one is absent. Chapter 14.
