from __future__ import annotations

from types import SimpleNamespace
from typing import Callable

import flet as ft


def _button_shape(radius: int) -> ft.RoundedRectangleBorder:
    return ft.RoundedRectangleBorder(radius=radius)


def themed_tooltip(constants: SimpleNamespace, message: str) -> ft.Tooltip:
    return ft.Tooltip(
        message=message,
        bgcolor="#D8D2D4",
        wait_duration=650,
        text_style=ft.TextStyle(
            color=constants.colors.page_bg,
            size=constants.font_sizes.small,
            weight=ft.FontWeight.W_600,
        ),
    )


class SectionLabel(ft.Text):
    def __init__(self, text: str, constants: SimpleNamespace):
        super().__init__(
            value=text,
            size=constants.font_sizes.section,
            weight=ft.FontWeight.W_600,
            color=constants.colors.text,
        )


class ReservedMessage(ft.Text):
    def __init__(self, constants: SimpleNamespace):
        super().__init__(
            value=" ",
            size=constants.font_sizes.small,
            color=constants.colors.danger,
            height=16,
        )

    def set_message(self, message: str | None):
        self.value = message or " "


class StyledTextField(ft.TextField):
    def __init__(self, hint_text: str, constants: SimpleNamespace, value: str = ""):
        super().__init__()
        self.value = value
        self.hint_text = hint_text
        self.hint_style = ft.TextStyle(
            color=constants.colors.text_subtle,
            size=constants.font_sizes.body,
        )
        self.text_style = ft.TextStyle(
            color=constants.colors.text,
            size=constants.font_sizes.body,
            weight=ft.FontWeight.W_400,
        )
        self.cursor_color = constants.colors.text
        self.selection_color = ft.Colors.with_opacity(0.24, constants.colors.accent)
        self.enable_interactive_selection = True
        self.always_call_on_tap = True
        self.autocorrect = False
        self.enable_suggestions = False
        self.border = ft.InputBorder.OUTLINE
        self.border_radius = constants.sizes.control_radius
        self.border_color = constants.colors.border
        self.focused_border_color = constants.colors.accent
        self.filled = True
        self.bgcolor = constants.colors.surface
        self.height = constants.sizes.input_height
        self.content_padding = ft.Padding(14, 8, 14, 8)
        self.expand = True


