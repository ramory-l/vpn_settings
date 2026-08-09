"""Extract the RU address set from v2fly's geoip.dat and republish it alone.

The upstream file is ~22 MB and is fetched by the build only. Clients receive
a single-country file, because Xray parses every referenced geo file into
memory inside an iOS network extension capped at 50 MB.
"""
import pathlib
import sys
import urllib.request

from artefact import check_size
from protobuf import encode_geoip_list, iter_fields

UPSTREAM = ("https://github.com/v2fly/geoip/releases/latest/download/geoip.dat")

ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT_DIR / "dist"


def extract(blob, code):
    """Return [(ip_bytes, prefix), ...] for one country code."""
    wanted = code.upper()
    for field, entry in iter_fields(blob):
        if field != 1:
            continue
        entry_code, cidrs = None, []
        for ef, ev in iter_fields(entry):
            if ef == 1:
                entry_code = ev.decode()
            elif ef == 2:
                ip, prefix = None, None
                for cf, cv in iter_fields(ev):
                    if cf == 1:
                        ip = cv
                    elif cf == 2:
                        prefix = cv
                cidrs.append((ip, prefix))
        if entry_code and entry_code.upper() == wanted:
            return cidrs
    return []


def build(blob):
    cidrs = extract(blob, "RU")
    if not cidrs:
        raise ValueError("category RU is empty — refusing to publish")
    return encode_geoip_list([("RU", cidrs)])


def main():
    with urllib.request.urlopen(UPSTREAM, timeout=300) as response:
        upstream = response.read()
    blob = build(upstream)
    check_size(blob, "geoip.dat", floor=100_000)
    DIST.mkdir(exist_ok=True)
    (DIST / "geoip.dat").write_bytes(blob)
    print("geoip.dat: %d bytes from %d bytes upstream" % (len(blob), len(upstream)))


if __name__ == "__main__":
    sys.exit(main())
