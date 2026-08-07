"""Tests for the root-filesystem inventory.

Each test builds the minimum filesystem that exhibits one real property observed
in the TOTOLINK images, so a regression here corresponds to losing a finding.
"""

from __future__ import annotations

import os
import sys

import pytest

from fwrecon import report, rootfs

from .fixtures import build_mips_be_elf

# The suspect-symlink logic is the core of the config.dat finding and depends on
# real symlinks; on Windows those need developer mode or admin.
needs_symlinks = pytest.mark.skipif(
    sys.platform == "win32", reason="symlink creation is privileged on Windows")


def make_rootfs(tmp_path, *, with_config_symlink=False, skt_commented=False,
                docroot="/web"):
    root = tmp_path / "squashfs-root"
    for d in ("bin", "etc/init.d", "etc/boa", "lib", "web", "var"):
        (root / d).mkdir(parents=True, exist_ok=True)

    boa = root / "bin/boa"
    boa.write_bytes(
        build_mips_be_elf(imports=("system", "popen", "strcpy", "sprintf"))
        + b"\x00Boa/0.94.14rc21\x00formLogin\x00formSysCmd\x00formWsc\x00"
          b"fromStaticDHCP\x00format\x00")
    boa.chmod(0o755)

    busybox = root / "bin/busybox"
    busybox.write_bytes(build_mips_be_elf(imports=("strcpy",)))
    busybox.chmod(0o755)

    (root / "etc/boa/boa.conf").write_text(
        f"Port 80\nUser root\nDocumentRoot {docroot}\nCGIPath /bin:/usr/bin\n")

    rcs = ["#!/bin/sh", "mkdir /var/web", "boa"]
    rcs.append("#skt&" if skt_commented else "skt&")
    rcs.append("#telnetd &")
    (root / "etc/init.d/rcS").write_text("\n".join(rcs) + "\n")

    (root / "bin/skt").write_bytes(build_mips_be_elf(imports=("system",)))
    (root / "bin/skt").chmod(0o755)

    if with_config_symlink:
        os.symlink("/var/config.dat", root / "web/config.dat")
    return root


def test_finds_web_server_and_banner(tmp_path):
    r = rootfs.analyse(make_rootfs(tmp_path))
    assert r.web_server == "/bin/boa"
    assert r.web_server_banner == "Boa/0.94.14rc21"


def test_reads_document_root_from_boa_conf(tmp_path):
    r = rootfs.analyse(make_rootfs(tmp_path, docroot="/var/web"))
    assert r.document_root == "/var/web"


def test_extracts_form_handlers_and_drops_stopwords(tmp_path):
    r = rootfs.analyse(make_rootfs(tmp_path))
    assert "formLogin" in r.handlers
    assert "formSysCmd" in r.handlers
    # 'fromStaticDHCP' is a vendor typo that shipped and is a real endpoint.
    assert "fromStaticDHCP" in r.handlers
    # 'format' is an ordinary libc string, not a handler.
    assert "format" not in r.handlers


def test_binaries_with_command_exec_sinks_listed(tmp_path):
    r = rootfs.analyse(make_rootfs(tmp_path))
    assert "/bin/boa" in r.command_exec_binaries
    assert "/bin/skt" in r.command_exec_binaries
    assert "/bin/busybox" not in r.command_exec_binaries


@needs_symlinks
def test_docroot_symlink_into_var_is_flagged_high(tmp_path):
    """`/web/config.dat -> /var/config.dat` is the exposure path behind
    CVE-2019-19822 and must be surfaced as a high-severity observation."""
    r = rootfs.analyse(make_rootfs(tmp_path, with_config_symlink=True))
    hits = [s for s in r.suspect_symlinks if s.path == "/web/config.dat"]
    assert hits, "docroot symlink into /var was not flagged"
    assert "writable" in hits[0].reason

    rep = report.build("t", rootfs=r)
    high = [f for f in rep.findings if f["severity"] == "high"]
    assert any("config.dat" in f["detail"] for f in high)