class NumberField(ft.TextField):
    def __init__(
        self,
        constants: SimpleNamespace,
        *,
        width: int | None = None,
        min_value: int | None = 0,
        max_value: int | None = None,
        default_number: int | None = 0,
        initial_value: int | None = None,
        allow_empty: bool = False,
        monospace: bool = True,
        pad_to: int | None = None,
        centered: bool = True,
        borderless: bool = False,
        bgcolor: str | None = None,
        expand: bool | int | None = None,
        hint_text: str | None = None,
    ):
        super().__init__()
        self.constants = constants
        self.min_value = min_value
        self.max_value = max_value
        self.default_number = default_number
        self.allow_empty = allow_empty
        self.pad_to = pad_to
        self._centered = centered
        self._focused = False
        self._suspend_change = False
        self.on_focus_changed: Callable[[bool], None] | None = None

        self.width = width
        self.expand = expand
        self.height = constants.sizes.input_height
        self.cursor_color = constants.colors.text
        self.selection_color = ft.Colors.with_opacity(0.24, constants.colors.accent)
        self.keyboard_type = ft.KeyboardType.NUMBER
        self.input_filter = ft.NumbersOnlyInputFilter()
        self.border = ft.InputBorder.OUTLINE
        self.border_radius = constants.sizes.control_radius
        self.border_color = "transparent" if borderless else constants.colors.border
        self.focused_border_color = (
            "transparent" if borderless else constants.colors.accent
        )
        self.bgcolor = bgcolor if bgcolor is not None else constants.colors.surface
        self.content_padding = ft.Padding(12, 8, 12, 8)
        self.text_align = ft.TextAlign.CENTER if centered else ft.TextAlign.LEFT
        self.text_style = ft.TextStyle(
            color=constants.colors.text,
            size=constants.font_sizes.number,
            weight=ft.FontWeight.W_400,
            font_family="IBMPlexMono" if monospace else "NunitoSans",
        )
        default_hint = (
            self._format_for_display(default_number)
            if default_number is not None
            else ""
        )
        self.hint_text = hint_text if hint_text is not None else default_hint
        self.hint_style = ft.TextStyle(
            color=ft.Colors.with_opacity(0.88, constants.colors.text),
            size=constants.font_sizes.number,
            weight=ft.FontWeight.W_400,
            font_family="IBMPlexMono" if monospace else "NunitoSans",
        )
        self.value = (
            ""
            if initial_value is None
            else self._format_for_display(initial_value)
        )
        self.on_change = self._handle_change
        self.on_focus = self._handle_focus
        self.on_blur = self._handle_blur

    def _handle_focus(self, _event=None):
        self._focused = True
        if self.on_focus_changed is not None:
            self.on_focus_changed(True)

    def _handle_blur(self, _event=None):
        self._focused = False
        if self.on_focus_changed is not None:
            self.on_focus_changed(False)
        self._normalize_on_exit()
        if self.page is not None:
            self.update()

    def _handle_change(self, _event=None):
        if self._suspend_change:
            return

        raw = "".join(ch for ch in (self.value or "") if ch.isdigit())
        if raw == "":
            self._set_value("")
            return

        value = int(raw)
        if self.min_value is not None and value < self.min_value:
            value = self.min_value
        if self.max_value is not None and value > self.max_value:
            value = self.max_value

        if self.pad_to is not None and not self._focused:
            display = str(value).zfill(self.pad_to)
        else:
            display = str(value)

        self._set_value(display)

    def _normalize_on_exit(self):
        if (self.value or "").strip() == "":
            if self.allow_empty:
                self.value = ""
                return
            self.value = ""
            return

        value = int(self.value)
        if self.min_value is not None and value < self.min_value:
            value = self.min_value
        if self.max_value is not None and value > self.max_value:
            value = self.max_value
        self.value = self._format_for_display(value)

    def _format_for_display(self, value: int | None) -> str:
        if value is None:
            return ""
        value = max(0, int(value))
        if self.pad_to is not None:
            return str(value).zfill(self.pad_to)
        return str(value)

    def _set_value(self, value: str):
        if self.value == value:
            return
        self._suspend_change = True
        self.value = value
        self._suspend_change = False
        if self.page is not None:
            self.update()

    def clamp_value(self):
        self._normalize_on_exit()

    def int_value(self, default: int = 0) -> int:
        raw = (self.value or "").strip()
        if raw:
            return int(raw)
        if self.default_number is not None:
            return int(self.default_number)
        return default

    def set_int_value(self, value: int | None):
        if value is None:
            self.value = ""
        else:
            self.value = self._format_for_display(value)

    def reset(self):
        self.value = ""

    def increment(self, step: int = 1):
        raw = (self.value or "").strip()
        if raw:
            value = int(raw) + step
        else:
            value = self.min_value if self.min_value is not None else 0
        if self.max_value is not None:
            value = min(value, self.max_value)
        if self.min_value is not None:
            value = max(value, self.min_value)
        self._set_value(self._format_for_display(value))

    def decrement(self, step: int = 1):
        raw = (self.value or "").strip()
        if not raw:
            return
        value = int(raw) - step
        if self.max_value is not None:
            value = min(value, self.max_value)
        if self.min_value is not None:
            value = max(value, self.min_value)
        self._set_value(self._format_for_display(value))


class InlineNumberField(NumberField):
    def __init__(
        self,
        constants: SimpleNamespace,
        *,
        max_value: int | None = None,
    ):
        super().__init__(
            constants,
            width=54,
            min_value=0,
            max_value=max_value,
            default_number=0,
            initial_value=None,
            allow_empty=False,
            monospace=True,
            pad_to=2,
            borderless=True,
            bgcolor=ft.Colors.TRANSPARENT,
        )
        self.content_padding = ft.Padding(6, 6, 6, 6)
        self.height = 32


