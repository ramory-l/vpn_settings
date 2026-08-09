"""Render the INCY routing profile and its subscription header value.

LastUpdated is stamped here and nowhere else. INCY applies an updated profile
only when LastUpdated is strictly greater than the stored value, so a payload
edited by hand without a bump is a silent no-op.
"""
import argparse
import base64
import json
import pathlib
import sys
import time

ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT_DIR / "profile" / "profile.template.json"

LINK_PREFIX = "incy://routing/onadd/"


def render(template, now, base_url):
    profile = json.loads(json.dumps(template))  # deep copy, stdlib only
    profile["LastUpdated"] = now
    for key in ("Geositeurl", "Geoipurl"):
        value = profile.get(key)
        if value is None:
            continue
        if "<owner>" in value or "<repo>" in value:
            raise ValueError("%s still contains a placeholder: %s" % (key, value))
        profile[key] = value.replace("{base_url}", base_url)
    return profile


def to_link(profile):
    payload = json.dumps(profile, separators=(",", ":"), sort_keys=True)
    return LINK_PREFIX + base64.b64encode(payload.encode("utf-8")).decode("ascii")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render the INCY routing profile link.")
    parser.add_argument("--base-url", required=True,
                        help="Directory URL that serves geosite.dat and geoip.dat")
    args = parser.parse_args(argv)

    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    profile = render(template, now=int(time.time()), base_url=args.base_url.rstrip("/"))
    print(to_link(profile))


if __name__ == "__main__":
    sys.exit(main())
