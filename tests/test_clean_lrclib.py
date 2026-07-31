import requests
import re

def clean_title(t):
    t = re.sub(r'[\(\[\{].*?(feat|ft|with|remastered).*?[\)\]\}]', '', t, flags=re.IGNORECASE)
    return t.strip()

def clean_artist(a):
    a = re.split(r'[,&]|\bfeat\b|\bft\b', a, flags=re.IGNORECASE)[0]
    return a.strip()

artist = "USHER, Plies"
title = "Hey Daddy (Daddy's Home) (feat. Plies)"

c_art = clean_artist(artist)
c_ti = clean_title(title)

print("Original:", artist, "-", title)
print("Cleaned: ", c_art, "-", c_ti)

url = f"https://lrclib.net/api/search?q={c_art} {c_ti}"
r = requests.get(url).json()
print(f"\nSearch found {len(r)} results:")
for item in r[:3]:
    print("  -", item.get("artistName"), "-", item.get("trackName"), "| Synced:", bool(item.get("syncedLyrics")))