class TimestampInput(ft.Container):
    def __init__(self, constants: SimpleNamespace):
        super().__init__()
        self.constants = constants
        self._focused_children = 0
        self.hours = InlineNumberField(constants)
        self.minutes = InlineNumberField(constants, max_value=59)
        self.seconds = InlineNumberField(constants, max_value=59)
        for field in (self.hours, self.minutes, self.seconds):
            field.on_focus_changed = self._handle_child_focus_change

        colon_style = dict(
            size=constants.font_sizes.number,
            weight=ft.FontWeight.W_700,
            color=constants.colors.text_muted,
        )

        self.content = ft.Row(
            controls=[
                self.hours,
                ft.Text(":", **colon_style),
                self.minutes,
                ft.Text(":", **colon_style),
                self.seconds,
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.expand = True
        self.padding = ft.Padding(8, 4, 8, 4)
        self.bgcolor = constants.colors.surface
        self.border = ft.border.all(1, constants.colors.border)
        self.border_radius = constants.sizes.control_radius

    def _handle_child_focus_change(self, focused: bool):
        if focused:
            self._focused_children += 1
        else:
            self._focused_children = max(0, self._focused_children - 1)
        border_color = (
            self.constants.colors.accent
            if self._focused_children > 0
            else self.constants.colors.border
        )
        self.border = ft.border.all(1, border_color)
        if self.page is not None:
            self.update()

    def total_seconds(self) -> int:
        return (
            self.hours.int_value()
            * 3600
            + self.minutes.int_value() * 60
            + self.seconds.int_value()
        )

    def set_seconds(self, total_seconds: int):
        total_seconds = max(0, int(total_seconds))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.hours.set_int_value(hours)
        self.minutes.set_int_value(minutes)
        self.seconds.set_int_value(seconds)

    def reset(self):
        self.hours.reset()
        self.minutes.reset()
        self.seconds.reset()


class DurationInput(ft.Row):
    def __init__(self, constants: SimpleNamespace):
        self.hours = NumberField(
            constants,
            width=46,
            min_value=0,
            default_number=0,
            monospace=True,
        )
        self.minutes = NumberField(
            constants,
            width=46,
            min_value=0,
            max_value=59,
            default_number=0,
            monospace=True,
        )
        self.seconds = NumberField(
            constants,
            width=46,
            min_value=0,
            max_value=59,
            default_number=0,
            monospace=True,
        )

        super().__init__(
            controls=[
                self._unit_column("H", self.hours, constants),
                self._colon(constants),
                self._unit_column("M", self.minutes, constants),
                self._colon(constants),
                self._unit_column("S", self.seconds, constants),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.END,
        )

    def _colon(self, constants: SimpleNamespace) -> ft.Container:
        return ft.Container(
            content=ft.Text(
                ":",
                color=constants.colors.text_muted,
                size=16,
                weight=ft.FontWeight.W_700,
            ),
            margin=ft.margin.only(bottom=8),
        )

    def _unit_column(
        self, label: str, field: NumberField, constants: SimpleNamespace
    ) -> ft.Column:
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
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def total_seconds(self) -> int:
        return (
            self.hours.int_value()
            * 3600
            + self.minutes.int_value() * 60
            + self.seconds.int_value()
        )

    def set_seconds(self, total_seconds: int | None):
        total_seconds = max(0, int(total_seconds or 0))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.hours.set_int_value(hours)
        self.minutes.set_int_value(minutes)
        self.seconds.set_int_value(seconds)

    def reset(self):
        self.hours.reset()
        self.minutes.reset()
        self.seconds.reset()


class NumberStepper(ft.Container):
    def __init__(
        self,
        constants: SimpleNamespace,
        *,
        on_increment: Callable,
        on_decrement: Callable,
    ):
        super().__init__()
        self.constants = constants
        self._top = self._build_half(
            ft.Icons.KEYBOARD_ARROW_UP_ROUNDED,
            "Increase",
            on_increment,
            top_half=True,
        )
        self._bottom = self._build_half(
            ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
            "Decrease",
            on_decrement,
            top_half=False,
        )

        self.width = 22
        self.height = constants.sizes.input_height
        self.bgcolor = constants.colors.surface
        self.border = ft.border.all(1, constants.colors.border)
        self.border_radius = constants.sizes.control_radius
        self.clip_behavior = ft.ClipBehavior.HARD_EDGE
        self.content = ft.Column(
            controls=[
                self._top,
                ft.Container(height=1, bgcolor=constants.colors.border),
                self._bottom,
            ],
            spacing=0,
            tight=True,
        )

    def _build_half(
        self,
        icon_name: str,
        tooltip: str,
        on_click: Callable,
        *,
        top_half: bool,
    ) -> ft.Container:
        icon = ft.Icon(icon_name, size=11, color=self.constants.colors.text_muted)
        control = ft.Container(
            height=(self.constants.sizes.input_height - 1) / 2,
            alignment=ft.alignment.center,
            tooltip=themed_tooltip(self.constants, tooltip),
            content=icon,
            border_radius=ft.border_radius.only(
                top_left=self.constants.sizes.control_radius if top_half else 0,
                top_right=self.constants.sizes.control_radius if top_half else 0,
                bottom_left=self.constants.sizes.control_radius if not top_half else 0,
                bottom_right=self.constants.sizes.control_radius
                if not top_half
                else 0,
            ),
        )

        def _handle_hover(event, half=control, half_icon=icon):
            hovered = str(event.data).lower() == "true"
            half.bgcolor = (
                self.constants.colors.surface_hover
                if hovered
                else ft.Colors.TRANSPARENT
            )
            half_icon.color = (
                self.constants.colors.text
                if hovered
                else self.constants.colors.text_muted
            )
            if half.page is not None:
                half.update()

        def _handle_click(event, half=control):
            half.bgcolor = ft.Colors.TRANSPARENT
            if half.page is not None:
                half.update()
            on_click(event)

        control.on_hover = _handle_hover
        control.on_click = _handle_click
        return control


class PrimaryButton(ft.ElevatedButton):
    def __init__(
        self,
        text: str,
        on_click: Callable,
        constants: SimpleNamespace,
        *,
        expand: bool = True,
    ):
        super().__init__()
        self.text = text
        self.on_click = on_click
        self.expand = expand
        self.height = constants.sizes.action_height
        self.style = ft.ButtonStyle(
            color=constants.colors.text,
            bgcolor={
                ft.ControlState.DEFAULT: constants.colors.accent,
                ft.ControlState.HOVERED: constants.colors.accent_dark,
                ft.ControlState.DISABLED: ft.Colors.with_opacity(
                    0.45, constants.colors.accent
                ),
            },
            shape=_button_shape(constants.sizes.control_radius),
            elevation=0,
            shadow_color=ft.Colors.TRANSPARENT,
            text_style=ft.TextStyle(
                size=constants.font_sizes.body,
                weight=ft.FontWeight.W_600,
                font_family="NunitoSans",
            ),
            padding=ft.Padding(14, 10, 14, 10),
        )


class SecondaryButton(ft.OutlinedButton):
    def __init__(
        self,
        text: str,
        on_click: Callable,
        constants: SimpleNamespace,
        *,
        expand: bool = True,
    ):
        super().__init__()
        self.text = text
        self.on_click = on_click
        self.expand = expand
        self.height = constants.sizes.action_height
        self.style = ft.ButtonStyle(
            color=constants.colors.text_muted,
            bgcolor={
                ft.ControlState.DEFAULT: constants.colors.surface_muted,
                ft.ControlState.HOVERED: constants.colors.surface_hover,
            },
            side=ft.BorderSide(
                width=1,
                color=ft.Colors.with_opacity(0.45, constants.colors.border),
            ),
            shape=_button_shape(constants.sizes.control_radius),
            text_style=ft.TextStyle(
                size=constants.font_sizes.body,
                weight=ft.FontWeight.W_600,
            ),
            padding=ft.Padding(14, 10, 14, 10),
        )


class SurfaceCard(ft.Container):
    def __init__(self, constants: SimpleNamespace, content: ft.Control | None = None):
        super().__init__()
        self.content = content
        self.bgcolor = constants.colors.surface
        self.border = ft.border.all(1, constants.colors.border)
        self.border_radius = constants.sizes.control_radius
        self.padding = ft.Padding(14, 14, 14, 14)


class ModeToggle(ft.Container):
    def __init__(
        self,
        constants: SimpleNamespace,
        *,
        value: str,
        on_change: Callable[[str], None],
    ):
        super().__init__()
        self.constants = constants
        self.value = value
        self.on_change = on_change
        self.watch_button = self._build_button("watch", "Watch Duration")
        self.length_button = self._build_button("length", "Playlist Length")
        self.content = ft.Row(
            controls=[self.watch_button, self.length_button],
            spacing=4,
        )
        self.padding = 4
        self.bgcolor = constants.colors.surface
        self.border = ft.border.all(
            1, ft.Colors.with_opacity(0.45, constants.colors.border)
        )
        self.border_radius = constants.sizes.control_radius
        self.set_value(value)

    def _build_button(self, key: str, text: str) -> ft.TextButton:
        return ft.TextButton(
            text=text,
            expand=True,
            height=34,
            style=ft.ButtonStyle(
                overlay_color=ft.Colors.TRANSPARENT,
                shape=_button_shape(self.constants.sizes.control_radius - 2),
                padding=ft.Padding(10, 0, 10, 0),
            ),
            on_click=lambda _event, selected=key: self._handle_click(selected),
        )

    def _handle_click(self, value: str):
        if value == self.value:
            return
        self.set_value(value)
        self.on_change(value)

    def set_value(self, value: str):
        self.value = value

        active_color = self.constants.colors.accent
        active_hover = self.constants.colors.accent_dark
        inactive_color = ft.Colors.TRANSPARENT
        inactive_hover = self.constants.colors.surface_hover

        button_style = lambda selected: ft.ButtonStyle(
            overlay_color=ft.Colors.TRANSPARENT,
            bgcolor={
                ft.ControlState.DEFAULT: active_color if selected else inactive_color,
                ft.ControlState.HOVERED: active_hover if selected else inactive_hover,
            },
            color=self.constants.colors.text,
            shape=_button_shape(self.constants.sizes.control_radius - 2),
            text_style=ft.TextStyle(
                size=self.constants.font_sizes.body,
                weight=ft.FontWeight.W_600,
            ),
            padding=ft.Padding(10, 0, 10, 0),
        )

        self.watch_button.style = button_style(value == "watch")
        self.length_button.style = button_style(value == "length")

        if self.page is not None:
            self.update()


def toolbar_button(
    constants: SimpleNamespace,
    *,
    tooltip: str,
    on_click: Callable,
    icon: str | ft.Icons | None = None,
    image_src: str | None = None,
) -> ft.Container:
    content = (
        ft.Image(src=image_src, width=28, height=28, fit=ft.ImageFit.CONTAIN)
        if image_src
        else None
    )
    button = ft.Container(
        width=constants.sizes.icon_button_size,
        height=constants.sizes.icon_button_size,
        bgcolor=constants.colors.surface,
        border=ft.border.all(
            1, ft.Colors.with_opacity(0.45, constants.colors.panel_edge)
        ),
        border_radius=10,
        tooltip=themed_tooltip(constants, tooltip),
        alignment=ft.alignment.center,
        content=content or ft.Icon(icon, size=20, color=constants.colors.text),
    )
    def _handle_click(event):
        button.bgcolor = constants.colors.surface
        if button.page is not None:
            button.update()
        on_click(event)
        button.bgcolor = constants.colors.surface
        if button.page is not None:
            button.update()

    button.on_click = _handle_click

    def _handle_hover(event):
        button.bgcolor = (
            constants.colors.surface_hover
            if str(event.data).lower() == "true"
            else constants.colors.surface
        )
        if button.page is not None:
            button.update()

    button.on_hover = _handle_hover
    return button


def build_screen_card(
    title: str,
    body: ft.Control,
    constants: SimpleNamespace,
    *,
    leading: ft.Control | None = None,
    trailing: ft.Control | None = None,
) -> ft.Container:
    leading = leading or ft.Container(
        width=constants.sizes.icon_button_size,
        height=constants.sizes.icon_button_size,
    )
    trailing = trailing or ft.Container(
        width=constants.sizes.icon_button_size,
        height=constants.sizes.icon_button_size,
    )

    return ft.Container(
        expand=True,
        bgcolor=constants.colors.panel_bg,
        padding=ft.Padding(
            constants.sizes.internal_padding,
            constants.sizes.internal_padding,
            constants.sizes.internal_padding,
            constants.sizes.internal_padding,
        ),
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        leading,
                        ft.Text(
                            title,
                            expand=True,
                            text_align=ft.TextAlign.CENTER,
                            size=constants.font_sizes.title,
                            color=constants.colors.text,
                            weight=ft.FontWeight.W_700,
                        ),
                        trailing,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(content=body, expand=True),
            ],
            spacing=18,
            expand=True,
        ),
    )