@needs_symlinks
def test_plumbing_symlink_outside_docroot_is_not_high(tmp_path):
    """`/etc/boa -> /var/boa` is normal read-only-rootfs plumbing. Ranking it
    beside `/web/config.dat` would bury the finding that matters."""
    root = make_rootfs(tmp_path)
    os.symlink("/var/boa", root / "etc/boa2")
    r = rootfs.analyse(root)
    link = next(s for s in r.suspect_symlinks if s.path == "/etc/boa2")
    assert link.in_docroot is False
    rep = report.build("t", rootfs=r)
    assert not [f for f in rep.findings if f["severity"] == "high"]


def test_binary_init_file_is_not_parsed_as_a_script(tmp_path):
    """`/init` is a busybox ELF on these images; grepping it as text emitted
    decompiled garbage into the report."""
    root = make_rootfs(tmp_path)
    (root / "init").write_bytes(build_mips_be_elf() + b"\x00telnetd boa skt\x00")
    r = rootfs.analyse(root)
    assert not any(f.file == "/init" for f in r.init_findings)


@needs_symlinks
def test_no_symlink_means_no_high_finding(tmp_path):
    r = rootfs.analyse(make_rootfs(tmp_path, with_config_symlink=False))
    rep = report.build("t", rootfs=r)
    assert not [f for f in rep.findings if f["severity"] == "high"]


def test_commented_out_service_is_reported_as_disabled(tmp_path):
    """The 2015 image disables its backdoor by commenting one init line while
    still shipping /bin/skt. Reporting only what runs would call that clean."""
    r = rootfs.analyse(make_rootfs(tmp_path, skt_commented=True))
    assert "skt" in r.disabled_services
    assert any(b.path == "/bin/skt" for b in r.binaries)
    assert any("disabled only by commenting" in n for n in r.notes)


def test_enabled_service_not_listed_as_disabled(tmp_path):
    r = rootfs.analyse(make_rootfs(tmp_path, skt_commented=False))
    assert "skt" not in r.disabled_services


def test_init_findings_record_line_numbers_and_comment_state(tmp_path):
    r = rootfs.analyse(make_rootfs(tmp_path, skt_commented=True))
    by_line = {f.line: f for f in r.init_findings}
    assert by_line["#skt&"].commented is True
    assert by_line["boa"].commented is False


def test_missing_etc_passwd_produces_a_note(tmp_path):
    r = rootfs.analyse(make_rootfs(tmp_path))
    assert any("No /etc/passwd" in n for n in r.notes)


def test_binary_hardening_recorded(tmp_path):
    r = rootfs.analyse(make_rootfs(tmp_path))
    boa = next(b for b in r.binaries if b.path == "/bin/boa")
    assert boa.endian == "big"
    assert boa.load_base == "0x00400000"
    assert boa.hardening["nx"] is None
    assert boa.hardening["canary"] is False


def test_report_renders_markdown_without_error(tmp_path):
    r = rootfs.analyse(make_rootfs(tmp_path))
    md = report.to_markdown(report.build("v-test", rootfs=r))
    assert "# Firmware recon" in md
    assert "formLogin" in md
    assert "/bin/boa" in md


def test_report_json_round_trips(tmp_path):
    import json
    r = rootfs.analyse(make_rootfs(tmp_path))
    d = json.loads(report.to_json(report.build("v-test", rootfs=r)))
    assert d["schema_version"] == report.SCHEMA_VERSION
    assert d["rootfs"]["web_server"] == "/bin/boa"


def test_iter_strings_matches_expectations():
    data = b"\x00\x01ab\x00hello world\x00\xff\xfeshort\x00"
    got = list(rootfs.iter_strings(data, min_len=4))
    assert "hello world" in got
    assert "short" in got
    assert "ab" not in got
