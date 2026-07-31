"""
Test LRCLIB Provider (butuh internet)
"""
import sys
sys.path.insert(0, r'e:\projects\jlyrics')

from backend.logger.app_logger import setup_logger
setup_logger(debug=False)

from backend.lyrics.lrclib_provider import LRCLibProvider
from backend.lyrics.parser import parse_lrc
from backend.lyrics.validator import validate_lyrics

print("=== Test LRCLIB Provider ===\n")

provider = LRCLibProvider()

# Test dengan lagu populer
test_songs = [
    ("Ed Sheeran", "Perfect", 255000),
    ("Taylor Swift", "Blank Space", 231826),
    ("Coldplay", "Yellow", 269000),
]

for artist, title, duration in test_songs:
    print(f"Testing: {artist} - {title}")
    lrc = provider.fetch(artist=artist, title=title, duration_ms=duration)
    if lrc:
        lines = parse_lrc(lrc)
        result = validate_lyrics(lines, duration)
        print(f"  [OK] Found {len(lines)} lines | Validation: {result.value}")
        if lines:
            print(f"  First: [{lines[0].timestamp_ms/1000:.1f}s] {lines[0].original_text[:50]}")
    else:
        print(f"  [NOT FOUND]")
    print()

print("=== LRCLIB Test Complete ===")
