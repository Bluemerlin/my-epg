#!/usr/bin/env python3
"""Merge iptv-org country playlists into one M3U with the guide URL in the header.

Usage: merge.py <guide_url> <output.m3u> <country>=<url> [<country>=<url> ...]
Group titles get the country label added in front, e.g. "UK | News".
A source labelled "-" (e.g. -=extras.m3u) is a local file kept as-is; list it first so its
names/groups win over duplicates from the country lists.
"""
import sys
import urllib.request
import re

guide_url, out_path, *sources = sys.argv[1:]

lines_out = [f'#EXTM3U url-tvg="{guide_url}" x-tvg-url="{guide_url}"']
seen = set()

for src in sources:
    label, url = src.split("=", 1)
    if url.startswith("http"):
        text = urllib.request.urlopen(url, timeout=60).read().decode("utf-8", "ignore")
    else:
        text = open(url, encoding="utf-8").read()
    block = []
    for line in text.splitlines():
        line = line.rstrip("\r")
        if not line or line.startswith("#EXTM3U"):
            continue
        if line.startswith("#EXTINF"):
            block = []
            if label == "-":
                pass  # local extras: keep their own group titles
            elif 'group-title="' in line:
                line = re.sub(r'group-title="([^"]*)"',
                              lambda m: f'group-title="{label} | {m.group(1) or "Other"}"', line)
            else:
                line = line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{label} | Other"', 1)
            block.append(line)
        elif line.startswith("#"):
            block.append(line)
        else:
            if block and line not in seen:
                seen.add(line)
                lines_out.extend(block + [line])
            block = []

with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines_out) + "\n")

print(f"{len(seen)} channels written to {out_path}")
