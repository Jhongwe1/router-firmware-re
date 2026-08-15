#!/usr/bin/env bash
# Self-test for tools/redact-photo.py and tools/annotate-photo.py.
#
# Every case below is either "this MUST be rejected, and for this reason" or
# "this MUST succeed". Both halves are needed: on 2026-08-14 the reject-only
# half of this suite reported 5/5 passing while every single invocation was
# dying on `import PIL`, and it was the must-succeed case that caught it.
# A guard suite without a control can go green with the whole system broken.
#
# Runs against a synthetic image, so it needs none of the photographs.
#
#   bash tools/test-photo-tools.sh

set -uo pipefail

# Not a formality. Every case below invokes tools/ by relative path, so a silent
# cd failure would turn every "this must be rejected" case into a pass — the tool
# would simply not be found. That is the exact failure this suite exists to catch,
# so it must not be reachable from the suite's own first line.
cd "$(dirname "$0")/.." || { echo "  FAIL  cannot cd to the repository root"; exit 1; }

PY="${FWRE_PY:-$HOME/fwre-work/venv/bin/python}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

SRC="$TMP/synthetic.jpg"
OUT="$TMP/out.jpg"
SPEC="$TMP/spec.json"
ERR="$TMP/err"

pass=0
fail=0

ok()   { echo "  ok    $1"; pass=$((pass + 1)); }
bad()  { echo "  FAIL  $1"; fail=$((fail + 1)); }

echo "=== interpreter ==="
if ! "$PY" -c 'import PIL' 2>/dev/null; then
  echo "  FAIL  no Pillow in $PY"
  echo "        $PY -m pip install Pillow"
  exit 1
fi
"$PY" -c 'import sys, PIL; print("  " + sys.executable + "  Pillow " + PIL.__version__)'
echo

# A noisy image, so a redacted region cannot pass the read-back check by
# accident just because the source happened to be dark there.
"$PY" - "$SRC" <<'PYEOF'
import sys
from PIL import Image
px = [((x * 7) % 256, (y * 11) % 256, ((x + y) * 13) % 256)
      for y in range(512) for x in range(512)]
im = Image.new("RGB", (512, 512))
im.putdata(px)
im.save(sys.argv[1], "JPEG", quality=92)
PYEOF

must_fail() {
  local label="$1" want="$2"; shift 2
  if "$PY" "$@" >/dev/null 2>"$ERR"; then
    bad "$label -- it PASSED and must not have"
    return
  fi
  local msg
  msg="$(head -1 "$ERR" | sed 's/^ *FAIL *//')"
  if [[ "$msg" == *"$want"* ]]; then
    ok "$label"
  else
    bad "$label -- rejected for the WRONG reason: $msg"
  fi
}

must_pass() {
  local label="$1"; shift
  if "$PY" "$@" >/dev/null 2>"$ERR"; then
    ok "$label"
  else
    bad "$label -- $(head -1 "$ERR" | sed 's/^ *FAIL *//')"
  fi
}

R=tools/redact-photo.py
A=tools/annotate-photo.py

echo "=== redact-photo: must be rejected ==="
must_fail "box outside the frame"    "outside the"              "$R" "$SRC" "$OUT" --box 400,400,200,200
must_fail "box under the minimum"    "coordinate typo"          "$R" "$SRC" "$OUT" --box 10,10,40,40
must_fail "declared size is wrong"   "expected 1024"            "$R" "$SRC" "$OUT" --box 10,10,64,64 --expect-size 1024x768
must_fail "would overwrite the input" "refusing to write over"  "$R" "$SRC" "$SRC" --box 10,10,64,64
must_fail "no box given"             "nothing would be redacted" "$R" "$SRC" "$OUT"
must_fail "input does not exist"     "does not exist"           "$R" "$TMP/nope.jpg" "$OUT" --box 10,10,64,64
echo

echo "=== redact-photo: must succeed ==="
rm -f "$OUT"
must_pass "a valid single-box redaction" "$R" "$SRC" "$OUT" --box 100,100,128,128 --expect-size 512x512
must_pass "two boxes at once" "$R" "$SRC" "$TMP/two.jpg" --box 10,10,64,64 --box 300,300,100,100
echo

echo "=== annotate-photo: must be rejected ==="
cat > "$SPEC" <<JSON
{"source": "synthetic.jpg", "expect_size": "512x512", "title": "t",
 "boxes": [{"x": 10, "y": 10, "w": 100, "h": 100,
            "label": "$(printf 'x%.0s' {1..400})"}]}
JSON
must_fail "labels that cannot be made to fit" "will not fit" "$A" "$SPEC" "$OUT"

cat > "$SPEC" <<'JSON'
{"source": "synthetic.jpg", "expect_size": "512x512", "title": "t", "boxes": []}
JSON
must_fail "empty box list" "nothing to annotate" "$A" "$SPEC" "$OUT"

cat > "$SPEC" <<'JSON'
{"source": "synthetic.jpg", "expect_size": "2048x1536", "title": "t",
 "boxes": [{"x": 10, "y": 10, "w": 100, "h": 100, "label": "a"}]}
JSON
must_fail "spec declares the wrong size" "measured against a different image" "$A" "$SPEC" "$OUT"

cat > "$SPEC" <<'JSON'
{"source": "synthetic.jpg", "expect_size": "512x512", "title": "t",
 "boxes": [{"x": 10, "y": 10, "w": 100, "h": 100, "label": "same"},
           {"x": 200, "y": 200, "w": 100, "h": 100, "label": "same"}]}
JSON
must_fail "two boxes with the same label" "same label" "$A" "$SPEC" "$OUT"
echo

echo "=== annotate-photo: must succeed ==="
cat > "$SPEC" <<'JSON'
{"source": "synthetic.jpg", "expect_size": "512x512",
 "title": "control", "subtitle": "a subtitle",
 "boxes": [{"x": 10, "y": 10, "w": 100, "h": 100, "label": "one"},
           {"x": 200, "y": 200, "w": 120, "h": 120, "label": "two"}]}
JSON
must_pass "a valid annotation render" "$A" "$SPEC" "$OUT"
echo

echo "  $pass passed, $fail failed"
[[ $fail -eq 0 ]] || exit 1
