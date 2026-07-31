import sys
sys.path.insert(0, r'e:\projects\jlyrics')

from backend.spotify.windows_media_provider import WindowsMediaProvider

win = WindowsMediaProvider()
playback = win.fetch_playback()

if playback and playback.track:
    print(f"SUCCESS! Track: {playback.track.artist} - {playback.track.title}")
    print(f"Status: {playback.state.value} | Position: {playback.progress_ms}ms")
else:
    print("No media playing")
