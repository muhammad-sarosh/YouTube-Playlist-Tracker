from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from yt_dlp import YoutubeDL


PLAYLIST_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
WEEKDAY_KEYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


class ValidationError(ValueError):
    pass


class PlaylistServiceError(RuntimeError):
    pass


@dataclass(slots=True)
class SavedPlaylist:
    id: str
    name: str
    url: str
    created_at: str
    default_watch_seconds: int | None = None
    default_watch_by_day: dict[str, int | None] | None = None
    completed_for_date: str | None = None
    bookmark_video_position: int | None = None
    bookmark_timestamp_seconds: int | None = None
    autofill_bookmark: bool = False


@dataclass(slots=True)
class PlaylistVideo:
    position: int
    title: str
    url: str | None
    duration_seconds: int
    available: bool


@dataclass(slots=True)
class PlaylistMetadata:
    title: str
    canonical_url: str
    videos: list[PlaylistVideo]

    @property
    def total_entries(self) -> int:
        return len(self.videos)

    @property
    def available_videos(self) -> list[PlaylistVideo]:
        return [video for video in self.videos if video.available]

    @property
    def available_count(self) -> int:
        return len(self.available_videos)

    @property
    def unavailable_count(self) -> int:
        return self.total_entries - self.available_count

    def video_at_position(self, position: int) -> PlaylistVideo | None:
        for video in self.videos:
            if video.position == position:
                return video
        return None


@dataclass(slots=True)
class WatchDurationResult:
    playlist_title: str
    playlist_video_count: int
    available_video_count: int
    unavailable_video_count: int
    requested_watch_seconds: int
    actual_watch_seconds: int
    start_video_position: int
    start_timestamp_seconds: int
    end_video_position: int
    end_timestamp_seconds: int
    end_video_title: str
    remaining_in_end_video_seconds: int
    note: str | None = None


@dataclass(slots=True)
class PlaylistLengthResult:
    playlist_title: str
    playlist_video_count: int
    available_video_count: int
    unavailable_video_count: int
    start_video_position: int
    end_video_position: int
    selected_video_count: int
    selected_missing_count: int
    total_length_seconds: int
    average_length_seconds: int
    playback_lengths: dict[float, int]
    note: str | None = None


def normalize_playlist_url(url: str) -> str:
    candidate = (url or "").strip()
    if not candidate:
        raise ValidationError("Enter a playlist link.")

    parsed = urlparse(candidate)
    if not parsed.scheme:
        parsed = urlparse(f"https://{candidate}")

    host = (parsed.netloc or "").lower()
    query = parse_qs(parsed.query)
    playlist_ids = query.get("list", [])
    playlist_id = playlist_ids[0].strip() if playlist_ids else ""

    if host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
        if playlist_id and PLAYLIST_ID_RE.fullmatch(playlist_id):
            return f"https://www.youtube.com/playlist?list={playlist_id}"
    if host in {"youtu.be", "www.youtu.be"} and playlist_id and PLAYLIST_ID_RE.fullmatch(playlist_id):
        return f"https://www.youtube.com/playlist?list={playlist_id}"

    raise ValidationError(
        "Enter a valid YouTube playlist link. The link must include a list ID."
    )


def format_clock(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def format_duration(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return ", ".join(parts)


def format_speed_label(speed: float) -> str:
    if speed.is_integer():
        return f"{speed:.1f}x"
    return f"{speed:.2f}".rstrip("0").rstrip(".") + "x"


def shorten_text(value: str, limit: int = 42) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "..."


class SavedPlaylistsStore:
    def __init__(self, data_dir: Path, legacy_paths: list[Path] | None = None):
        self.file_path = data_dir / "playlists.json"
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.legacy_paths = legacy_paths or []

    def load(self) -> list[SavedPlaylist]:
        raw = self._read_json(self.file_path)
        if raw is None:
            for legacy_path in self.legacy_paths:
                raw = self._read_json(legacy_path)
                if raw is not None:
                    break
        return self._deserialize(raw)

    def save(self, playlists: list[SavedPlaylist]):
        payload = [asdict(playlist) for playlist in playlists]
        self.file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _read_json(self, path: Path) -> object | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _deserialize(self, data: object | None) -> list[SavedPlaylist]:
        if data is None:
            return []

        playlists: list[SavedPlaylist] = []
        timestamp = datetime.now(timezone.utc).isoformat()

        def _optional_int(value):
            if value in (None, ""):
                return None
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        if isinstance(data, dict):
            for name, url in data.items():
                if isinstance(name, str) and isinstance(url, str):
                    playlists.append(
                        SavedPlaylist(
                            id=uuid4().hex,
                            name=name.strip(),
                            url=url.strip(),
                            created_at=timestamp,
                            default_watch_seconds=None,
                            default_watch_by_day=None,
                            completed_for_date=None,
                            bookmark_video_position=None,
                            bookmark_timestamp_seconds=None,
                            autofill_bookmark=False,
                        )
                    )
            return playlists

        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "")).strip()
                url = str(item.get("url", "")).strip()
                if not name or not url:
                    continue
                default_watch_by_day = None
                raw_default_watch_by_day = item.get("default_watch_by_day")
                if isinstance(raw_default_watch_by_day, dict):
                    parsed_default_watch_by_day = {}
                    for day in WEEKDAY_KEYS:
                        if day in raw_default_watch_by_day:
                            parsed_default_watch_by_day[day] = _optional_int(
                                raw_default_watch_by_day.get(day)
                            )
                    if parsed_default_watch_by_day:
                        default_watch_by_day = parsed_default_watch_by_day
                playlists.append(
                    SavedPlaylist(
                        id=str(item.get("id") or uuid4().hex),
                        name=name,
                        url=url,
                        created_at=str(item.get("created_at") or timestamp),
                        default_watch_seconds=_optional_int(
                            item.get("default_watch_seconds")
                        ),
                        default_watch_by_day=default_watch_by_day,
                        completed_for_date=(
                            str(item.get("completed_for_date")).strip() or None
                            if item.get("completed_for_date") is not None
                            else None
                        ),
                        bookmark_video_position=_optional_int(
                            item.get("bookmark_video_position")
                        ),
                        bookmark_timestamp_seconds=_optional_int(
                            item.get("bookmark_timestamp_seconds")
                        ),
                        autofill_bookmark=bool(item.get("autofill_bookmark", False)),
                    )
                )
        return playlists


