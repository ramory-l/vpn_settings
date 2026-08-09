"""Size checks every published .dat file must pass.

Both bounds exist because both ends are failure modes on the client, and neither
is visible from the build alone.

Ceiling: Xray parses referenced geo files into memory inside a
NEPacketTunnelProvider capped at 50 MB on iOS 15+, so an oversized file stops the
tunnel from starting rather than merely slowing it.

Floor: INCY refuses a downloaded geo file below an undocumented minimum — a
29-byte probe was rejected with "Downloaded file is too small (29 bytes)", while
the 15,291-byte geosite.dat and 346,187-byte geoip.dat were accepted. The client
then falls back to its bundled data, Xray cannot resolve our category names, and
the user is shown a dialog offering to start without any routing rules.

The exact threshold is unknown, so the floor is a heuristic: above the only
value known to be rejected, below the smallest value known to be accepted. It
earns its place independently of the client, because a file that shrinks past it
has lost most of its content and should not be published either way.
"""

CEILING = 1_000_000


def check_size(blob, name, floor):
    if len(blob) < floor:
        raise ValueError(
            "%s is %d bytes, under the %d byte floor — the lists have collapsed, "
            "and a file this small is refused by the client" % (name, len(blob), floor))
    if len(blob) > CEILING:
        raise ValueError(
            "%s is %d bytes, over the %d byte ceiling" % (name, len(blob), CEILING))
    return blob
