import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import pytest
from build_geosite import parse_list, build
from protobuf import iter_fields, ROOT, FULL, REGEX, PLAIN


def categories(blob):
    out = {}
    for f, entry in iter_fields(blob):
        if f != 1:
            continue
        code, domains = None, []
        for ef, ev in iter_fields(entry):
            if ef == 1:
                code = ev.decode()
            elif ef == 2:
                dtype = value = None
                for df, dv in iter_fields(ev):
                    if df == 1:
                        dtype = dv
                    elif df == 2:
                        value = dv.decode()
                domains.append((dtype, value))
        out[code] = domains
    return out


def test_parse_bare_domain_is_root():
    assert parse_list("ozon.ru\n", lambda n: "") == [(ROOT, "ozon.ru")]


def test_parse_prefixes():
    text = "domain:a.ru\nfull:www.b.ru\nregexp:^c\\.ru$\nkeyword:dee\n"
    assert parse_list(text, lambda n: "") == [
        (ROOT, "a.ru"), (FULL, "www.b.ru"), (REGEX, "^c\\.ru$"), (PLAIN, "dee"),
    ]


def test_parse_strips_comments_and_attributes():
    text = "# comment\n\na.ru @cn\nb.ru  # trailing\n"
    assert parse_list(text, lambda n: "") == [(ROOT, "a.ru"), (ROOT, "b.ru")]


def test_parse_follows_include_without_looping():
    files = {"one": "include:two\na.ru\n", "two": "include:one\nb.ru\n"}
    assert parse_list(files["one"], files.get, seen={"one"}) == [(ROOT, "b.ru"), (ROOT, "a.ru")]


BASE_LOCAL = {
    "ru-direct.categories": "cat-a\n",
    "ru-direct.extra": "domain:ru\ndomain:su\n",
    "bulk-cdn": "steamcontent.com\n",
    "override-proxy": "broken.ru\n",
}

UPSTREAM = {"cat-a": "a.ru\n"}


def test_build_emits_three_uppercase_categories():
    cats = categories(build(fetch=UPSTREAM.__getitem__, local=BASE_LOCAL))
    assert set(cats) == {"RU-DIRECT", "BULK-CDN", "OVERRIDE-PROXY"}
    assert cats["BULK-CDN"] == [(ROOT, "steamcontent.com")]


def test_ru_direct_merges_upstream_with_local_extras():
    cats = categories(build(fetch=UPSTREAM.__getitem__, local=BASE_LOCAL))
    assert cats["RU-DIRECT"] == [(ROOT, "a.ru"), (ROOT, "ru"), (ROOT, "su")]


def test_build_rejects_ru_direct_with_no_upstream_entries():
    # sources/ru-direct.extra alone would keep the category non-empty, so a guard
    # on the merged list would publish a two-entry RU-DIRECT and hide a total
    # upstream failure — the exact silent breakage the guard exists to catch.
    with pytest.raises(ValueError, match="upstream"):
        build(fetch=lambda name: "", local=BASE_LOCAL)


def test_build_substitutes_a_sentinel_for_empty_optional_categories():
    cats = categories(build(
        fetch=UPSTREAM.__getitem__,
        local={**BASE_LOCAL,
               "bulk-cdn": "# nothing verified yet\n",
               "override-proxy": "# nothing to repair\n"},
    ))
    assert cats["BULK-CDN"] == [(ROOT, "none.invalid")]
    assert cats["OVERRIDE-PROXY"] == [(ROOT, "none.invalid")]
