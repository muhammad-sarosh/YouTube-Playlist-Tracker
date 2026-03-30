from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import flet as ft

from components import (
    DurationInput,
    ModeToggle,
    NumberField,
    PrimaryButton,
    ReservedMessage,
    SectionLabel,
    SecondaryButton,
    StyledTextField,
    SurfaceCard,
    TimestampInput,
    build_screen_card,
    toolbar_button,
)
from constants import constants
from services import (
    PlaylistLengthResult,
    PlaylistService,
    PlaylistServiceError,
    SavedPlaylist,
    SavedPlaylistsStore,
    ValidationError,
    WEEKDAY_KEYS,
    format_clock,
    format_duration,
    format_speed_label,
    normalize_playlist_url,
)

WEEKDAY_LABELS = {day: day.title() for day in WEEKDAY_KEYS}


class PlaylistTrackerApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.base_dir = Path(__file__).resolve().parent
        self.data_dir = self.base_dir / "data"
        self.saved_store = SavedPlaylistsStore(
            self.data_dir,
            legacy_paths=[self.base_dir.parent / "playlists.json"],
        )
        self.playlist_service = PlaylistService()
        self.saved_playlists = self.saved_store.load()

        self.active_mode = "watch"
        self.current_screen = "main"
        self.editing_playlist_id: str | None = None
        self.selected_watch_playlist_id: str | None = None
        self.selected_length_playlist_id: str | None = None
        self.open_picker_mode: str | None = None
        self.copy_feedback_tokens = {"watch": 0, "length": 0}
        self.playlist_schedule_opened = False
        self.playlist_initial_default_watch_seconds: int | None = None
        self.playlist_initial_default_watch_by_day: dict[str, int | None] | None = None
        self._configure_page()

        self.screen_host = ft.Container(expand=True)
        self.dropdown_scrim = ft.Container(
            left=0,
            top=0,
            right=0,
            bottom=0,
            visible=False,
            bgcolor=ft.Colors.with_opacity(0.01, ft.Colors.BLACK),
            on_click=self.close_pickers,
        )
        self.dropdown_list = ft.Column(
            spacing=0,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self.dropdown_panel = ft.Container(
            visible=False,
            left=constants.sizes.internal_padding,
            right=constants.sizes.internal_padding,
            top=0,
            bgcolor=constants.colors.surface,
            border=ft.border.all(1, constants.colors.border),
            border_radius=constants.sizes.control_radius,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=self.dropdown_list,
        )
        self.page.add(
            ft.Stack(
                expand=True,
                clip_behavior=ft.ClipBehavior.NONE,
                controls=[
                    self.screen_host,
                    self.dropdown_scrim,
                    self.dropdown_panel,
                ],
            )
        )

        self._build_main_controls()
        self._build_playlist_form_controls()
        self.refresh_saved_playlist_controls()
        self.show_main_screen()

    def _configure_page(self):
        self.page.title = constants.app_title
        self.page.bgcolor = constants.colors.page_bg
        self.page.padding = 0
        self.page.scroll = ft.ScrollMode.HIDDEN
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window.width = constants.window.default_width
        self.page.window.height = constants.window.default_height
        self.page.window.min_width = constants.window.min_width
        self.page.window.min_height = constants.window.min_height
        self.page.window.resizable = True
        self.page.window.center()
        self.page.on_keyboard_event = self._handle_page_keyboard_event
        self.page.fonts = {
            "NunitoSans": "fonts/NunitoSans-VariableFont_YTLC,opsz,wdth,wght.ttf",
            "IBMPlexMono": "fonts/IBMPlexMono-Regular.ttf",
        }
        self.page.theme = ft.Theme(
            font_family="NunitoSans",
            color_scheme_seed=constants.colors.accent,
            scrollbar_theme=ft.ScrollbarTheme(
                thickness=4,
                radius=8,
            ),
        )

    def _handle_page_keyboard_event(self, event: ft.KeyboardEvent):
        key = (event.key or "").casefold().replace(" ", "")
        if event.ctrl or event.alt or event.meta:
            return
        if getattr(self.page, "dialog", None) is not None:
            return

        if key in {"escape", "esc"}:
            if self.current_screen == "main":
                if self.open_picker_mode is not None:
                    self.close_pickers()
            elif self.current_screen == "saved":
                self.show_main_screen()
            elif self.current_screen == "schedule":
                self.show_active_playlist_form_screen()
            elif self.current_screen in {"add", "edit"}:
                self.show_saved_playlists_screen()
            return

        if key in {"enter", "numpadenter"} and self.current_screen == "edit":
            self.save_playlist()

    def _build_main_controls(self):
        self.manage_playlists_button = toolbar_button(
            constants,
            tooltip="Saved playlists",
            image_src="icons/edit_playlist_icon.png",
            on_click=self.show_saved_playlists_screen,
        )
        self.mode_toggle = ModeToggle(
            constants,
            value=self.active_mode,
            on_change=self.change_mode,
        )

        self.watch_link_field = StyledTextField("Playlist Link", constants)
        self.watch_link_field.on_change = self._handle_watch_link_change
        self.watch_link_message = ReservedMessage(constants)
        self.watch_picker_icon = ft.Icon(
            ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
            color=constants.colors.text,
            size=22,
        )
        self.watch_picker_button = self._build_saved_picker_button("watch")
        self.watch_start_video_field = NumberField(
            constants,
            width=54,
            min_value=1,
            default_number=1,
            monospace=True,
        )
        self.watch_timestamp = TimestampInput(constants)
        self.watch_start_message = ReservedMessage(constants)
        self.watch_duration = DurationInput(constants)
        self.watch_result_content = ft.Column(
            controls=[
                self._result_body(
                    self._placeholder_result("Result will appear here."),
                    min_height=112,
                )
            ],
            spacing=0,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
        )
        self.watch_result_text: str | None = None
        self.watch_result_copy_button = self._compact_icon_button(
            ft.Icons.CONTENT_COPY_ROUNDED,
            "Copy result",
            lambda _event: self.copy_result_text("watch"),
        )
        self.watch_result_copy_button.disabled = True
        self.watch_result_card = SurfaceCard(constants, self.watch_result_content)
        self.watch_result_card.expand = True
        self.watch_calculate_button = PrimaryButton(
            "Calculate", self.handle_watch_duration, constants
        )

        self.length_link_field = StyledTextField("Playlist Link", constants)
        self.length_link_field.on_change = self._handle_length_link_change
        self.length_link_message = ReservedMessage(constants)
        self.length_picker_icon = ft.Icon(
            ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
            color=constants.colors.text,
            size=22,
        )
        self.length_picker_button = self._build_saved_picker_button("length")
        self.length_start_video_field = NumberField(
            constants,
            width=54,
            min_value=1,
            default_number=None,
            allow_empty=True,
            monospace=True,
            hint_text="-",
        )
        self.length_end_video_field = NumberField(
            constants,
            width=54,
            min_value=1,
            default_number=None,
            allow_empty=True,
            monospace=True,
            hint_text="-",
        )
        self.length_result_content = ft.Column(
            controls=[
                self._result_body(
                    self._placeholder_result("Result will appear here."),
                    min_height=96,
                )
            ],
            spacing=0,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
        )
        self.length_result_text: str | None = None
        self.length_result_copy_button = self._compact_icon_button(
            ft.Icons.CONTENT_COPY_ROUNDED,
            "Copy result",
            lambda _event: self.copy_result_text("length"),
        )
        self.length_result_copy_button.disabled = True
        self.length_result_card = SurfaceCard(constants, self.length_result_content)
        self.length_result_card.expand = True
        self.length_calculate_button = PrimaryButton(
            "Calculate", self.handle_playlist_length, constants
        )

        self.watch_section = ft.Column(
            controls=[
                self._field_with_message(
                    self._playlist_link_row(
                        self.watch_link_field, self.watch_picker_button
                    ),
                    self.watch_link_message,
                ),
                self._gap(8),
                ft.Row(
                    controls=[
                        SectionLabel("Starting Video | Timestamp", constants),
                        ft.Container(expand=True),
                        self._compact_icon_button(
                            ft.Icons.REFRESH_ROUNDED,
                            "Reset starting video and timestamp",
                            self.reset_watch_start,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self._gap(8),
                ft.Row(
                    controls=[self.watch_start_video_field, self.watch_timestamp],
                    spacing=8,
                ),
                self._gap(4),
                self.watch_start_message,
                self._gap(14),
                ft.Row(
                    controls=[
                        SectionLabel("Time to watch", constants),
                        ft.Container(expand=True),
                        self._compact_icon_button(
                            ft.Icons.REFRESH_ROUNDED,
                            "Reset time to watch",
                            self.reset_watch_duration,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self._gap(6),
                self.watch_duration,
                self._gap(18),
                ft.Row(controls=[self.watch_calculate_button], spacing=0),
                self._gap(18),
                ft.Row(
                    controls=[
                        SectionLabel("Result", constants),
                        ft.Container(expand=True),
                        self.watch_result_copy_button,
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self._gap(10),
                self.watch_result_card,
            ],
            spacing=0,
            tight=True,
            expand=True,
        )

        self.length_section = ft.Column(
            controls=[
                self._field_with_message(
                    self._playlist_link_row(
                        self.length_link_field, self.length_picker_button
                    ),
                    self.length_link_message,
                ),
                self._gap(8),
                ft.Row(
                    controls=[
                        self._labeled_small_field(
                            "Start Video", self.length_start_video_field
                        ),
                        self._labeled_small_field(
                            "End Video", self.length_end_video_field
                        ),
                        ft.Container(expand=True),
                        self._compact_icon_button(
                            ft.Icons.REFRESH_ROUNDED,
                            "Reset start and end video",
                            self.reset_length_range,
                        ),
                    ],
                    spacing=16,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
                self._gap(18),
                ft.Row(controls=[self.length_calculate_button], spacing=0),
                self._gap(18),
                ft.Row(
                    controls=[
                        SectionLabel("Result", constants),
                        ft.Container(expand=True),
                        self.length_result_copy_button,
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self._gap(10),
                self.length_result_card,
            ],
            spacing=0,
            tight=True,
            expand=True,
            visible=False,
        )

        body = ft.Column(
            controls=[
                self.mode_toggle,
                self._gap(18),
                self.watch_section,
                self.length_section,
            ],
            spacing=0,
            expand=True,
        )

        self.main_screen = build_screen_card(
            "Playlist Calculator",
            body,
            constants,
            leading=self._toolbar_spacer(),
            trailing=self.manage_playlists_button,
        )

    def _build_playlist_form_controls(self):
        self.playlist_name_field = StyledTextField("Playlist Name", constants)
        self.playlist_url_field = StyledTextField("Link", constants)
        self.playlist_name_message = ReservedMessage(constants)
        self.playlist_url_message = ReservedMessage(constants)
        self.playlist_bookmark_message = ReservedMessage(constants)

        self.playlist_default_watch = DurationInput(constants)
        self.playlist_default_watch_by_day_fields = {
            day: DurationInput(constants) for day in WEEKDAY_KEYS
        }
        self.playlist_bookmark_video_field = NumberField(
            constants,
            width=62,
            min_value=1,
            default_number=None,
            allow_empty=True,
            monospace=True,
            hint_text="-",
        )
        self.playlist_bookmark_timestamp = TimestampInput(constants)
        self.playlist_autofill_checkbox = ft.Checkbox(
            value=True,
            label="Auto-fill start video and time",
            fill_color=constants.colors.accent,
            check_color=constants.colors.text,
            active_color=constants.colors.accent,
            label_style=ft.TextStyle(
                size=constants.font_sizes.body,
                color=constants.colors.text_muted,
                weight=ft.FontWeight.W_600,
            ),
        )

    def _toolbar_spacer(self) -> ft.Container:
        return ft.Container(
            width=constants.sizes.icon_button_size,
            height=constants.sizes.icon_button_size,
        )

    def _gap(self, height: int) -> ft.Container:
        return ft.Container(height=height)

    def _compact_action_button(self, text: str, on_click) -> ft.TextButton:
        return ft.TextButton(
            text=text,
            on_click=on_click,
            height=30,
            style=ft.ButtonStyle(
                overlay_color=ft.Colors.TRANSPARENT,
                bgcolor={
                    ft.ControlState.DEFAULT: constants.colors.surface_muted,
                    ft.ControlState.HOVERED: constants.colors.surface_hover,
                    ft.ControlState.DISABLED: ft.Colors.with_opacity(
                        0.4, constants.colors.surface_muted
                    ),
                },
                color={
                    ft.ControlState.DEFAULT: constants.colors.text_muted,
                    ft.ControlState.HOVERED: constants.colors.text,
                    ft.ControlState.DISABLED: constants.colors.text_subtle,
                },
                side=ft.BorderSide(
                    width=1,
                    color=ft.Colors.with_opacity(0.38, constants.colors.border),
                ),
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding(10, 0, 10, 0),
                text_style=ft.TextStyle(
                    size=constants.font_sizes.small,
                    weight=ft.FontWeight.W_600,
                ),
            ),
        )

    def _compact_icon_button(
        self, icon_name: str, tooltip: str, on_click
    ) -> ft.Container:
        icon = ft.Icon(icon_name, size=16, color=constants.colors.text_muted)
        button = ft.Container(
            width=30,
            height=30,
            bgcolor=constants.colors.surface,
            border=ft.border.all(
                1, ft.Colors.with_opacity(0.38, constants.colors.border)
            ),
            border_radius=10,
            alignment=ft.alignment.center,
            tooltip=tooltip,
            content=icon,
        )

        def _handle_click(event, control=button):
            if control.disabled:
                return
            on_click(event)

        def _handle_hover(event, control=button, icon_control=icon):
            hovered = str(event.data).lower() == "true"
            if control.disabled:
                control.bgcolor = ft.Colors.with_opacity(
                    0.4, constants.colors.surface
                )
                icon_control.color = constants.colors.text_subtle
            else:
                control.bgcolor = (
                    constants.colors.surface_hover if hovered else constants.colors.surface
                )
                icon_control.color = (
                    constants.colors.text if hovered else constants.colors.text_muted
                )
            if control.page is not None:
                control.update()

        button.on_click = _handle_click
        button.on_hover = _handle_hover
        return button

    def _format_result_duration(self, total_seconds: int) -> str:
        return format_duration(total_seconds).replace(", ", " ")

    def _build_shell(self, screen: ft.Control) -> ft.Container:
        return ft.Container(
            expand=True,
            bgcolor=constants.colors.page_bg,
            content=screen,
        )

    def _playlist_link_row(
        self, field: StyledTextField, picker_button: ft.Control
    ) -> ft.Row:
        return ft.Row(
            controls=[field, picker_button],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def _field_with_message(
        self, control: ft.Control, message: ReservedMessage
    ) -> ft.Column:
        return ft.Column(
            controls=[control, message],
            spacing=4,
            tight=True,
        )

    def _picker_button_parts(self, mode: str) -> tuple[ft.Container, ft.Icon]:
        if mode == "watch":
            return self.watch_picker_button, self.watch_picker_icon
        return self.length_picker_button, self.length_picker_icon

    def _picker_top(self) -> int:
        title_row_height = constants.sizes.icon_button_size
        mode_toggle_height = 42
        return (
            constants.sizes.internal_padding
            + title_row_height
            + 18
            + mode_toggle_height
            + 18
            + constants.sizes.input_height
            + 6
        )

    def _build_saved_picker_button(self, mode: str) -> ft.Container:
        icon = self.watch_picker_icon if mode == "watch" else self.length_picker_icon
        button = ft.Container(
            width=40,
            height=constants.sizes.input_height,
            bgcolor=constants.colors.surface,
            border=ft.border.all(1, constants.colors.border),
            border_radius=constants.sizes.control_radius,
            tooltip="Choose saved playlist",
            alignment=ft.alignment.center,
            content=icon,
        )

        def _handle_click(_event, selected_mode=mode):
            self.toggle_picker(selected_mode)

        def _handle_hover(event, control=button, selected_mode=mode):
            if control.disabled:
                control.bgcolor = constants.colors.surface
            elif self.open_picker_mode == selected_mode:
                control.bgcolor = constants.colors.surface_hover
            else:
                control.bgcolor = (
                    constants.colors.surface_hover
                    if str(event.data).lower() == "true"
                    else constants.colors.surface
                )
            if control.page is not None:
                control.update()

        button.on_click = _handle_click
        button.on_hover = _handle_hover
        return button

    def _picker_item_content(
        self,
        mode: str,
        playlist: SavedPlaylist,
        *,
        selected: bool,
        is_first: bool,
        is_last: bool,
    ) -> ft.Container:
        row_radius = ft.border_radius.only(
            top_left=constants.sizes.control_radius if is_first else 0,
            top_right=constants.sizes.control_radius if is_first else 0,
            bottom_left=constants.sizes.control_radius if is_last else 0,
            bottom_right=constants.sizes.control_radius if is_last else 0,
        )
        row = ft.Container(
            bgcolor=constants.colors.accent_soft if selected else constants.colors.surface,
            border_radius=row_radius,
            padding=ft.Padding(14, 11, 14, 11),
            content=ft.Row(
                controls=[
                    ft.Text(
                        playlist.name,
                        expand=True,
                        color=constants.colors.text,
                        size=constants.font_sizes.body,
                        weight=ft.FontWeight.W_500,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        no_wrap=True,
                    )
                ],
                spacing=0,
            ),
            on_click=lambda _event, chosen=playlist, selected_mode=mode: self.apply_saved_playlist(
                selected_mode, chosen
            ),
        )

        def _handle_hover(event, control=row, is_selected=selected):
            if is_selected:
                control.bgcolor = constants.colors.accent_soft
            else:
                control.bgcolor = (
                    constants.colors.surface_hover
                    if str(event.data).lower() == "true"
                    else constants.colors.surface
                )
            if control.page is not None:
                control.update()

        row.on_hover = _handle_hover
        return row

    def _refresh_picker_overlay(self):
        if (
            self.current_screen != "main"
            or self.open_picker_mode is None
            or not self.saved_playlists
        ):
            self.dropdown_scrim.visible = False
            self.dropdown_panel.visible = False
            self.dropdown_list.controls = []
            self.dropdown_list.height = None
            self.dropdown_panel.height = None
            for mode in ("watch", "length"):
                button, icon = self._picker_button_parts(mode)
                button.bgcolor = constants.colors.surface
                icon.name = ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED
            return

        mode = self.open_picker_mode
        selected_id = self._selected_playlist_id_for_mode(mode)
        list_controls: list[ft.Control] = []
        for index, playlist in enumerate(self.saved_playlists):
            is_first = index == 0
            is_last = index == len(self.saved_playlists) - 1
            list_controls.append(
                self._picker_item_content(
                    mode,
                    playlist,
                    selected=selected_id == playlist.id,
                    is_first=is_first,
                    is_last=is_last,
                )
            )
            if not is_last:
                list_controls.append(
                    ft.Container(
                        height=1,
                        bgcolor=ft.Colors.with_opacity(
                            0.26, constants.colors.border
                        ),
                    )
                )
        self.dropdown_list.controls = list_controls
        divider_count = max(len(self.saved_playlists) - 1, 0)
        list_height = len(self.saved_playlists) * 44 + divider_count
        if list_height > 220:
            self.dropdown_list.height = 220
            self.dropdown_panel.height = 220
        else:
            self.dropdown_list.height = None
            self.dropdown_panel.height = None
        self.dropdown_panel.top = self._picker_top()
        self.dropdown_scrim.visible = True
        self.dropdown_panel.visible = True
        for picker_mode in ("watch", "length"):
            button, icon = self._picker_button_parts(picker_mode)
            is_open = picker_mode == mode
            button.bgcolor = (
                constants.colors.surface_hover
                if is_open
                else constants.colors.surface
            )
            icon.name = (
                ft.Icons.KEYBOARD_ARROW_UP_ROUNDED
                if is_open
                else ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED
            )

    def _labeled_small_field(self, label: str, field: NumberField) -> ft.Column:
        return ft.Column(
            controls=[
                ft.Text(
                    label,
                    size=constants.font_sizes.small,
                    color=constants.colors.text_muted,
                    weight=ft.FontWeight.W_600,
                ),
                field,
            ],
            spacing=6,
            tight=True,
        )

    def _placeholder_result(self, text: str) -> ft.Text:
        return ft.Text(
            text,
            color=constants.colors.text_subtle,
            size=constants.font_sizes.body,
            weight=ft.FontWeight.W_400,
        )

    def _result_body(
        self, control: ft.Control, *, min_height: int | None = None
    ) -> ft.Container:
        return ft.Container(
            content=ft.SelectionArea(content=control),
            alignment=ft.alignment.top_left,
            height=min_height,
        )

    def _result_line(
        self, label: str, value: str | None = None, *, monospace_value: bool = False
    ) -> ft.Text:
        spans = [
            ft.TextSpan(
                text=label,
                style=ft.TextStyle(
                    color=constants.colors.text,
                    size=constants.font_sizes.body,
                    weight=ft.FontWeight.W_500,
                    font_family="NunitoSans",
                ),
            )
        ]
        if value is not None:
            spans.append(
                ft.TextSpan(
                    text=value,
                    style=ft.TextStyle(
                        color=constants.colors.text,
                        size=constants.font_sizes.body,
                        weight=ft.FontWeight.W_500,
                        font_family="IBMPlexMono" if monospace_value else "NunitoSans",
                    ),
                )
            )
        return ft.Text(
            spans=spans,
        )

    def _plain_result_line(self, text: str) -> ft.Text:
        return ft.Text(
            text,
            color=constants.colors.text,
            size=constants.font_sizes.body,
            weight=ft.FontWeight.W_500,
        )

    def _note_text(self, text: str) -> ft.Text:
        return ft.Text(
            text,
            color=constants.colors.text_subtle,
            size=constants.font_sizes.small,
        )

    def _set_inline_message(
        self, message_control: ReservedMessage, message: str | None
    ):
        message_control.set_message(message)
        if message_control.page is not None:
            message_control.update()

    def _build_result_groups(
        self,
        groups: list[list[ft.Control]],
        notes: list[str] | None = None,
        *,
        group_gap: int = 14,
        line_gap: int = 8,
    ) -> ft.Column:
        controls: list[ft.Control] = []
        for group in groups:
            controls.append(
                ft.Column(
                    controls=group,
                    spacing=line_gap,
                    tight=True,
                )
            )
        for note in notes or []:
            controls.append(self._note_text(note))
        return ft.Column(controls=controls, spacing=group_gap, tight=True)

    def _compose_result_copy_text(
        self, groups: list[list[str]], notes: list[str] | None = None
    ) -> str:
        sections = ["\n".join(group) for group in groups if group]
        if notes:
            sections.append("\n".join(note for note in notes if note))
        return "\n\n".join(section for section in sections if section).strip()

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
        button.tooltip = "Copied"
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
        button.tooltip = "Copy result"
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
            tooltip=tooltip,
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
                SectionLabel("Current Video | Timestamp", constants),
                self._gap(8),
                ft.Row(
                    controls=[
                        self.playlist_bookmark_video_field,
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
            button.tooltip = (
                "Choose saved playlist" if has_saved else "No saved playlists yet"
            )
            button.disabled = not has_saved
            icon.color = constants.colors.text if has_saved else constants.colors.text_subtle
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

    def _active_link_field(self) -> StyledTextField:
        if self.active_mode == "watch":
            return self.watch_link_field
        return self.length_link_field

    def show_message(self, message: str, *, error: bool = False):
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=constants.colors.text),
            bgcolor=constants.colors.danger if error else constants.colors.accent_dark,
            behavior=ft.SnackBarBehavior.FLOATING,
        )
        self.page.snack_bar.open = True
        self.page.update()


def main(page: ft.Page):
    PlaylistTrackerApp(page)


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
