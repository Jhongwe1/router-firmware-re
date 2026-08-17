# PoC 04 — held

**This file deliberately contains no request.**

## What was measured

On 2026-08-17, on the 2018-01-10 build, two things were demonstrated on
hardware and recorded in the register with the refutation conditions that were
frozen before any packet was sent:

| register | finding | verdict |
|---|---|---|
| `P10-3` | The administrator password can be changed by an **unauthenticated** request that does not carry the current password. The form has fields for the current credentials; the handler does not check them. | confirmed |
| `P10-4` | With the stored administrator password empty, the credential comparison is **skipped entirely** — pages that were redirected are served with no `Authorization` header at all, and a *wrong* password is also accepted. | confirmed |

Separately, and distinct from both:

| register | finding | verdict |
|---|---|---|
| — | **A single unauthenticated, well-formed POST to one named handler removes the web server** until the device is power-cycled. Three requests of the same shape to a different handler immediately before it were all served normally. Nothing respawns `boa`. | measured, `D-11` |

The addresses, the handler names and the mechanism are stated in
[`PROGRESS.md`](../PROGRESS.md), [`notes/auth-flow-2018.md`](../notes/auth-flow-2018.md)
and [`test-ledger.md`](../test-ledger.md). **Naming a defect is research and it
is published.**

## Why there is no request here

[`docs/disclosure.md`](../docs/disclosure.md) — *findings are published,
reproductions follow the disclosure state, tradecraft is not published at all.*

None of the three above has been reported to anyone. So a copy-pasteable request
for them is not a reproduction of published work; it is a recipe for something
unreported, against a device that is end-of-life and still deployed. The other
files in this directory carry full requests **because** the issues they cover
have been public since 2019 and 2024.

This is the first time that rule has cost this project something it wanted to
write, which is the only kind of test a disclosure policy gets.

## What changes this file

The procedure is in `docs/disclosure.md` and it has four steps: demonstrate on
hardware and register the result (**done**), re-run the prior-art search for the
specific handler and parameter (**not done** — and the same search done for a
different handler this week returned a Cisco Talos advisory on the first page
that a search by product name had missed entirely), report to TWCERT/CC with the
reproduction, and hold public discussion until the coordinator closes the case or
90 days pass.

The date the clock starts gets written into `docs/disclosure.md` in the same
commit as the report. **It has not started.**
