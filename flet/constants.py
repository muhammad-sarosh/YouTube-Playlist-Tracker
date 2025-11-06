from types import SimpleNamespace
import flet as ft

colors = SimpleNamespace(
    primary="#D31130", # Main
    primary_2="#9a0c24", # Main Darker (65%)
    secondary="#1A1A1A", # App BG
    secondary_2="#292929", # Darker secondary BH
    secondary_3="#2D1A1E", # Maroon BG
    secondary_3_2="#3a161e", # Brighter Maroon BG (for hover)
    secondary_3_3="#804A56", # Maroon outline
    white="#EFEFEF"
)

font_sizes = SimpleNamespace(
    large=20,
    medium=16
)

margins = SimpleNamespace(
    xl=10,
    large=8,
    medium=8,
    medium_small=7,
    small=6,
    xs=5
)

constants = SimpleNamespace(
    colors=colors,
    font_sizes=font_sizes,
    margins=margins,
    default_width=375,
    default_height=645,
    scroll_bar_thickness=5,
    scroll_bar_radius=10,
    border_radius=8
)