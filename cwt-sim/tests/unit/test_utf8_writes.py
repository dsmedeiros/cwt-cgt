"""UTF-8 write/read smoke tests."""

from pathlib import Path


def test_tmp_utf8_write_read(tmp_path: Path) -> None:
    sample = "rho: ρ, zeta: ζ, tau: τ"
    path = tmp_path / "tmp_utf8_test.txt"
    path.write_text(sample, encoding="utf-8")

    contents = path.read_text(encoding="utf-8")

    assert "ρ" in contents
    assert contents == sample
