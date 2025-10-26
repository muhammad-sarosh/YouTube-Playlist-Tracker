from types import SimpleNamespace
import flet as ft

colors = SimpleNamespace(
    primary="#D31130", # Main
    primary_2="#9a0c24", # Main Darker (65%)
    secondary="#1A1A1A", # App BG
    secondary_2="#292929", # Darker secondary BH
    secondary_3="#2D1A1E", # Maroon BG
    white="#EFEFEF"
)

font_sizes = SimpleNamespace(
    large=24,
    medium=20
)

constants = SimpleNamespace(
    colors=colors,
    font_sizes=font_sizes,
    default_width=400,
    default_height=600,
    scroll_bar_thickness=5,
    scroll_bar_radius=10
)