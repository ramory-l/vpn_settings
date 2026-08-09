import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

from protobuf import (
    encode_varint, field_varint, field_bytes, field_string,
    encode_geosite_list, encode_geoip_list, iter_fields,
    PLAIN, REGEX, ROOT, FULL,
)


def test_varint_single_byte():
    assert encode_varint(0) == b"\x00"
    assert encode_varint(1) == b"\x01"
    assert encode_varint(127) == b"\x7f"


def test_varint_multi_byte():
    assert encode_varint(128) == b"\x80\x01"
    assert encode_varint(300) == b"\xac\x02"


def test_field_headers():
    # field 1, wire type 0 -> tag byte 0x08
    assert field_varint(1, 3) == b"\x08\x03"
    # field 2, wire type 2 -> tag byte 0x12
    assert field_bytes(2, b"ab") == b"\x12\x02ab"
    assert field_string(1, "RU") == b"\x0a\x02RU"


def test_geosite_roundtrip():
    blob = encode_geosite_list([("RU-DIRECT", [(ROOT, "ozon.ru"), (FULL, "www.vk.com")])])
    entries = [v for f, v in iter_fields(blob) if f == 1]
    assert len(entries) == 1

    code, domains = None, []
    for f, v in iter_fields(entries[0]):
        if f == 1:
            code = v.decode()
        elif f == 2:
            dtype, value = None, None
            for df, dv in iter_fields(v):
                if df == 1:
                    dtype = dv
                elif df == 2:
                    value = dv.decode()
            domains.append((dtype, value))

    assert code == "RU-DIRECT"
    assert domains == [(ROOT, "ozon.ru"), (FULL, "www.vk.com")]


def test_geoip_roundtrip():
    blob = encode_geoip_list([("RU", [(bytes([5, 8, 0, 0]), 16)])])
    entries = [v for f, v in iter_fields(blob) if f == 1]
    code, cidrs = None, []
    for f, v in iter_fields(entries[0]):
        if f == 1:
            code = v.decode()
        elif f == 2:
            ip, prefix = None, None
            for cf, cv in iter_fields(v):
                if cf == 1:
                    ip = cv
                elif cf == 2:
                    prefix = cv
            cidrs.append((ip, prefix))

    assert code == "RU"
    assert cidrs == [(bytes([5, 8, 0, 0]), 16)]


def test_match_type_constants():
    assert (PLAIN, REGEX, ROOT, FULL) == (0, 1, 2, 3)
