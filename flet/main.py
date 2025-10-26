import flet as ft
import os
import sys
import json
from types import SimpleNamespace

from constants import constants
from components import ResizeDialog

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
    page.theme = ft.Theme(
        scrollbar_theme=ft.ScrollbarTheme(
            thickness=constants.scroll_bar_thickness,
            radius=constants.scroll_bar_radius,
        )
    )

    # Main setup
    resize_dialog = ResizeDialog(page=page, DATA_FILE=DATA_FILE, constants=constants, save_dimensions_callback=save_dimensions_to_file)
    resize_button = ft.IconButton(icon=ft.Icons.LAPTOP_WINDOWS, icon_color=constants.colors.primary, tooltip="Resize window", on_click=lambda e: open_resize_dialog(page, resize_dialog, e))

    page.add(resize_button)
    

ft.app(target=main)