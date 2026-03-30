# YouTube Playlist Tracker

A desktop app for planning YouTube playlist watching time.

Instead of manually adding up video lengths, this app lets you paste a playlist link and quickly answer two common questions:

- If I want to watch for a specific amount of time, where should I stop?
- How long is this playlist, or a selected range of it?

The app is built with Python and Flet and is intended to be used through the Windows release download.

## Download

The normal way to use this project is through the `.exe` on the repo's Releases page.

- Download the latest `YouTube Playlist Tracker.exe` from Releases.
- Run it on Windows.
- No Python setup is required for normal use.

## Features

- `Watch Duration` mode: enter a playlist link, starting video, starting timestamp, and target watch time to find exactly where to stop.
- `Playlist Length` mode: calculate the total length of the whole playlist or a selected video range.
- Saved playlists: store playlist names and links for quick reuse.
- Bookmark support: save your current video and timestamp for a playlist.
- Auto-fill bookmarks: optionally load the saved bookmark into the starting video and timestamp fields.
- Default watch time: save a default watch duration for each playlist.
- Watch time by day: optionally save different default watch times for different days of the week.
- Copyable results: copy the calculated result text directly from the app.
- Playback speed estimates: see playlist length at `1.25x`, `1.5x`, `1.75x`, and `2.0x`.

## How It Works

### Watch Duration

Use this mode when you know how long you want to watch.

The app calculates:

- the playlist title
- where you are starting from
- how much time will actually be watched
- which video and timestamp you should stop at

### Playlist Length

Use this mode when you want the total length of a playlist or a selected section of it.

The app calculates:

- playlist title
- selected video count
- average video length
- total watch time
- equivalent watch times at faster playback speeds

## Saved Playlists

Saved playlists are meant to make repeat use easier.

You can:

- add playlists with a custom name
- edit or delete saved playlists
- reorder playlists in the saved list
- save a current video and timestamp bookmark
- choose whether that bookmark should auto-fill the starting position
- save a default watch duration for every day or by weekday

## Notes

- An internet connection is required when reading playlist information from YouTube.
- The app expects a valid YouTube playlist link containing a playlist ID.
- Unavailable or unreadable videos are handled and reported where relevant.
- Private, restricted, or otherwise inaccessible playlists may not work correctly.

## Source Code

The source code is included in this repository for reference and development, but regular users should use the packaged Windows release from the Releases page.
