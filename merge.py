#!/usr/bin/env python3
"""Merge the playlists listed in sources.txt into one M3U.

Usage: merge.py <guide_url> <sources.txt> <output.m3u> <extra_guides.txt>

- Each source line is Label=URL (or Label=local/file.m3u).
- Groups get the label in front ("UK | News"); label "-" keeps the source's own groups.
- Duplicate streams are dropped; earlier sources win.
- Any guide a source advertises in its header (url-tvg / x-tvg-url) is written to
  extra_guides.txt so the guide step can merge it into ours.
- A source that fails to load is skipped with a warning rather than breaking the build.
"""
import re
import sys
import urllib.request

guide_url, sources_path, out_path, guides_path = sys.argv[1:5]


def load(url):
    if url.startswith(("http://", "https://")):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")
    with open(url, encoding="utf-8") as f:
        return f.read()


sources = []
for raw in open(sources_path, encoding="utf-8"):
    raw = raw.strip()
    if raw and not raw.startswith("#") and "=" in raw:
        label, url = raw.split("=", 1)
        sources.append((label.strip(), url.strip()))

out = [f'#EXTM3U url-tvg="{guide_url}" x-tvg-url="{guide_url}"']
seen, extra_guides = set(), []

for label, url in sources:
    try:
        text = load(url)
    except Exception as e:  # noqa: BLE001
        print(f"::warning::Skipped {label} ({url}): {e}")
        continue

    before = len(seen)
    block = []
    for line in text.splitlines():
        line = line.rstrip("\r")
        if not line:
            continue
        if line.startswith("#EXTM3U"):
            for g in re.findall(r'(?:url-tvg|x-tvg-url)="([^"]+)"', line):
                for u in g.split(","):
                    u = u.strip()
                    if u and u not in extra_guides and u != guide_url:
                        extra_guides.append(u)
            continue
        if line.startswith("#EXTINF"):
            block = []
            if label != "-":
                if 'group-title="' in line:
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
                out.extend(block + [line])
            block = []
    print(f"{label}: {len(seen) - before} channels")

with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
with open(guides_path, "w", encoding="utf-8") as f:
    f.write("\n".join(extra_guides) + ("\n" if extra_guides else ""))

print(f"{len(seen)} channels written to {out_path}; {len(extra_guides)} extra guide(s) found")
