"""Minimal protobuf writer/reader for the v2ray geosite and geoip schemas.

Hand-rolled so the build has no third-party runtime dependency. Only the two
wire types the schemas use are supported: varint (0) and length-delimited (2).
"""

PLAIN, REGEX, ROOT, FULL = 0, 1, 2, 3


def encode_varint(value):
    out = bytearray()
    while True:
        chunk = value & 0x7F
        value >>= 7
        if value:
            out.append(chunk | 0x80)
        else:
            out.append(chunk)
            return bytes(out)


def _tag(field, wire):
    return encode_varint((field << 3) | wire)


def field_varint(field, value):
    return _tag(field, 0) + encode_varint(value)


def field_bytes(field, value):
    return _tag(field, 2) + encode_varint(len(value)) + value


def field_string(field, value):
    return field_bytes(field, value.encode("utf-8"))


def _encode_domain(dtype, value):
    return field_varint(1, dtype) + field_string(2, value)


def encode_geosite_list(entries):
    """entries: [(country_code, [(match_type, domain), ...]), ...]"""
    out = b""
    for code, domains in entries:
        body = field_string(1, code)
        for dtype, value in domains:
            body += field_bytes(2, _encode_domain(dtype, value))
        out += field_bytes(1, body)
    return out


def _encode_cidr(ip, prefix):
    return field_bytes(1, ip) + field_varint(2, prefix)


def encode_geoip_list(entries):
    """entries: [(country_code, [(ip_bytes, prefix_len), ...]), ...]"""
    out = b""
    for code, cidrs in entries:
        body = field_string(1, code)
        for ip, prefix in cidrs:
            body += field_bytes(2, _encode_cidr(ip, prefix))
        out += field_bytes(1, body)
    return out


def read_varint(buf, pos):
    result, shift = 0, 0
    while True:
        byte = buf[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7


def iter_fields(buf, pos=0, end=None):
    """Yield (field_number, value) for one protobuf message."""
    if end is None:
        end = len(buf)
    while pos < end:
        key, pos = read_varint(buf, pos)
        field, wire = key >> 3, key & 0x07
        if wire == 0:
            value, pos = read_varint(buf, pos)
            yield field, value
        elif wire == 2:
            length, pos = read_varint(buf, pos)
            yield field, buf[pos:pos + length]
            pos += length
        else:
            raise ValueError("unsupported wire type %d in field %d" % (wire, field))
