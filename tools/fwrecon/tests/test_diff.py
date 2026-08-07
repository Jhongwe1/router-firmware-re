"""Tests for the cross-version diff."""

from __future__ import annotations

import json

from fwrecon import diff


def _report(label, *, handlers, binaries, exec_bins, symlinks, sha,
            docroot_symlinks=()):
    links = [{"path": p, "target": t, "reason": "x", "in_docroot": False}
             for p, t in symlinks]
    links += [{"path": p, "target": t, "reason": "x", "in_docroot": True}
              for p, t in docroot_symlinks]
    return {
        "label": label,
        "image_sha256": sha,
        "rootfs": {
            "web_server": "/bin/boa",
            "handlers": handlers,
            "binaries": [{"path": p, "needed": ["libc.so.0"]} for p in binaries],
            "command_exec_binaries": exec_bins,
            "suspect_symlinks": links,
            "init_findings": [],
        },
    }


def _write(tmp_path, name, obj):
    p = tmp_path / name
    p.write_text(json.dumps(obj), "utf-8")
    return p


def test_detects_removed_binary(tmp_path):
    old = _write(tmp_path, "old.json", _report(
        "2015", handlers=["formLogin"], binaries=["/bin/boa", "/bin/skt"],
        exec_bins=["/bin/boa", "/bin/skt"], symlinks=[], sha="a"))
    new = _write(tmp_path, "new.json", _report(
        "2020", handlers=["formLogin"], binaries=["/bin/boa"],
        exec_bins=["/bin/boa"], symlinks=[], sha="b"))

    d = diff.compare(old, new)
    bins = next(c for c in d["changes"] if c["category"] == "binaries")
    assert bins["removed"] == ["/bin/skt"]
    assert bins["added"] == []


def test_detects_added_handler(tmp_path):
    old = _write(tmp_path, "old.json", _report(
        "2015", handlers=["formLogin"], binaries=["/bin/boa"],
        exec_bins=[], symlinks=[], sha="a"))
    new = _write(tmp_path, "new.json", _report(
        "2020", handlers=["formLogin", "formAjaxGet"], binaries=["/bin/boa"],
        exec_bins=[], symlinks=[], sha="b"))

    d = diff.compare(old, new)
    h = next(c for c in d["changes"] if c["category"] == "web handlers")
    assert h["added"] == ["formAjaxGet"]


def test_symlink_appearing_in_newer_build_is_reported(tmp_path):
    """The exposure introduced between builds is the headline result of a diff,
    so it must not be buried in an 'unchanged' bucket."""
    old = _write(tmp_path, "old.json", _report(
        "2015", handlers=[], binaries=[], exec_bins=[], symlinks=[], sha="a"))
    new = _write(tmp_path, "new.json", _report(
        "2020", handlers=[], binaries=[], exec_bins=[], symlinks=[], sha="b",
        docroot_symlinks=[("/web/config.dat", "/var/config.dat")]))

    d = diff.compare(old, new)
    s = next(c for c in d["changes"]
             if c["category"].startswith("symlinks exposing runtime state"))
    assert s["added"] == ["/web/config.dat -> /var/config.dat"]


def test_docroot_and_plumbing_symlinks_are_separate_categories(tmp_path):
    """A dozen /usr/share/udhcpc hooks pointing at /var must not sit in the same
    bucket as /web/config.dat, or the signal is lost in the noise."""
    old = _write(tmp_path, "old.json", _report(
        "2015", handlers=[], binaries=[], exec_bins=[], symlinks=[], sha="a"))
    new = _write(tmp_path, "new.json", _report(
        "2020", handlers=[], binaries=[], exec_bins=[],
        symlinks=[("/usr/share/udhcpc/usb0.deconfig", "/var/udhcpc/usb0.deconfig")],
        docroot_symlinks=[("/web/config.dat", "/var/config.dat")], sha="b"))

    d = diff.compare(old, new)
    docroot = next(c for c in d["changes"]
                   if c["category"].startswith("symlinks exposing runtime state"))
    other = next(c for c in d["changes"]
                 if c["category"].startswith("other symlinks"))
    assert docroot["added"] == ["/web/config.dat -> /var/config.dat"]
    assert "udhcpc" in other["added"][0]


def test_identical_reports_produce_no_changes(tmp_path):
    body = _report("x", handlers=["formLogin"], binaries=["/bin/boa"],
                   exec_bins=["/bin/boa"], symlinks=[], sha="a")
    old = _write(tmp_path, "old.json", body)
    new = _write(tmp_path, "new.json", dict(body, label="y", image_sha256="b"))
    d = diff.compare(old, new)
    assert d["changes"] == []
    assert "web handlers" in d["unchanged_categories"]


def test_markdown_render(tmp_path):
    old = _write(tmp_path, "old.json", _report(
        "2015", handlers=[], binaries=["/bin/skt"], exec_bins=[], symlinks=[], sha="a"))
    new = _write(tmp_path, "new.json", _report(
        "2020", handlers=[], binaries=[], exec_bins=[], symlinks=[], sha="b"))
    md = diff.to_markdown(diff.compare(old, new))
    assert "2015 -> 2020" in md
    assert "- /bin/skt" in md
