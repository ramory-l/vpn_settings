# Routing rules

Geo files and the INCY routing profile for the RU-direct split: Russian destinations and
bulk-download CDNs are routed directly from the client, everything else keeps using the cascade.

- `sources/` — hand-maintained lists. Edit these.
- `dist/` — published artefacts. Generated; never edit by hand.
- `tools/` — build scripts. Python standard library only.
- `profile/` — the routing profile template.

Artefacts are served from
`https://raw.githubusercontent.com/ramory-l/vpn_settings/main/dist/`, rebuilt daily by
`.github/workflows/build.yml`.

## Changing a routing decision

1. Edit `sources/bulk-cdn` or `sources/override-proxy`.
2. Push. The workflow rebuilds `dist/` and its `.sha256` sidecars.
3. Clients pick the change up on their next subscription refresh.

No profile change and no user action are needed for list edits. Note that the refresh is not
immediate — a correction propagates on the client's schedule, not on yours.

`sources/override-proxy` is the repair mechanism: a domain listed there is forced through the
cascade even though a broader direct list matches it. This works because `RouteOrder` is
`block-proxy-direct`, so proxy rules are evaluated before direct ones.

## Changing the profile itself

Adding a list, changing `RouteOrder` or adding DNS requires a new profile:

```bash
python3 tools/render_profile.py --base-url https://raw.githubusercontent.com/ramory-l/vpn_settings/main/dist
```

Paste the output into 3x-ui → Subscription settings → Incy tab → `Routing rules`, with
`Enable routing` on and the Happ tab's `Routing rules` left empty. Populating both is a
misconfiguration: INCY reads the header before the body, so the header wins silently and the
Incy field looks broken.

`LastUpdated` is stamped by the script. Never hand-edit the payload: INCY applies an update
only when `LastUpdated` is greater than the stored value, so an un-stamped edit is a silent
no-op.

## Build guarantees

- Each `.dat` stays under 1 MB. Xray parses referenced geo files into memory inside a
  `NEPacketTunnelProvider` capped at 50 MB on iOS 15+, so oversized files break the tunnel
  rather than merely slowing it.
- The build exits non-zero if `RU-DIRECT` has no upstream entries. The check covers the
  upstream portion specifically — `sources/ru-direct.extra` contributes the `.ru`/`.su`
  suffixes unconditionally and would otherwise mask a total upstream failure.
- `BULK-CDN` and `OVERRIDE-PROXY` are legitimately empty. They get a `none.invalid` sentinel
  so the category exists for the profile to reference; the reserved TLD can never match a real
  lookup.
