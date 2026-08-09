import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import pytest
from artefact import check_size, CEILING


def test_passes_a_file_between_the_bounds():
    blob = b"x" * 20_000
    assert check_size(blob, "geosite.dat", floor=10_000) is blob


def test_rejects_a_file_under_the_floor():
    # The size that was actually refused by the client.
    with pytest.raises(ValueError, match="floor"):
        check_size(b"x" * 29, "geosite.dat", floor=10_000)


def test_rejects_a_file_over_the_ceiling():
    with pytest.raises(ValueError, match="ceiling"):
        check_size(b"x" * (CEILING + 1), "geoip.dat", floor=10_000)


def test_the_published_artefacts_pass_their_own_checks():
    dist = pathlib.Path(__file__).resolve().parents[1] / "dist"
    check_size((dist / "geosite.dat").read_bytes(), "geosite.dat", floor=10_000)
    check_size((dist / "geoip.dat").read_bytes(), "geoip.dat", floor=100_000)
