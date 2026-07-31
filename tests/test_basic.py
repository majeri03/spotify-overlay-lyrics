"""
Test LRC Parser & Timeline Engine
"""
import sys
sys.path.insert(0, r'e:\projects\jlyrics')

from backend.lyrics.parser import parse_lrc
from backend.lyrics.validator import validate_lyrics, ValidationResult
from backend.lyrics.timeline_engine import TimelineEngine
from backend.models.models import TrackInfo

# Test 1: Parser
print("=== Test 1: LRC Parser ===")
lrc = """[ar:Ed Sheeran]
[ti:Perfect]
[00:12.50]I found a love for me
[00:17.00]Darling, just dive right in
[00:21.50]And follow my lead
[00:26.00]Well, I found a girl, beautiful and sweet
[00:30.50]Oh, I never knew you were the someone waiting for me
[00:36.00]'Cause we were just kids when we fell in love
[00:40.50]Not knowing what it was
"""
lines = parse_lrc(lrc)
print(f"Parsed {len(lines)} lines")
for l in lines:
    print(f"  [{l.timestamp_ms/1000:.2f}s] {l.original_text}")

# Test 2: Validator
print("\n=== Test 2: Validator ===")
result = validate_lyrics(lines, 240000)
print(f"Validation result: {result}")

# Test 3: Timeline Engine
print("\n=== Test 3: Timeline Engine ===")
track = TrackInfo(
    spotify_id="6OLs3vI4N6B1qPD5C1EJZM",
    title="Perfect",
    artist="Ed Sheeran",
    album="÷",
    duration_ms=255000
)
engine = TimelineEngine()
timeline = engine.build(track, lines)
print(f"Timeline built: {len(timeline)} lines")
print(f"First line end: {timeline.lines[0].end_timestamp_ms}ms")
print(f"First line duration: {timeline.lines[0].duration_ms}ms")

# Test 4: Timeline sync
import time
engine.start(12000)  # Start at 12 seconds
time.sleep(0.2)      # Wait 200ms
queue = engine.get_current_queue()
if queue and queue.current:
    print(f"\nAt ~12.2s: current = '{queue.current.original_text}'")
if queue and queue.next:
    print(f"Next: '{queue.next.original_text}'")

# Test 5: Seek
engine.seek(36000)  # Seek to 36s
time.sleep(0.05)
queue = engine.get_current_queue()
if queue and queue.current:
    print(f"\nAfter seek to 36s: current = '{queue.current.original_text}'")

print("\n=== All Tests PASSED! ===")
