import flet as ft
from types import SimpleNamespace
from typing import Callable

class ConfirmButton(ft.ElevatedButton):
    def __init__(self, text:str, callback:Callable, constants:SimpleNamespace, width:int=95, expand:bool=False):
        super().__init__()
        self.text = text
        self.color = "white"
        self.width = width
        self.expand = expand
        self.bgcolor = {
            ft.ControlState.DEFAULT: constants.colors.primary_2,
            ft.ControlState.HOVERED: constants.colors.primary_2
        }
        self.style = ft.ButtonStyle(
            alignment=ft.alignment.center,
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding(6, 14, 6, 16)
        )
        self.on_click = callback


class CancelButton(ft.OutlinedButton):
    def __init__(self, text:str, callback:Callable, constants:SimpleNamespace, width:int=95, expand:bool=False):
        super().__init__()
        self.content = ft.Text(text, color=constants.colors.primary)
        self.width = width
        self.expand = expand
        self.style = ft.ButtonStyle(
            alignment=ft.alignment.center,
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding(6, 14, 6, 16),
            side=ft.BorderSide(width=1.5, color=constants.colors.primary)
        )
        self.on_click = callback

class ResizeDialog(ft.AlertDialog):
    def __init__(self, page:ft.Page, DATA_FILE:str, constants:SimpleNamespace, save_dimensions_callback:Callable):
        super().__init__()
        self.page = page
        self.DATA_FILE = DATA_FILE
        self.constants = constants
        self.save_dimensions_callback = save_dimensions_callback

        self.width_field = ft.TextField(
            hint_text="Width",
            autofocus=True,
            bgcolor=self.constants.colors.secondary_3,
            cursor_color=self.constants.colors.white,
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
            border=ft.InputBorder.OUTLINE,
            border_radius=10,
            border_color="transparent",
            border_width=1.3
        )
        self.height_field = ft.TextField(
            hint_text="Height",
            autofocus=True,
            bgcolor=self.constants.colors.secondary_3,
            cursor_color=self.constants.colors.white,
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
            border=ft.InputBorder.OUTLINE,
            border_radius=10,
            border_color="transparent",
            border_width=1.3
        )
        resize_dialog_fields = ft.Row([ft.Container(self.width_field, expand=True), ft.Container(self.height_field, expand=True)])
        use_current_button = ft.Container(
            content=ft.TextButton(
                "Use current",
                style=ft.ButtonStyle(color="#aaaaaa", text_style=ft.TextStyle(size=12), padding=ft.Padding(2, 0, 2, 0), overlay_color="transparent"),
                on_click=self.get_current_size,
            ),
            height=22
        )
        reset_to_default_button = ft.Container(
            content=ft.TextButton(
                "Reset to default",
                style=ft.ButtonStyle(color="#aaaaaa", text_style=ft.TextStyle(size=12), padding=ft.Padding(2, 0, 2, 0), overlay_color="transparent"),
                on_click=self.get_default_size,
            ),
            height=22
        )
        resize_dialog_column = ft.Column(
            [resize_dialog_fields, use_current_button, reset_to_default_button],
            spacing=0,
            tight=True
        )

        # Alert Dialog
        self.title = ft.Text("Resize Window", weight=ft.FontWeight.W_500)
        self.bgcolor = self.constants.colors.secondary
        self.content = resize_dialog_column
        self.actions = [
            ft.Row(
                [
                    CancelButton(text="Cancel", callback=self.close_resize_dialog, constants=self.constants, expand=True, width=None),
                    ConfirmButton(text="Save", callback=self.save_dimensions, constants=self.constants, expand=True, width=None)
                ],
                spacing=10
            )
        ]
    
    def close_resize_dialog(self, e=None):
        self.page.close(self)
        self.width_field.value = ""
        self.width_field.error_text = None
        self.height_field.value = ""
        self.height_field.error_text = None
        self.page.update()

    def get_current_size(self, e):
        self.width_field.value = int(self.page.window.width)
        self.height_field.value = int(self.page.window.height)
        self.page.update()

    def get_default_size(self, e):
        self.width_field.value = self.constants.default_width
        self.height_field.value = self.constants.default_height
        self.page.update()

    def save_dimensions(self, e):
        error = False
        if not str(self.width_field.value).strip():
            self.width_field.error_text = " "
            error = True
        if not str(self.height_field.value).strip():
            self.height_field.error_text = " "
            error = True
        if error:
            self.page.update()
            return

        self.save_dimensions_callback(self.DATA_FILE, self.width_field.value, self.height_field.value)

        self.page.window.width = self.width_field.value
        self.page.window.height = self.height_field.value
        self.page.window.center()
        self.close_resize_dialog()

class SegmentedControlButton(ft.ElevatedButton):
    def __init__(self, text:str, default_bgcolor, hover_bgcolor, constants:SimpleNamespace):
        super().__init__()
        self.text = text
        self.expand = True
        self.style=ft.ButtonStyle(
            color=constants.colors.white,
            bgcolor={
                ft.ControlState.DEFAULT: default_bgcolor,
                ft.ControlState.HOVERED: hover_bgcolor
            },
            padding=13,
            shape=ft.RoundedRectangleBorder(radius=constants.border_radius),
            shadow_color=ft.Colors.TRANSPARENT,
            text_style=ft.TextStyle(
                size=constants.font_sizes.medium,
                font_family="NunitoSans",
                weight=ft.FontWeight.W_600
            )
        )

class SegmentedControl(ft.Container):
    def __init__(self, activated_button_args:dict, deactivated_button_args:dict, constants:SimpleNamespace):
        super().__init__()
        activated_button = SegmentedControlButton(
            text=activated_button_args['text'],
            default_bgcolor=activated_button_args['default_bgcolor'],
            hover_bgcolor=activated_button_args['hover_bgcolor'],
            constants=constants
        )
        deactivated_button = SegmentedControlButton(
            text=deactivated_button_args['text'],
            default_bgcolor=deactivated_button_args['default_bgcolor'],
            hover_bgcolor=deactivated_button_args['hover_bgcolor'],
            constants=constants
        )
        row = ft.Row([activated_button, deactivated_button], spacing=3)

        self.content = row
        self.padding = 5
        self.bgcolor=constants.colors.secondary_3
        self.border_radius=constants.border_radius
        self.margin = ft.margin.only(bottom=constants.margins.xl)

class CustomTextField(ft.TextField):
    def __init__(self, hint_text: str, constants:SimpleNamespace):
        super().__init__()
        self.hint_text = hint_text
        self.expand = True
        self.border_radius = constants.border_radius
        self.bgcolor = constants.colors.secondary_3
        self.border_color = constants.colors.secondary_3_3
        self.cursor_color = constants.colors.primary
        self.hover_color = constants.colors.secondary_3
        