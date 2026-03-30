from __future__ import annotations

from pathlib import Path

import flet as ft

from app_playlists import PlaylistManagementMixin
from app_results import ResultHandlingMixin
from app_ui import AppUIBuildMixin
from constants import constants
from services import PlaylistService, SavedPlaylistsStore


class PlaylistTrackerApp(
    AppUIBuildMixin,
    PlaylistManagementMixin,
    ResultHandlingMixin,
):
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


def main(page: ft.Page):
    PlaylistTrackerApp(page)


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
