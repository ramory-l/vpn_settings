"""Build geosite.dat from upstream v2fly category files plus local lists.

Emits exactly three categories: RU-DIRECT, BULK-CDN, OVERRIDE-PROXY.
Upstream category names never appear in the routing profile, so an upstream
rename changes only sources/ru-direct.categories.
"""
import pathlib
import sys
import urllib.request

from protobuf import encode_geosite_list, PLAIN, REGEX, ROOT, FULL

V2FLY_DATA = "https://raw.githubusercontent.com/v2fly/domain-list-community/master/data/"
RUNETFREEDOM = ("https://raw.githubusercontent.com/runetfreedom/"
                "russia-domains-list/main/")

ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
SOURCES = ROOT_DIR / "sources"
DIST = ROOT_DIR / "dist"

PREFIXES = (("domain:", ROOT), ("full:", FULL), ("regexp:", REGEX), ("keyword:", PLAIN))

# RFC 2606 reserves .invalid, so this can never match a real lookup.
SENTINEL = (ROOT, "none.invalid")


def parse_list(text, fetch, seen=None):
    """Parse one v2fly list file into [(match_type, value), ...]."""
    if seen is None:
        seen = set()
    out = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        line = line.split()[0].split("@", 1)[0]
        if not line:
            continue
        if line.startswith("include:"):
            name = line[len("include:"):]
            if name in seen:
                continue
            seen.add(name)
            out.extend(parse_list(fetch(name), fetch, seen))
            continue
        for prefix, dtype in PREFIXES:
            if line.startswith(prefix):
                out.append((dtype, line[len(prefix):]))
                break
        else:
            out.append((ROOT, line))
    return out


def _dedupe(pairs):
    seen, out = set(), []
    for pair in pairs:
        if pair not in seen:
            seen.add(pair)
            out.append(pair)
    return out


def _optional(pairs):
    """Return `pairs`, or a sentinel if it is empty.

    BULK-CDN holds nothing until verification finishes, and OVERRIDE-PROXY is
    empty whenever nothing needs repairing — but the routing profile names both
    categories. A category missing from geosite.dat makes Xray reject the rule
    that references it, so emit an unresolvable domain instead: the category
    exists and matches nothing.
    """
    return _dedupe(pairs) or [SENTINEL]


def build(fetch, local):
    """Return geosite.dat bytes. `fetch(name)` returns an upstream list body."""
    seen = set()
    upstream = []
    for line in local["ru-direct.categories"].splitlines():
        name = line.split("#", 1)[0].strip()
        if not name or name in seen:
            continue
        seen.add(name)
        upstream.extend(parse_list(fetch(name), fetch, seen))

    # Guard the upstream portion rather than the merged list. ru-direct.extra
    # contributes entries unconditionally, so a check on the merge would never
    # fire and a total upstream failure would publish silently.
    if not upstream:
        raise ValueError("RU-DIRECT has no upstream entries — refusing to publish")

    ru_direct = upstream + parse_list(local["ru-direct.extra"], fetch)

    return encode_geosite_list([
        ("RU-DIRECT", _dedupe(ru_direct)),
        ("BULK-CDN", _optional(parse_list(local["bulk-cdn"], fetch))),
        ("OVERRIDE-PROXY", _optional(parse_list(local["override-proxy"], fetch))),
    ])


def _fetch(name):
    base = RUNETFREEDOM if name == "ru-available-only-inside" else V2FLY_DATA
    with urllib.request.urlopen(base + name, timeout=60) as response:
        return response.read().decode("utf-8")


def main():
    local = {n: (SOURCES / n).read_text(encoding="utf-8")
             for n in ("ru-direct.categories", "ru-direct.extra",
                       "bulk-cdn", "override-proxy")}
    blob = build(_fetch, local)
    if len(blob) > 1_000_000:
        raise ValueError("geosite.dat is %d bytes, over the 1 MB budget" % len(blob))
    DIST.mkdir(exist_ok=True)
    (DIST / "geosite.dat").write_bytes(blob)
    print("geosite.dat: %d bytes" % len(blob))


if __name__ == "__main__":
    sys.exit(main())