class PlaylistService:
    def __init__(self):
        self._cache: dict[str, PlaylistMetadata] = {}

    def clear_cache(self):
        self._cache.clear()

    def get_playlist(self, url: str, *, refresh: bool = False) -> PlaylistMetadata:
        canonical_url = normalize_playlist_url(url)
        if not refresh and canonical_url in self._cache:
            return self._cache[canonical_url]

        metadata = self._fetch_playlist(canonical_url)
        self._cache[canonical_url] = metadata
        return metadata

    def calculate_watch_duration(
        self,
        url: str,
        *,
        start_video_position: int,
        start_timestamp_seconds: int,
        requested_watch_seconds: int,
    ) -> WatchDurationResult:
        if start_video_position < 1:
            raise ValidationError("Starting video must be 1 or higher.")
        if requested_watch_seconds <= 0:
            raise ValidationError("Time to watch must be greater than 0.")

        metadata = self.get_playlist(url)
        if metadata.total_entries == 0:
            raise PlaylistServiceError("No videos were found in that playlist.")

        if start_video_position > metadata.total_entries:
            raise ValidationError(
                f"Starting video must be between 1 and {metadata.total_entries}."
            )

        target_video = metadata.video_at_position(start_video_position)
        if target_video is None or not target_video.available:
            raise PlaylistServiceError(
                "The selected starting video is unavailable or its duration could not be read."
            )

        if start_timestamp_seconds >= target_video.duration_seconds:
            raise ValidationError(
                "The starting timestamp is longer than the selected video's duration."
            )

        available_videos = metadata.available_videos
        start_index = next(
            index
            for index, video in enumerate(available_videos)
            if video.position == start_video_position
        )

        watched_seconds = 0
        end_video = target_video
        end_timestamp = target_video.duration_seconds
        truncated = False

        for index in range(start_index, len(available_videos)):
            video = available_videos[index]
            offset = start_timestamp_seconds if index == start_index else 0
            usable_seconds = video.duration_seconds - offset

            if watched_seconds + usable_seconds >= requested_watch_seconds:
                need = requested_watch_seconds - watched_seconds
                end_video = video
                end_timestamp = offset + need
                watched_seconds = requested_watch_seconds
                break

            watched_seconds += usable_seconds
            end_video = video
            end_timestamp = video.duration_seconds
        else:
            truncated = True

        note = None
        if metadata.unavailable_count:
            note = (
                f"{metadata.unavailable_count} playlist video(s) were skipped because "
                "their duration could not be read."
            )
        if truncated:
            remaining = requested_watch_seconds - watched_seconds
            extra_note = (
                "The playlist ends before the requested watch time is reached"
                f" ({format_duration(remaining)} short)."
            )
            note = f"{note} {extra_note}".strip() if note else extra_note

        return WatchDurationResult(
            playlist_title=metadata.title,
            playlist_video_count=metadata.total_entries,
            available_video_count=metadata.available_count,
            unavailable_video_count=metadata.unavailable_count,
            requested_watch_seconds=requested_watch_seconds,
            actual_watch_seconds=watched_seconds,
            start_video_position=start_video_position,
            start_timestamp_seconds=start_timestamp_seconds,
            end_video_position=end_video.position,
            end_timestamp_seconds=end_timestamp,
            end_video_title=end_video.title,
            remaining_in_end_video_seconds=max(
                0, end_video.duration_seconds - end_timestamp
            ),
            note=note,
        )

    def calculate_playlist_length(
        self,
        url: str,
        *,
        start_video_position: int | None = None,
        end_video_position: int | None = None,
    ) -> PlaylistLengthResult:
        metadata = self.get_playlist(url)
        if metadata.total_entries == 0:
            raise PlaylistServiceError("No videos were found in that playlist.")

        start = start_video_position or 1
        end = end_video_position or metadata.total_entries

        if start < 1:
            raise ValidationError("Starting video must be 1 or higher.")
        if end < 1:
            raise ValidationError("Ending video must be 1 or higher.")
        if start > metadata.total_entries or end > metadata.total_entries:
            raise ValidationError(
                f"Video range must stay between 1 and {metadata.total_entries}."
            )
        if end < start:
            raise ValidationError("Ending video must be greater than or equal to starting video.")

        selected_videos = [
            video
            for video in metadata.available_videos
            if start <= video.position <= end
        ]
        selected_missing_count = sum(
            1
            for video in metadata.videos
            if start <= video.position <= end and not video.available
        )

        if not selected_videos:
            raise PlaylistServiceError(
                "No playable videos were found in the selected range."
            )

        total_length_seconds = sum(video.duration_seconds for video in selected_videos)
        average_length_seconds = round(total_length_seconds / len(selected_videos))
        playback_lengths = {
            speed: math.ceil(total_length_seconds / speed)
            for speed in (1.25, 1.5, 1.75, 2.0)
        }

        note = None
        if selected_missing_count:
            note = (
                f"{selected_missing_count} selected video(s) were excluded because "
                "their duration could not be read."
            )

        return PlaylistLengthResult(
            playlist_title=metadata.title,
            playlist_video_count=metadata.total_entries,
            available_video_count=metadata.available_count,
            unavailable_video_count=metadata.unavailable_count,
            start_video_position=start,
            end_video_position=end,
            selected_video_count=len(selected_videos),
            selected_missing_count=selected_missing_count,
            total_length_seconds=total_length_seconds,
            average_length_seconds=average_length_seconds,
            playback_lengths=playback_lengths,
            note=note,
        )

    def _fetch_playlist(self, canonical_url: str) -> PlaylistMetadata:
        try:
            with YoutubeDL(
                {
                    "quiet": True,
                    "no_warnings": True,
                    "skip_download": True,
                    "extract_flat": True,
                    "ignoreerrors": True,
                }
            ) as ydl:
                info = ydl.extract_info(canonical_url, download=False)
        except Exception as exc:
            raise PlaylistServiceError(
                "Couldn't fetch the playlist. Check the link and your internet connection."
            ) from exc

        entries = info.get("entries") if isinstance(info, dict) else None
        if not entries:
            raise PlaylistServiceError("No videos were found in that playlist.")

        title = str(info.get("title") or "Unknown Playlist")
        videos: list[PlaylistVideo] = []

        for position, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                videos.append(
                    PlaylistVideo(
                        position=position,
                        title=f"Video {position}",
                        url=None,
                        duration_seconds=0,
                        available=False,
                    )
                )
                continue

            url = self._build_video_url(entry)
            title_text = str(entry.get("title") or f"Video {position}")
            duration = entry.get("duration")

            if (duration is None or int(duration) <= 0) and url:
                duration, fallback_title = self._fetch_video_duration_and_title(url)
                if fallback_title and title_text.startswith("Video "):
                    title_text = fallback_title

            duration_seconds = int(duration or 0)
            videos.append(
                PlaylistVideo(
                    position=position,
                    title=title_text,
                    url=url,
                    duration_seconds=duration_seconds,
                    available=duration_seconds > 0,
                )
            )

        return PlaylistMetadata(title=title, canonical_url=canonical_url, videos=videos)

    def _fetch_video_duration_and_title(self, video_url: str) -> tuple[int, str | None]:
        try:
            with YoutubeDL(
                {"quiet": True, "no_warnings": True, "skip_download": True}
            ) as ydl:
                info = ydl.extract_info(video_url, download=False)
        except Exception:
            return 0, None

        if not isinstance(info, dict):
            return 0, None
        return int(info.get("duration") or 0), info.get("title")

    def _build_video_url(self, entry: dict) -> str | None:
        raw = entry.get("webpage_url") or entry.get("url") or entry.get("id")
        if not raw:
            return None
        raw = str(raw)
        if raw.startswith("http://") or raw.startswith("https://"):
            return raw
        if VIDEO_ID_RE.fullmatch(raw):
            return f"https://www.youtube.com/watch?v={raw}"
        return f"https://www.youtube.com/watch?v={raw}"
