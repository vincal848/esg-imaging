"""fetch_data.py: checksum mismatch is an error for versioned files, a warning otherwise."""

import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest

import fetch_data


def test_checksum_mismatch_policy(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fetch_data, "RAW", str(tmp_path))
    (tmp_path / "f.txt").write_bytes(b"abc")  # already present: no network
    good = hashlib.sha256(b"abc").hexdigest()
    fetch_data.fetch("f.txt", "http://unused", good, True)
    with pytest.raises(SystemExit):
        fetch_data.fetch("f.txt", "http://unused", "0" * 64, True)
    fetch_data.fetch("f.txt", "http://unused", "0" * 64, False)
    assert "WARNING" in capsys.readouterr().err


def test_every_hansen_tile_is_pinned():
    assert len(fetch_data.TILES) == 22 and all(len(h) == 64 for h in fetch_data.TILES.values())
