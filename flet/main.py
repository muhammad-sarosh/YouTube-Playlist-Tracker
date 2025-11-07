import flet as ft
import os
import sys
import json
from types import SimpleNamespace

from constants import constants
from components import ResizeDialog, SegmentedControl, CustomHeading, Timestamp, CustomTimeToWatchColumn, CustomNumbersOnlyField, CustomContainer

def open_resize_dialog(page:ft.Page, resize_dialog:ft.AlertDialog, e):
    page.open(resize_dialog)
    page.update()

def load_dimensions(DATA_FILE, constants:SimpleNamespace):
    width = None
    height = None

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                dimensions = json.load(f)
                width = dimensions['width']
                height = dimensions['height']
        except:
            pass
    if not width or not height:
        return constants.default_width, constants.default_height
    else:
        return width, height

def save_dimensions_to_file(DATA_FILE, width, height):
    try:
        with open(DATA_FILE, 'w') as f:
            dimensions = {"width": width, "height": height}
            json.dump(dimensions, f, indent=4)
    except Exception:
        pass

def handle_window_close(page:ft.Page, e):
    if e.data == "close":
        page.window.visible = False
        # Do something
        page.window.destroy()

def main(page: ft.Page):
    # Absolute path needed for data file
    if getattr(sys, 'frozen', False):
        BASE_DIR = os.path.dirname(sys.executable)
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    DATA_DIR = os.path.join(BASE_DIR, "data")
    os.makedirs(DATA_DIR, exist_ok=True)

    DATA_FILE = os.path.join(DATA_DIR, "playlists.json")

    page.title = "YouTube Playlist Calculator"
    page.window.width, page.window.height = load_dimensions(DATA_FILE, constants)
    page.bgcolor = constants.colors.secondary
    page.window.center()
    page.window.prevent_close = True
    page.window.on_event = lambda e: handle_window_close(page=page, e=e)

    page.padding = ft.Padding(16, 12, 16, 12)
    page.fonts = {
        "NunitoSans": "fonts/NunitoSans-VariableFont_YTLC,opsz,wdth,wght.ttf",
        "IBMPlexMono": "fonts/IBMPlexMono-Regular.ttf"
    }
    page.theme = ft.Theme(
        font_family="NunitoSans",
        color_scheme_seed=constants.colors.primary,
        scrollbar_theme=ft.ScrollbarTheme(
            thickness=constants.scroll_bar_thickness,
            radius=constants.scroll_bar_radius,
        )
    )

    # Main setup
    resize_dialog = ResizeDialog(page=page, DATA_FILE=DATA_FILE, constants=constants, save_dimensions_callback=save_dimensions_to_file)
    resize_button = ft.IconButton(icon=ft.Icons.LAPTOP_WINDOWS, icon_color=constants.colors.primary, tooltip="Resize window", on_click=lambda e: open_resize_dialog(page, resize_dialog, e))

    # Top row
    heading = ft.Text(
        "Playlist Calculator",
        color=constants.colors.white,
        weight=ft.FontWeight.W_700,
        size=constants.font_sizes.large,
        text_align=ft.TextAlign.CENTER,
        style=ft.TextStyle(letter_spacing=1.3)
    )

    # edit_playlist_button = ft.IconButton(icon=ft.Icons.ADD, icon_color=constants.colors.primary, tooltip="Edit Playlsit")
    edit_playlist_button = ft.IconButton(
        content=ft.Image(src="icons/edit_playlist_icon.png", width=30, height=30),
        tooltip="Edit Playlist"
    )

    top_row = ft.Row(
        [resize_button, heading, edit_playlist_button],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    top_row_container = ft.Container(
        top_row,
        margin=ft.margin.only(bottom=constants.margins.xl)
    )


    # Mode Switch Control
    switch_mode_container = SegmentedControl(
        activated_button_args={
            'text': 'Watch Duration',
            'default_bgcolor': constants.colors.primary_2,
            'hover_bgcolor': None
        },
        deactivated_button_args={
            'text': 'Playlist Length',
            'default_bgcolor': ft.Colors.TRANSPARENT,
            'hover_bgcolor': constants.colors.secondary_3_2
        },
        constants=constants
    )

    
    # Dropdown
    playlist_link_dropdown = ft.Dropdown(
        hint_text="Playlist Link",
        hint_style=ft.TextStyle(weight=ft.FontWeight.W_500),
        text_style=ft.TextStyle(weight=ft.FontWeight.W_500),
        bgcolor=constants.colors.secondary_3,
        border_color=constants.colors.secondary_3_3,
        border_radius = constants.border_radius,
        hover_color = constants.colors.secondary_3,
        fill_color=constants.colors.secondary_3,
        expand=True,
        enable_filter=True,
        filled=True,
        editable=True,
        options=[
            ft.dropdown.Option(key="https://youtu.be/mth501_link", text="MTH501"),
            ft.dropdown.Option(key="https://youtu.be/mth501_link", text="ENG201"),
            ft.dropdown.Option(key="https://youtu.be/mth501_link", text="CS101"),
            ft.dropdown.Option(key="https://youtu.be/mth501_link", text="MGT301"),
        ]
    )


    # Starting Video | Timestamp
    starting_video_heading = CustomHeading(constants=constants, text="Starting Video | Timestamp")

    starting_video_field = CustomNumbersOnlyField(constants=constants)

    timestamp_video_field = Timestamp(constants=constants)

    watch_duration_mode_column = ft.Column(
        [
            starting_video_heading,
            ft.Row(
                [starting_video_field, timestamp_video_field]
            )
        ]
    )

    
    # Time to watch
    time_to_watch_heading = CustomHeading(constants=constants, text='Time to Watch')

    hours_column = CustomTimeToWatchColumn(constants=constants, heading_text='H')
    minutes_column = CustomTimeToWatchColumn(constants=constants, heading_text='M')
    seconds_column = CustomTimeToWatchColumn(constants=constants, heading_text='S')

    def colon():
        return ft.Container(
                ft.Text(':', weight=ft.FontWeight.W_500),
                margin=ft.margin.only(top=25)
            )

    time_to_watch_row = ft.Row(
        [
            hours_column,
            colon(),
            minutes_column,
            colon(),
            seconds_column
        ]
    )

    time_to_watch_column = ft.Column(
        [
            time_to_watch_heading,
            time_to_watch_row
        ]
    )


    # Calculate Button
    calculate_button = ft.ElevatedButton(
        text='Calculate',
        style=ft.ButtonStyle(
            bgcolor=constants.colors.primary,
            alignment=ft.alignment.center,
            padding=ft.Padding(6, 18, 6, 18),
            shape=ft.RoundedRectangleBorder(radius=constants.border_radius),
            text_style=ft.TextStyle(
                color=constants.colors.white,
                weight=ft.FontWeight.W_700,
                size=constants.font_sizes.medium
            )
        ),
        expand=True
    )

    calculate_button_row = ft.Row(
        [calculate_button]
    )


    # Result
    result_heading = CustomHeading(constants=constants, text='Result')
    result_heading.size = constants.font_sizes.large

    result_content_column = ft.Column(
        [
            ft.Text('Playlist Name: MTH501 Linear Algebra')
        ]
    )

    result_container = CustomContainer(constants=constants)
    result_container.content = result_content_column

    result_container_row = ft.Row(
        [result_container],
        expand=True
    )

    result_column = ft.Column(
        [
            result_heading,
            result_container_row
        ],
        expand=True
    )

    page.add(top_row_container, switch_mode_container, playlist_link_dropdown, watch_duration_mode_column, time_to_watch_column, calculate_button_row, result_column)
    

ft.app(target=main, assets_dir="assets/")