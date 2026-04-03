from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import flet as ft

from components import (
    PrimaryButton,
    ReservedMessage,
    SecondaryButton,
    SectionLabel,
    StyledTextField,
    SurfaceCard,
    build_screen_card,
    themed_tooltip,
    toolbar_button,
)
from constants import constants
from services import SavedPlaylist, ValidationError, WEEKDAY_KEYS, normalize_playlist_url

WEEKDAY_LABELS = {day: day.title() for day in WEEKDAY_KEYS}


class PlaylistManagementMixin:
    def increment_playlist_bookmark_video(self, _event=None):
        self.playlist_bookmark_video_field.increment()

    def decrement_playlist_bookmark_video(self, _event=None):
        self.playlist_bookmark_video_field.decrement()

    def reset_playlist_bookmark_timestamp(self, _event=None):
        self.playlist_bookmark_timestamp.reset()
        self._set_inline_message(self.playlist_bookmark_message, None)
        self.page.update()

    def _effective_watch_default_for_today(
        self, playlist: SavedPlaylist
    ) -> int | None:
        weekday_key = WEEKDAY_KEYS[datetime.now().weekday()]
        day_defaults = playlist.default_watch_by_day or {}

        if weekday_key in day_defaults:
            value = day_defaults.get(weekday_key)
            return value if value and value > 0 else None

        value = playlist.default_watch_seconds
        return value if value and value > 0 else None

    def _link_field_for_mode(self, mode: str) -> StyledTextField:
        if mode == "watch":
            return self.watch_link_field
        return self.length_link_field

    def _link_message_for_mode(self, mode: str) -> ReservedMessage:
        if mode == "watch":
            return self.watch_link_message
        return self.length_link_message

    def _selected_playlist_id_for_mode(self, mode: str) -> str | None:
        if mode == "watch":
            return self.selected_watch_playlist_id
        return self.selected_length_playlist_id

    def _set_selected_playlist_id(self, mode: str, playlist_id: str | None):
        if mode == "watch":
            self.selected_watch_playlist_id = playlist_id
        else:
            self.selected_length_playlist_id = playlist_id

    def _selected_playlist(self, mode: str) -> SavedPlaylist | None:
        playlist_id = self._selected_playlist_id_for_mode(mode)
        if not playlist_id:
            return None
        return self.find_playlist(playlist_id)

    def close_pickers(self, _event=None):
        self.open_picker_mode = None
        self._refresh_picker_overlay()
        if self.page is not None:
            self.page.update()

    def toggle_picker(self, mode: str):
        if not self.saved_playlists or self.current_screen != "main":
            return
        self.open_picker_mode = None if self.open_picker_mode == mode else mode
        self._refresh_picker_overlay()
        self.page.update()

    def _active_link_field(self) -> StyledTextField:
        if self.active_mode == "watch":
            return self.watch_link_field
        return self.length_link_field

    def _active_playlist_url(self) -> str:
        selected = self._selected_playlist(self.active_mode)
        if selected is not None:
            return selected.url
        return self._active_link_field().value.strip()

    def _handle_watch_link_change(self, _event=None):
        if self.open_picker_mode is not None:
            self.close_pickers()
        self._clear_selection_if_edited("watch")

    def _handle_length_link_change(self, _event=None):
        if self.open_picker_mode is not None:
            self.close_pickers()
        self._clear_selection_if_edited("length")

    def _clear_selection_if_edited(self, mode: str):
        selected = self._selected_playlist(mode)
        if selected is None:
            return
        field = self._link_field_for_mode(mode)
        if field.value.strip() != selected.name:
            self._set_selected_playlist_id(mode, None)

    def _resolve_playlist_url(self, mode: str) -> str:
        selected = self._selected_playlist(mode)
        raw_value = selected.url if selected is not None else self._link_field_for_mode(
            mode
        ).value.strip()
        return normalize_playlist_url(raw_value)

    def _sync_selected_playlist_fields(self):
        for mode in ("watch", "length"):
            field = self._link_field_for_mode(mode)
            playlist = self._selected_playlist(mode)
            if playlist is None:
                if self._selected_playlist_id_for_mode(mode) is not None:
                    self._set_selected_playlist_id(mode, None)
                    field.value = ""
                continue
            field.value = playlist.name

    def _apply_watch_playlist_defaults(self, playlist: SavedPlaylist):
        weekday_key = WEEKDAY_KEYS[datetime.now().weekday()]
        day_defaults = playlist.default_watch_by_day or {}
        if weekday_key in day_defaults:
            self.watch_duration.set_seconds(day_defaults[weekday_key] or 0)
        elif playlist.default_watch_seconds is not None:
            self.watch_duration.set_seconds(playlist.default_watch_seconds)
        if playlist.autofill_bookmark and playlist.bookmark_video_position is not None:
            self.watch_start_video_field.set_int_value(playlist.bookmark_video_position)
            self.watch_timestamp.set_seconds(playlist.bookmark_timestamp_seconds or 0)

    def _set_playlist_default_watch_by_day_fields(
        self,
        default_watch_seconds: int | None,
        default_watch_by_day: dict[str, int | None] | None = None,
    ):
        effective_default_seconds = default_watch_seconds or 0
        day_defaults = default_watch_by_day or {}
        for day, control in self.playlist_default_watch_by_day_fields.items():
            if day in day_defaults:
                control.set_seconds(day_defaults[day] or 0)
            else:
                control.set_seconds(effective_default_seconds)

    def _collect_playlist_default_watch_by_day_fields(self) -> dict[str, int | None]:
        return {
            day: (control.total_seconds() or None)
            for day, control in self.playlist_default_watch_by_day_fields.items()
        }

    def change_mode(self, mode: str):
        self.active_mode = mode
        if self.open_picker_mode is not None:
            self.close_pickers()
        self.mode_toggle.set_value(mode)
        self.watch_section.visible = mode == "watch"
        self.length_section.visible = mode == "length"
        self.page.update()

    def show_main_screen(self, _event=None):
        self.current_screen = "main"
        self.screen_host.content = self._build_shell(self.main_screen)
        self._refresh_picker_overlay()
        self.page.update()

    def show_saved_playlists_screen(self, _event=None):
        self.current_screen = "saved"
        self.close_pickers()

        if self.saved_playlists:
            list_control: ft.Control = ft.ReorderableListView(
                controls=[
                    self._saved_playlist_tile(index, playlist)
                    for index, playlist in enumerate(self.saved_playlists)
                ],
                expand=True,
                show_default_drag_handles=False,
                on_reorder=self.handle_playlist_reorder,
                build_controls_on_demand=False,
            )
        else:
            list_control = ft.Container(
                expand=True,
                alignment=ft.alignment.top_center,
                content=SurfaceCard(
                    constants,
                    ft.Text(
                        "No saved playlists yet. Add one to make the playlist picker useful.",
                        color=constants.colors.text_subtle,
                        size=constants.font_sizes.body,
                    ),
                ),
            )

        body = ft.Column(
            controls=[
                ft.Text(
                    "Drag playlists to move them up or down. This also changes their order in the playlist dropdown.",
                    color=constants.colors.text_subtle,
                    size=constants.font_sizes.small,
                ),
                self._gap(10),
                list_control,
            ],
            spacing=0,
            expand=True,
        )

        screen = build_screen_card(
            "Saved Playlists",
            body,
            constants,
            leading=toolbar_button(
                constants,
                tooltip="Back",
                icon=ft.Icons.ARROW_BACK_ROUNDED,
                on_click=self.show_main_screen,
            ),
            trailing=toolbar_button(
                constants,
                tooltip="Add playlist",
                icon=ft.Icons.ADD_ROUNDED,
                on_click=self.show_add_playlist_screen,
            ),
        )
        self.screen_host.content = self._build_shell(screen)
        self.page.update()

    def _saved_playlist_tile(self, index: int, playlist: SavedPlaylist) -> ft.Control:
        edit_button = self._playlist_icon_action(
            ft.Icons.EDIT_ROUNDED,
            "Edit playlist",
            lambda _event, playlist_id=playlist.id: self.show_edit_playlist_screen(
                playlist_id
            ),
        )
        delete_button = self._playlist_icon_action(
            ft.Icons.DELETE_OUTLINE_ROUNDED,
            "Delete playlist",
            lambda _event, playlist_id=playlist.id: self.open_delete_dialog(
                playlist_id
            ),
        )

        tile = SurfaceCard(
            constants,
            ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.DRAG_INDICATOR_ROUNDED,
                        color=constants.colors.text_subtle,
                        size=18,
                    ),
                    ft.Text(
                        playlist.name,
                        expand=True,
                        size=constants.font_sizes.body,
                        weight=ft.FontWeight.W_600,
                        color=constants.colors.text,
                    ),
                    edit_button,
                    delete_button,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        tile.padding = ft.Padding(10, 8, 8, 8)
        tile.margin = ft.margin.only(bottom=8)
        return ft.ReorderableDraggable(index=index, content=tile)

    def _playlist_icon_action(
        self, icon: ft.Icons | str, tooltip: str, on_click
    ) -> ft.Container:
        button = ft.Container(
            width=30,
            height=30,
            bgcolor=constants.colors.surface_muted,
            border_radius=10,
            alignment=ft.alignment.center,
            tooltip=themed_tooltip(constants, tooltip),
            content=ft.Icon(
                icon,
                size=16,
                color=constants.colors.text_muted,
            ),
        )

        def _handle_click(event, control=button):
            control.bgcolor = constants.colors.surface_muted
            if control.page is not None:
                control.update()
            on_click(event)
            control.bgcolor = constants.colors.surface_muted
            if control.page is not None:
                control.update()

        button.on_click = _handle_click

        def _handle_hover(event, control=button):
            control.bgcolor = (
                constants.colors.surface_hover
                if str(event.data).lower() == "true"
                else constants.colors.surface_muted
            )
            if control.page is not None:
                control.update()

        button.on_hover = _handle_hover
        return button

    def handle_playlist_reorder(self, event):
        old_index = event.old_index
        new_index = event.new_index
        if old_index is None or new_index is None:
            return
        if new_index > old_index:
            new_index -= 1
        moved = self.saved_playlists.pop(old_index)
        self.saved_playlists.insert(new_index, moved)
        self.saved_store.save(self.saved_playlists)
        self.refresh_saved_playlist_controls()
        self.show_saved_playlists_screen()

    def show_add_playlist_screen(self, _event=None):
        self.current_screen = "add"
        self.close_pickers()
        self.editing_playlist_id = None
        self.playlist_schedule_opened = False
        self.playlist_initial_default_watch_seconds = None
        self.playlist_initial_default_watch_by_day = None
        self._clear_form_messages()
        self.playlist_name_field.value = ""
        self.playlist_url_field.value = ""
        self.playlist_default_watch.set_seconds(0)
        self._set_playlist_default_watch_by_day_fields(None, None)
        self.playlist_bookmark_video_field.set_int_value(None)
        self.playlist_bookmark_timestamp.set_seconds(0)
        self.playlist_autofill_checkbox.value = True
        self._show_playlist_form_screen("Add Playlist", "Add")

    def show_edit_playlist_screen(self, playlist_id: str):
        playlist = self.find_playlist(playlist_id)
        if playlist is None:
            self.show_message("That saved playlist could not be found.", error=True)
            self.show_saved_playlists_screen()
            return

        self.current_screen = "edit"
        self.close_pickers()
        self.editing_playlist_id = playlist_id
        self.playlist_schedule_opened = False
        self.playlist_initial_default_watch_seconds = playlist.default_watch_seconds
        self.playlist_initial_default_watch_by_day = (
            dict(playlist.default_watch_by_day)
            if playlist.default_watch_by_day
            else None
        )
        self._clear_form_messages()
        self.playlist_name_field.value = playlist.name
        self.playlist_url_field.value = playlist.url
        self.playlist_default_watch.set_seconds(playlist.default_watch_seconds or 0)
        self._set_playlist_default_watch_by_day_fields(
            playlist.default_watch_seconds,
            self.playlist_initial_default_watch_by_day,
        )
        self.playlist_bookmark_video_field.set_int_value(
            playlist.bookmark_video_position
        )
        self.playlist_bookmark_timestamp.set_seconds(
            playlist.bookmark_timestamp_seconds or 0
        )
        self.playlist_autofill_checkbox.value = playlist.autofill_bookmark
        self._show_playlist_form_screen("Edit Playlist", "Save")

    def show_active_playlist_form_screen(self, _event=None):
        self.current_screen = "edit" if self.editing_playlist_id else "add"
        self._show_playlist_form_screen(
            "Edit Playlist" if self.editing_playlist_id else "Add Playlist",
            "Save" if self.editing_playlist_id else "Add",
        )

    def show_default_watch_schedule_screen(self, _event=None):
        if self.current_screen not in {"add", "edit", "schedule"}:
            return

        if not self.playlist_schedule_opened:
            self._set_playlist_default_watch_by_day_fields(
                self.playlist_default_watch.total_seconds() or None,
                self.playlist_initial_default_watch_by_day,
            )
            self.playlist_schedule_opened = True

        self.current_screen = "schedule"
        day_rows: list[ft.Control] = [
            ft.Text(
                "These values become the saved watch-time defaults for each day.",
                color=constants.colors.text_subtle,
                size=constants.font_sizes.small,
            ),
            self._gap(12),
        ]
        for day in WEEKDAY_KEYS:
            day_rows.extend(
                [
                    ft.Row(
                        controls=[
                            ft.Text(
                                WEEKDAY_LABELS[day],
                                expand=True,
                                size=constants.font_sizes.body,
                                color=constants.colors.text,
                                weight=ft.FontWeight.W_600,
                            ),
                            self.playlist_default_watch_by_day_fields[day],
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self._gap(10),
                ]
            )

        body = ft.Column(
            controls=[
                *day_rows,
                self._gap(18),
                ft.Container(expand=True),
                ft.Row(
                    controls=[
                        PrimaryButton(
                            "Done",
                            self.apply_default_watch_schedule,
                            constants,
                        )
                    ],
                    spacing=0,
                ),
            ],
            spacing=0,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        screen = build_screen_card(
            "Watch Time by Day",
            body,
            constants,
            leading=toolbar_button(
                constants,
                tooltip="Back",
                icon=ft.Icons.ARROW_BACK_ROUNDED,
                on_click=self.show_active_playlist_form_screen,
            ),
            trailing=self._toolbar_spacer(),
        )
        self.screen_host.content = self._build_shell(screen)
        self.page.update()

    def apply_default_watch_schedule(self, _event=None):
        self.playlist_schedule_opened = True
        default_watch_seconds_value = self.playlist_default_watch.total_seconds() or None
        day_defaults = self._collect_playlist_default_watch_by_day_fields()
        default_watch_by_day = (
            None
            if all(value == default_watch_seconds_value for value in day_defaults.values())
            else day_defaults
        )
        self.playlist_initial_default_watch_seconds = default_watch_seconds_value
        self.playlist_initial_default_watch_by_day = (
            dict(default_watch_by_day) if default_watch_by_day else None
        )

        if self.editing_playlist_id:
            playlist = self.find_playlist(self.editing_playlist_id)
            if playlist is None:
                self.show_message("That saved playlist could not be found.", error=True)
                self.show_saved_playlists_screen()
                return
            playlist.default_watch_seconds = default_watch_seconds_value
            playlist.default_watch_by_day = default_watch_by_day
            self.saved_store.save(self.saved_playlists)
            self.refresh_saved_playlist_controls()
            if self.selected_watch_playlist_id == playlist.id:
                self._apply_watch_playlist_defaults(playlist)

        self.show_active_playlist_form_screen()

    def _show_playlist_form_screen(self, title: str, submit_label: str):
        body = ft.Column(
            controls=[
                self._field_with_message(
                    self.playlist_name_field, self.playlist_name_message
                ),
                self._gap(8),
                self._field_with_message(
                    self.playlist_url_field, self.playlist_url_message
                ),
                self._gap(8),
                ft.Row(
                    controls=[
                        SectionLabel("Default time to watch", constants),
                        ft.Container(expand=True),
                        self._compact_action_button(
                            "By day", self.show_default_watch_schedule_screen
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self._gap(6),
                self.playlist_default_watch,
                self._gap(14),
                ft.Row(
                    controls=[
                        SectionLabel("Current Video | Timestamp", constants),
                        ft.Container(expand=True),
                        self._compact_icon_button(
                            ft.Icons.REFRESH_ROUNDED,
                            "Reset timestamp",
                            self.reset_playlist_bookmark_timestamp,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self._gap(8),
                ft.Row(
                    controls=[
                        ft.Row(
                            controls=[
                                self.playlist_bookmark_video_field,
                                self.playlist_bookmark_video_stepper,
                            ],
                            spacing=6,
                            tight=True,
                        ),
                        self.playlist_bookmark_timestamp,
                    ],
                    spacing=8,
                ),
                self._gap(8),
                self.playlist_autofill_checkbox,
                self.playlist_bookmark_message,
                ft.Container(expand=True),
                ft.Row(
                    controls=[
                        SecondaryButton(
                            "Cancel",
                            self.show_saved_playlists_screen,
                            constants,
                        ),
                        PrimaryButton(
                            submit_label,
                            self.save_playlist,
                            constants,
                        ),
                    ],
                    spacing=12,
                ),
            ],
            spacing=0,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        screen = build_screen_card(
            title,
            body,
            constants,
            leading=toolbar_button(
                constants,
                tooltip="Back",
                icon=ft.Icons.ARROW_BACK_ROUNDED,
                on_click=self.show_saved_playlists_screen,
            ),
            trailing=self._toolbar_spacer(),
        )
        self.screen_host.content = self._build_shell(screen)
        self.page.update()

    def refresh_saved_playlist_controls(self):
        has_saved = bool(self.saved_playlists)
        for mode in ("watch", "length"):
            button, icon = self._picker_button_parts(mode)
            button.tooltip = themed_tooltip(
                constants,
                "Choose saved playlist" if has_saved else "No saved playlists yet",
            )
            button.disabled = not has_saved
            icon.color = (
                constants.colors.text
                if has_saved
                else constants.colors.text_subtle
            )
            if not has_saved and self.open_picker_mode == mode:
                self.open_picker_mode = None
        self._sync_selected_playlist_fields()
        self._refresh_picker_overlay()

    def apply_saved_playlist(self, mode: str, playlist: SavedPlaylist):
        self._set_selected_playlist_id(mode, playlist.id)
        self.open_picker_mode = None
        self._refresh_picker_overlay()
        target_field = self._link_field_for_mode(mode)
        target_field.value = playlist.name
        self._set_inline_message(self._link_message_for_mode(mode), None)
        if mode == "watch":
            self._apply_watch_playlist_defaults(playlist)
        self.refresh_saved_playlist_controls()
        self.page.update()

    def find_playlist(self, playlist_id: str) -> SavedPlaylist | None:
        for playlist in self.saved_playlists:
            if playlist.id == playlist_id:
                return playlist
        return None

    def _clear_form_messages(self):
        for message in (
            self.watch_link_message,
            self.watch_start_message,
            self.length_link_message,
            self.playlist_name_message,
            self.playlist_url_message,
            self.playlist_bookmark_message,
        ):
            message.set_message(None)

    def save_playlist(self, _event=None):
        self._set_inline_message(self.playlist_name_message, None)
        self._set_inline_message(self.playlist_url_message, None)
        self._set_inline_message(self.playlist_bookmark_message, None)

        name = self.playlist_name_field.value.strip()
        raw_url = self.playlist_url_field.value.strip()
        bookmark_video_raw = self.playlist_bookmark_video_field.value.strip()
        bookmark_timestamp_seconds = self.playlist_bookmark_timestamp.total_seconds()
        default_watch_seconds = self.playlist_default_watch.total_seconds()
        default_watch_seconds_value = default_watch_seconds or None
        has_error = False

        if not name:
            self._set_inline_message(
                self.playlist_name_message, "Enter a playlist name."
            )
            has_error = True

        try:
            normalized_url = normalize_playlist_url(raw_url)
        except ValidationError as exc:
            self._set_inline_message(self.playlist_url_message, str(exc))
            has_error = True
            normalized_url = ""

        if bookmark_timestamp_seconds > 0 and not bookmark_video_raw:
            self._set_inline_message(
                self.playlist_bookmark_message,
                "Set a bookmark video before saving a bookmark timestamp.",
            )
            has_error = True

        for playlist in self.saved_playlists:
            if playlist.id == self.editing_playlist_id:
                continue
            if playlist.name.casefold() == name.casefold():
                self._set_inline_message(
                    self.playlist_name_message,
                    "A saved playlist with this name already exists.",
                )
                has_error = True
            if normalized_url and playlist.url == normalized_url:
                self._set_inline_message(
                    self.playlist_url_message,
                    "This playlist link is already saved.",
                )
                has_error = True

        if has_error:
            self.page.update()
            return

        bookmark_video_position = int(bookmark_video_raw) if bookmark_video_raw else None
        if self.playlist_schedule_opened:
            day_defaults = self._collect_playlist_default_watch_by_day_fields()
            default_watch_by_day = (
                None
                if all(value == default_watch_seconds_value for value in day_defaults.values())
                else day_defaults
            )
        else:
            default_watch_changed = (
                default_watch_seconds_value
                != self.playlist_initial_default_watch_seconds
            )
            if self.editing_playlist_id and not default_watch_changed:
                default_watch_by_day = (
                    dict(self.playlist_initial_default_watch_by_day)
                    if self.playlist_initial_default_watch_by_day
                    else None
                )
            else:
                default_watch_by_day = None
        previous_url = None
        previous_name = None

        if self.editing_playlist_id:
            playlist = self.find_playlist(self.editing_playlist_id)
            if playlist is None:
                self.show_message("That saved playlist could not be found.", error=True)
                self.show_saved_playlists_screen()
                return
            previous_url = playlist.url
            previous_name = playlist.name
            playlist.name = name
            playlist.url = normalized_url
            playlist.default_watch_seconds = default_watch_seconds_value
            playlist.default_watch_by_day = default_watch_by_day
            playlist.bookmark_video_position = bookmark_video_position
            playlist.bookmark_timestamp_seconds = (
                bookmark_timestamp_seconds if bookmark_video_position is not None else None
            )
            playlist.autofill_bookmark = bool(self.playlist_autofill_checkbox.value)
            message = "Playlist updated."
        else:
            playlist = SavedPlaylist(
                id=uuid4().hex,
                name=name,
                url=normalized_url,
                created_at=datetime.now(timezone.utc).isoformat(),
                default_watch_seconds=default_watch_seconds_value,
                default_watch_by_day=default_watch_by_day,
                bookmark_video_position=bookmark_video_position,
                bookmark_timestamp_seconds=(
                    bookmark_timestamp_seconds
                    if bookmark_video_position is not None
                    else None
                ),
                autofill_bookmark=bool(self.playlist_autofill_checkbox.value),
            )
            self.saved_playlists.append(playlist)
            message = "Playlist saved."

        if previous_url:
            for field in (self.watch_link_field, self.length_link_field):
                current_value = field.value.strip()
                if current_value in {previous_url, previous_name or ""}:
                    field.value = normalized_url

        self.saved_store.save(self.saved_playlists)
        self.refresh_saved_playlist_controls()

        if self.selected_watch_playlist_id == playlist.id:
            self._apply_watch_playlist_defaults(playlist)

        self.show_saved_playlists_screen()
        self.show_message(message)

    def open_delete_dialog(self, playlist_id: str):
        playlist = self.find_playlist(playlist_id)
        if playlist is None:
            self.show_message("That saved playlist could not be found.", error=True)
            self.show_saved_playlists_screen()
            return

        dialog = ft.AlertDialog(
            modal=True,
            bgcolor=constants.colors.panel_bg,
            title=ft.Text(
                "Delete Playlist",
                color=constants.colors.text,
                weight=ft.FontWeight.W_700,
            ),
            content=ft.Text(
                f'Delete "{playlist.name}" from saved playlists?',
                color=constants.colors.text_muted,
            ),
            actions=[
                ft.Row(
                    controls=[
                        SecondaryButton(
                            "Cancel",
                            lambda _event: self.page.close(dialog),
                            constants,
                        ),
                        PrimaryButton(
                            "Delete",
                            lambda _event: self.delete_playlist(dialog, playlist_id),
                            constants,
                        ),
                    ],
                    spacing=12,
                )
            ],
        )
        self.page.open(dialog)

    def delete_playlist(self, dialog: ft.AlertDialog, playlist_id: str):
        self.page.close(dialog)
        playlist = self.find_playlist(playlist_id)
        if playlist is None:
            self.show_message("That saved playlist could not be found.", error=True)
            self.show_saved_playlists_screen()
            return

        self.saved_playlists = [
            item for item in self.saved_playlists if item.id != playlist_id
        ]

        if self.selected_watch_playlist_id == playlist_id:
            self.selected_watch_playlist_id = None
            self.watch_link_field.value = ""
        if self.selected_length_playlist_id == playlist_id:
            self.selected_length_playlist_id = None
            self.length_link_field.value = ""

        self.saved_store.save(self.saved_playlists)
        self.refresh_saved_playlist_controls()
        self.show_saved_playlists_screen()
        self.show_message("Playlist deleted.")
