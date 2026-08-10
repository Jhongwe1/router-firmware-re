# require-linux-workspace.sh — validate FWRE_WORK before anything writes to it.
#
# Sourced, not executed. Expects $WORK to be set and the c_err helper to exist.
#
# Why this is a hard failure and not a warning
# --------------------------------------------
# The whole analysis rests on filesystem detail that a Windows filesystem cannot
# hold. `/web/config.dat` being a *symlink* to `/var/config.dat` is the evidence
# behind the CVE-2019-19822 exposure claim, and "no setuid binaries anywhere in
# the image" is only sayable if setuid bits survived extraction. Extract onto
# DrvFs and both facts quietly become something else — the run still succeeds,
# the reports still generate, and the conclusions are wrong. There is no useful
# degraded mode here.
#
# Three ways this has actually gone wrong, in the order they were found:
#
#   FWRE_WORK=/mnt/c/...       DrvFs. Loses symlinks and mode bits.
#   FWRE_WORK=C:\Users\me      $HOME leaked from Windows into WSL (WSLENV, or a
#                              `wsl` invocation inheriting the caller's HOME).
#                              On a DrvFs mount the backslashes are stripped and
#                              you get a directory literally named `C:Usersme`
#                              inside the repository — which is how this check
#                              came to be written.
#   FWRE_WORK=relative/path    Resolves against whatever the caller's cwd was.
#
# W01's recurring lesson was that silent acceptance of a bad value costs more
# than a loud refusal. This is that lesson, applied to the one input every
# artefact path is built from.

case "$WORK" in
  '') c_err "FWRE_WORK is empty."
      exit 2 ;;
  [A-Za-z]:*|*\\*)
      c_err "FWRE_WORK=$WORK looks like a Windows path."
      c_err "This usually means HOME leaked from Windows into WSL."
      c_err "Check: 'echo \$HOME' inside WSL should print /home/<user>."
      c_err "Fix:   unset WSLENV's HOME passthrough, or set FWRE_WORK explicitly."
      exit 2 ;;
  /mnt/*)
      c_err "FWRE_WORK=$WORK is on a Windows drive mount."
      c_err "SquashFS extraction there loses symlinks and mode bits, and this"
      c_err "analysis depends on both — see docs/workspace-layout.md."
      exit 2 ;;
  /*) ;;
  *)  c_err "FWRE_WORK=$WORK is not an absolute path."
      c_err "It would resolve against the caller's working directory."
      exit 2 ;;
esac
