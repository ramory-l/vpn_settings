import sys, pathlib, base64, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import pytest
from render_profile import render, to_link

TEMPLATE = {
    "Name": "RU-Direct",
    "LastUpdated": 0,
    "GlobalProxy": "true",
    "DomainStrategy": "IPIfNonMatch",
    "Geositeurl": "{base_url}/geosite.dat",
    "Geoipurl": "{base_url}/geoip.dat",
    "DirectSites": ["geosite:ru-direct"],
}


def test_render_stamps_last_updated():
    out = render(TEMPLATE, now=1754740000, base_url="https://example.test/x")
    assert out["LastUpdated"] == 1754740000


def test_render_substitutes_base_url():
    out = render(TEMPLATE, now=1, base_url="https://example.test/x")
    assert out["Geositeurl"] == "https://example.test/x/geosite.dat"
    assert out["Geoipurl"] == "https://example.test/x/geoip.dat"


def test_render_does_not_mutate_the_template():
    render(TEMPLATE, now=1, base_url="https://example.test/x")
    assert TEMPLATE["LastUpdated"] == 0
    assert TEMPLATE["Geositeurl"] == "{base_url}/geosite.dat"


def test_render_rejects_a_template_with_unset_placeholder():
    bad = dict(TEMPLATE, Geositeurl="https://raw.githubusercontent.com/<owner>/<repo>/main/geosite.dat")
    with pytest.raises(ValueError, match="placeholder"):
        render(bad, now=1, base_url="https://example.test/x")


def test_to_link_is_the_onadd_form_and_decodes_back():
    profile = render(TEMPLATE, now=42, base_url="https://example.test/x")
    link = to_link(profile)
    assert link.startswith("incy://routing/onadd/")
    payload = base64.b64decode(link[len("incy://routing/onadd/"):])
    assert json.loads(payload)["LastUpdated"] == 42


def test_to_link_emits_compact_json():
    link = to_link(render(TEMPLATE, now=42, base_url="https://example.test/x"))
    payload = base64.b64decode(link[len("incy://routing/onadd/"):]).decode()
    assert ", " not in payload and '": ' not in payload


def test_the_shipped_template_renders_cleanly():
    """Guard the file that is actually published, not just the fixture above."""
    path = pathlib.Path(__file__).resolve().parents[1] / "profile" / "profile.template.json"
    out = render(json.loads(path.read_text()), now=7,
                 base_url="https://raw.githubusercontent.com/ramory-l/vpn_settings/main/dist")
    assert out["RouteOrder"] == "block-proxy-direct"
    # Key casing is exact: the client silently ignores a miscased key and
    # substitutes its own default, which is invisible when they agree.
    assert "UseChunkFiles" in out and "useChunkFiles" not in out
    assert out["DomesticDNSType"] == "DoU" and out["RemoteDNSType"] == "DoH"
    assert out["DomesticDNSIP"] == "77.88.8.8"
    assert out["Geositeurl"].endswith("/dist/geosite.dat")
    assert "geosite:override-proxy" in out["ProxySites"]
    assert {"geosite:ru-direct", "geosite:bulk-cdn"} <= set(out["DirectSites"])
    assert "geoip:ru" in out["DirectIp"]
    assert "{base_url}" not in json.dumps(out)
