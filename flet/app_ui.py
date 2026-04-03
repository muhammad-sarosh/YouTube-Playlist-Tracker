from __future__ import annotations

import flet as ft

from components import (
    DurationInput,
    ModeToggle,
    NumberField,
    NumberStepper,
    PrimaryButton,
    ReservedMessage,
    SectionLabel,
    StyledTextField,
    SurfaceCard,
    TimestampInput,
    build_screen_card,
    themed_tooltip,
    toolbar_button,
)
from constants import constants
from services import SavedPlaylist, WEEKDAY_KEYS, format_duration


class AppUIBuildMixin:
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
        self.playlist_bookmark_video_stepper = NumberStepper(
            constants,
            on_increment=self.increment_playlist_bookmark_video,
            on_decrement=self.decrement_playlist_bookmark_video,
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
            tooltip=themed_tooltip(constants, tooltip),
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
                    constants.colors.surface_hover
                    if hovered
                    else constants.colors.surface
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
            tooltip=themed_tooltip(constants, "Choose saved playlist"),
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
        today_watch_seconds = self._effective_watch_default_for_today(playlist)
        row_radius = ft.border_radius.only(
            top_left=constants.sizes.control_radius if is_first else 0,
            top_right=constants.sizes.control_radius if is_first else 0,
            bottom_left=constants.sizes.control_radius if is_last else 0,
            bottom_right=constants.sizes.control_radius if is_last else 0,
        )
        label = ft.Text(
            playlist.name,
            expand=True,
            color=constants.colors.text,
            size=constants.font_sizes.body,
            weight=ft.FontWeight.W_500,
            overflow=ft.TextOverflow.ELLIPSIS,
            no_wrap=True,
        )
        select_area = ft.Container(
            expand=True,
            alignment=ft.alignment.center_left,
            content=label,
            on_click=lambda _event, chosen=playlist, selected_mode=mode: self.apply_saved_playlist(
                selected_mode, chosen
            ),
        )

        edit_icon = ft.Icon(
            ft.Icons.EDIT_ROUNDED,
            size=13,
            color=constants.colors.text_muted,
        )
        edit_button = ft.Container(
            width=22,
            height=22,
            border_radius=7,
            alignment=ft.alignment.center,
            tooltip=themed_tooltip(constants, "Edit playlist"),
            content=edit_icon,
            on_click=lambda _event, chosen=playlist: self.show_edit_playlist_screen(
                chosen.id
            ),
        )

        def _handle_edit_hover(event, control=edit_button, icon=edit_icon):
            hovered = str(event.data).lower() == "true"
            control.bgcolor = (
                constants.colors.surface_hover
                if hovered
                else ft.Colors.TRANSPARENT
            )
            icon.color = (
                constants.colors.text if hovered else constants.colors.text_muted
            )
            if control.page is not None:
                control.update()

        edit_button.on_hover = _handle_edit_hover

        row = ft.Container(
            height=constants.sizes.input_height,
            bgcolor=constants.colors.accent_soft if selected else constants.colors.surface,
            border_radius=row_radius,
            padding=ft.Padding(14, 11, 14, 11),
            content=ft.Row(
                controls=[
                    select_area,
                    *(
                        [
                            ft.Icon(
                                ft.Icons.FLAG_ROUNDED,
                                size=14,
                                color=constants.colors.accent,
                                tooltip=ft.Tooltip(
                                    message=(
                                        "Today's watch goal: "
                                        f"{format_duration(today_watch_seconds).replace(', ', ' ')}"
                                    ),
                                    bgcolor="#D8D2D4",
                                    text_style=ft.TextStyle(
                                        color=constants.colors.page_bg,
                                        size=constants.font_sizes.small,
                                        weight=ft.FontWeight.W_600,
                                    ),
                                ),
                            )
                        ]
                        if today_watch_seconds is not None
                        else []
                    ),
                    edit_button,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
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
        visible_item_limit = 5
        item_height = constants.sizes.input_height
        divider_count = max(len(self.saved_playlists) - 1, 0)
        list_height = len(self.saved_playlists) * item_height + divider_count
        max_panel_height = visible_item_limit * item_height + (visible_item_limit - 1)
        if len(self.saved_playlists) > visible_item_limit:
            self.dropdown_list.height = max_panel_height
            self.dropdown_panel.height = max_panel_height
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
