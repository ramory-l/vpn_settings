import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import pytest
from build_geoip import extract, build
from protobuf import encode_geoip_list, iter_fields

SAMPLE = encode_geoip_list([
    ("CN", [(bytes([1, 0, 1, 0]), 24)]),
    ("RU", [(bytes([5, 8, 0, 0]), 16), (bytes([31, 6, 0, 0]), 17)]),
])


def test_extract_picks_the_requested_country():
    assert extract(SAMPLE, "RU") == [(bytes([5, 8, 0, 0]), 16), (bytes([31, 6, 0, 0]), 17)]


def test_extract_is_case_insensitive():
    assert extract(SAMPLE, "ru") == extract(SAMPLE, "RU")


def test_extract_missing_country_is_empty():
    assert extract(SAMPLE, "ZZ") == []


def test_build_emits_single_uppercase_category():
    blob = build(SAMPLE)
    codes = []
    for f, entry in iter_fields(blob):
        if f == 1:
            for ef, ev in iter_fields(entry):
                if ef == 1:
                    codes.append(ev.decode())
    assert codes == ["RU"]


def test_build_rejects_empty_result():
    with pytest.raises(ValueError, match="RU"):
        build(encode_geoip_list([("CN", [(bytes([1, 0, 1, 0]), 24)])]))
