from __future__ import annotations

import asyncio

import flet as ft

from components import themed_tooltip
from constants import constants
from services import (
    PlaylistLengthResult,
    PlaylistServiceError,
    ValidationError,
    format_clock,
    format_speed_label,
)


class ResultHandlingMixin:
    def copy_result_text(self, mode: str):
        result_text = (
            self.watch_result_text if mode == "watch" else self.length_result_text
        )
        if not result_text:
            self.show_message("Nothing to copy yet.", error=True)
            return
        self.page.set_clipboard(result_text)
        self._activate_copy_feedback(mode)
        self.show_message("Result copied.")

    def _copy_button_for_mode(self, mode: str) -> ft.Container:
        return (
            self.watch_result_copy_button
            if mode == "watch"
            else self.length_result_copy_button
        )

    def _activate_copy_feedback(self, mode: str):
        button = self._copy_button_for_mode(mode)
        icon = button.content
        if not isinstance(icon, ft.Icon):
            return
        token = self.copy_feedback_tokens.get(mode, 0) + 1
        self.copy_feedback_tokens[mode] = token
        icon.name = ft.Icons.CHECK_ROUNDED
        icon.color = constants.colors.text
        button.bgcolor = constants.colors.accent_soft
        button.tooltip = themed_tooltip(constants, "Copied")
        if button.page is not None:
            button.update()
        if hasattr(self.page, "run_task"):
            self.page.run_task(self._reset_copy_feedback, mode, token)

    async def _reset_copy_feedback(self, mode: str, token: int):
        await asyncio.sleep(0.9)
        if self.copy_feedback_tokens.get(mode, 0) != token:
            return
        button = self._copy_button_for_mode(mode)
        icon = button.content
        if not isinstance(icon, ft.Icon):
            return
        icon.name = ft.Icons.CONTENT_COPY_ROUNDED
        icon.color = constants.colors.text_muted
        button.bgcolor = constants.colors.surface
        button.tooltip = themed_tooltip(constants, "Copy result")
        if button.page is not None:
            button.update()

    def reset_watch_start(self, _event=None):
        self.watch_start_video_field.reset()
        self.watch_timestamp.reset()
        self._set_inline_message(self.watch_start_message, None)
        self.page.update()

    def reset_watch_duration(self, _event=None):
        self.watch_duration.reset()
        self.page.update()

    def reset_length_range(self, _event=None):
        self.length_start_video_field.reset()
        self.length_end_video_field.reset()
        self.page.update()

    def handle_watch_duration(self, _event=None):
        self._set_inline_message(self.watch_link_message, None)
        self._set_inline_message(self.watch_start_message, None)

        try:
            playlist_url = self._resolve_playlist_url("watch")
        except ValidationError as exc:
            self._set_inline_message(self.watch_link_message, str(exc))
            self.page.update()
            return

        watch_seconds = self.watch_duration.total_seconds()
        if watch_seconds <= 0:
            self.show_message("Time to watch must be greater than 0.", error=True)
            return

        start_video = self.watch_start_video_field.int_value(default=1)
        start_timestamp = self.watch_timestamp.total_seconds()

        result = None
        self._set_busy(self.watch_calculate_button, True)
        try:
            result = self.playlist_service.calculate_watch_duration(
                playlist_url,
                start_video_position=start_video,
                start_timestamp_seconds=start_timestamp,
                requested_watch_seconds=watch_seconds,
            )
        except ValidationError as exc:
            message = str(exc)
            lowered = message.casefold()
            if "starting video" in lowered or "timestamp" in lowered:
                self._set_inline_message(self.watch_start_message, message)
            else:
                self.show_message(message, error=True)
        except PlaylistServiceError as exc:
            self._set_inline_message(self.watch_link_message, str(exc))
        finally:
            self._set_busy(self.watch_calculate_button, False)

        if result is not None:
            self.render_watch_result(result)

    def render_watch_result(self, result):
        copy_groups = [
            [f"Playlist:  {result.playlist_title}"],
            [
                f"Watch From:  {result.start_video_position} - {format_clock(result.start_timestamp_seconds)}",
                f"Watch Time:  {self._format_result_duration(result.actual_watch_seconds)}",
            ],
            [
                f"Watch Until:  {result.end_video_position} - {format_clock(result.end_timestamp_seconds)}"
            ],
        ]
        groups = [
            [
                self._result_line("Playlist:  ", result.playlist_title),
            ],
            [
                self._result_line(
                    "Watch From:  ",
                    f"{result.start_video_position} - {format_clock(result.start_timestamp_seconds)}",
                    monospace_value=True,
                ),
                self._result_line(
                    "Watch Time:  ",
                    self._format_result_duration(result.actual_watch_seconds),
                    monospace_value=True,
                ),
            ],
            [
                self._result_line(
                    "Watch Until:  ",
                    f"{result.end_video_position} - {format_clock(result.end_timestamp_seconds)}",
                    monospace_value=True,
                )
            ],
        ]

        notes: list[str] = []
        if result.remaining_in_end_video_seconds:
            notes.append(
                f"Remaining in that video:  {self._format_result_duration(result.remaining_in_end_video_seconds)}"
            )
        if result.note:
            notes.append(result.note)

        self.watch_result_text = self._compose_result_copy_text(copy_groups, notes)
        self.watch_result_copy_button.disabled = False
        self.watch_result_content.controls = [
            self._result_body(
                self._build_result_groups(groups, notes, group_gap=16, line_gap=8)
            )
        ]
        self.page.update()

    def handle_playlist_length(self, _event=None):
        self._set_inline_message(self.length_link_message, None)

        try:
            playlist_url = self._resolve_playlist_url("length")
        except ValidationError as exc:
            self._set_inline_message(self.length_link_message, str(exc))
            self.page.update()
            return

        start_value = self.length_start_video_field.value.strip()
        end_value = self.length_end_video_field.value.strip()
        start_video = int(start_value) if start_value else None
        end_video = int(end_value) if end_value else None

        result = None
        self._set_busy(self.length_calculate_button, True)
        try:
            result = self.playlist_service.calculate_playlist_length(
                playlist_url,
                start_video_position=start_video,
                end_video_position=end_video,
            )
        except ValidationError as exc:
            self.show_message(str(exc), error=True)
        except PlaylistServiceError as exc:
            self._set_inline_message(self.length_link_message, str(exc))
        finally:
            self._set_busy(self.length_calculate_button, False)

        if result is not None:
            self.render_playlist_length_result(result)

    def render_playlist_length_result(self, result: PlaylistLengthResult):
        copy_groups = [
            [
                f"Playlist:  {result.playlist_title}",
                f"Video Count:  {result.selected_video_count}",
                f"Average Video Length:  {self._format_result_duration(result.average_length_seconds)}",
            ],
            [
                f"Total Length:  {self._format_result_duration(result.total_length_seconds)}",
                *[
                    f"At {format_speed_label(float(speed))}:  {self._format_result_duration(result.playback_lengths[float(speed)])}"
                    for speed in constants.playback_speeds
                ],
            ],
        ]
        groups = [
            [
                self._result_line("Playlist:  ", result.playlist_title),
                self._result_line(
                    "Video Count:  ",
                    str(result.selected_video_count),
                    monospace_value=True,
                ),
                self._result_line(
                    "Average Video Length:  ",
                    self._format_result_duration(result.average_length_seconds),
                    monospace_value=True,
                ),
            ],
            [
                self._result_line(
                    "Total Length:  ",
                    self._format_result_duration(result.total_length_seconds),
                    monospace_value=True,
                ),
                *[
                    self._result_line(
                        f"At {format_speed_label(float(speed))}:  ",
                        self._format_result_duration(result.playback_lengths[float(speed)]),
                        monospace_value=True,
                    )
                    for speed in constants.playback_speeds
                ],
            ],
        ]

        notes: list[str] = []
        if not (
            result.start_video_position == 1
            and result.end_video_position == result.playlist_video_count
        ):
            notes.append(
                f"Selected range:  {result.start_video_position} to {result.end_video_position}"
            )
        if result.note:
            notes.append(result.note)

        self.length_result_text = self._compose_result_copy_text(copy_groups, notes)
        self.length_result_copy_button.disabled = False
        self.length_result_content.controls = [
            self._result_body(
                self._build_result_groups(groups, notes, group_gap=18, line_gap=10)
            )
        ]
        self.page.update()

    def _set_busy(self, button: ft.ElevatedButton, busy: bool):
        button.disabled = busy
        button.text = "Calculating..." if busy else "Calculate"
        self.page.update()

    def show_message(self, message: str, *, error: bool = False):
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=constants.colors.text),
            bgcolor=constants.colors.danger if error else constants.colors.accent_dark,
            behavior=ft.SnackBarBehavior.FLOATING,
        )
        self.page.snack_bar.open = True
        self.page.update()
