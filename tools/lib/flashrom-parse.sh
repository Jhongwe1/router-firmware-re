#!/usr/bin/env bash
#
# flashrom-parse.sh -- everything this repository believes about the TEXT that
# flashrom prints, in one place, sourced by both tools that drive the clip.
#
# Why this is shared when the refusals deliberately are not
# --------------------------------------------------------
# flash-read.sh and flash-write.sh keep SEPARATE copies of the forbidden
# regions on purpose: two independent paths refusing the same two ranges is
# what makes "this project does not write the boot loader" a property of the
# project rather than of one script. That argument is about a POLICY, and a
# policy duplicated is a policy confirmed.
#
# The output format of another program is not a policy. It is one fact, and
# until 2026-08-21 it had two homes with the SAME defect in both: each asked
# flashrom for -V and then looked for a line that flashrom only prints at -VVV.
# flash-read.sh reported the empty result as "the chip is not answering" and
# named three hardware causes; flash-write.sh refused every write with "not
# writing a chip that is silent". Both messages point at the part. Neither
# failure is about the part.
#
# One fact, one owner. Instrument bugs 50 and 51.

# Measured 2026-08-21 against flashrom 1.3.0-2.1ubuntu2 through its own `dummy`
# programmer -- no clip, no router, no CH341A:
#
#   flags    RDID lines   identification lines
#   (none)        0               1
#   -V            0               2
#   -VV           0               2
#   -VVV          6               2
#
# `RDID returned ...` is emitted from flashrom's programmer-independent SPI
# probe path, so the threshold should be a property of the build rather than of
# the programmer -- but that is a structural argument resting on one
# measurement. Confirming it on the CH341A is a written prediction rather than
# an assumption carried forward: BENCH-LOG.md 2026-08-21, prediction 14.
FLASHROM_PROBE_V="-VVV"

# `Found` when flashrom matched the id against its own table; `Assuming` when it
# was TOLD the name with -c. The distinction is the whole value of the line: one
# is a second source, the other is this project's own input read back to it.
parse_chip_verb() {
  grep -m1 -oE '(Found|Assuming) [^"]*flash chip "' "$1" 2>/dev/null \
    | sed -E 's/^([A-Za-z]+) .*/\1/' || true
}

parse_chip_name() {
  # Anchored on the identification line, deliberately NOT on `flash chip "`
  # alone: that also matches every candidate flashrom lists when several of its
  # definitions match one id, and -m1 would then present a candidate as the
  # answer. The bracket is `[^"]`, not `[^\n]` -- inside a POSIX bracket
  # expression `[^\n]` means "neither a backslash nor the letter n", and every
  # vendor string this project will ever see here contains an n (Eon, Winbond,
  # Macronix). That was instrument bug 50, and it printed nothing for four days.
  grep -m1 -oE '(Found|Assuming) [^"]*flash chip "[^"]+"' "$1" 2>/dev/null \
    | sed -E 's/.*"([^"]+)".*/\1/' || true
}

parse_flashrom_version() {
  # The whole banner, verbatim, including the word "unknown" when that is what
  # the binary claims -- Debian and Ubuntu build the package without the version
  # string. A provenance record that omits a version it could not parse is
  # indistinguishable from one taken by a reader nobody identified.
  grep -m1 -oE 'flashrom [^,]+' "$1" 2>/dev/null || true
}

parse_rdids() {
  # RDID is re-issued for every candidate in flashrom's table, so a healthy
  # probe prints the same three bytes many times. More than one DISTINCT value
  # means the bus is unstable -- a contact problem, not a finding. A four-byte
  # RDID4 line yields the same three-byte prefix and collapses with the rest.
  grep -oE 'RDID returned 0x[0-9a-f]{2} 0x[0-9a-f]{2} 0x[0-9a-f]{2}' "$1" 2>/dev/null \
    | sed -E 's/RDID returned 0x([0-9a-f]{2}) 0x([0-9a-f]{2}) 0x([0-9a-f]{2})/\1\2\3/' \
    | sort -u || true
}

# No ids in the log is two completely different situations, and which one it is
# decides whether the operator touches the clip at all.
#
#   no-answer    nothing identified anything. The bus really is suspect.
#   not-printed  flashrom matched a chip, so the bus carried a transaction --
#                the RDID line simply was not in the log. A verbosity or a
#                format problem, and re-seating the clip cannot fix either.
rdid_failure_kind() {
  if [ -n "$(parse_chip_name "$1")" ]; then printf 'not-printed'; else printf 'no-answer'; fi
}
