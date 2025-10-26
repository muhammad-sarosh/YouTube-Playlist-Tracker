import flet as ft

class ConfirmButton(ft.ElevatedButton):
    def __init__(self, text, callback, constants, width=95, expand=False):
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
    def __init__(self, text, callback, constants, width=95, expand=False):
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
    def __init__(self, page, DATA_FILE, constants, save_dimensions_callback):
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