#!/usr/bin/env python3
"""Fold extra XMLTV guides into our guide.

Usage: merge_guides.py <our_guide.xml> <extra_guides.txt> <output.xml.gz>

Streams each guide line by line, keeping <channel> and <programme> elements.
Channels already in our guide are not duplicated; a guide that fails is skipped.
"""
import gzip
import io
import re
import sys
import urllib.request

ours, guides_path, out_path = sys.argv[1:4]
urls = [u.strip() for u in open(guides_path, encoding="utf-8") if u.strip()]

chan_re = re.compile(r'<channel\s+id="([^"]+)"')
prog_re = re.compile(r'<programme\b[^>]*\bchannel="([^"]+)"')
selfclose_re = re.compile(r'^\s*<(channel|programme)\b[^>]*/>\s*$')


def elements(fh):
    """Yield (kind, id, text) for each <channel> / <programme> element."""
    buf, kind, end = [], None, None
    for raw in fh:
        line = raw.decode("utf-8", "ignore") if isinstance(raw, bytes) else raw
        if kind is None:
            s = line.lstrip()
            if s.startswith("<channel"):
                kind, end = "channel", "</channel>"
            elif s.startswith("<programme"):
                kind, end = "programme", "</programme>"
            else:
                continue
        buf.append(line)
        if end in line or (len(buf) == 1 and selfclose_re.match(line)):
            text = "".join(buf)
            m = (chan_re if kind == "channel" else prog_re).search(text)
            yield kind, (m.group(1) if m else None), text
            buf, kind = [], None


def open_guide(src):
    if src.startswith(("http://", "https://")):
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
        fh = urllib.request.urlopen(req, timeout=120)
    else:
        fh = open(src, "rb")
    data = fh.read()
    fh.close()
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return io.BytesIO(data)


with gzip.open(out_path, "wt", encoding="utf-8") as out:
    out.write('<?xml version="1.0" encoding="UTF-8"?>\n<tv>\n')
    have = set()
    # our guide first; its channels win
    for kind, cid, text in elements(open_guide(ours)):
        if kind == "channel":
            have.add(cid)
        out.write(text)
    base = set(have)
    for url in urls:
        try:
            added = 0
            for kind, cid, text in elements(open_guide(url)):
                if cid in base:
                    continue  # we already have listings for this channel
                if kind == "channel":
                    if cid in have:
                        continue
                    have.add(cid)
                    added += 1
                out.write(text)
            base = set(have)
            print(f"{url}: +{added} channels")
        except Exception as e:  # noqa: BLE001
            print(f"::warning::Skipped guide {url}: {e}")
    out.write("</tv>\n")
