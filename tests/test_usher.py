import sys
sys.path.insert(0, r'e:\projects\jlyrics')

from backend.lyrics.lrclib_provider import LRCLibProvider
from backend.lyrics.parser import parse_lrc

provider = LRCLibProvider()
lrc = provider.fetch(artist="USHER, Plies", title="Hey Daddy (Daddy's Home) (feat. Plies)")

if lrc:
    lines = parse_lrc(lrc)
    print(f"SUCCESS! Found {len(lines)} lines of lyrics for Usher!")
    print(f"First line: [{lines[0].timestamp_ms}ms] {lines[0].original_text}")
else:
    print("Failed to find lyrics.")
