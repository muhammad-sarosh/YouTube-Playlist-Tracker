from types import SimpleNamespace

import flet as ft


colors = SimpleNamespace(
    accent="#F22048",
    accent_dark="#B91535",
    accent_soft="#2E171D",
    accent_glow="#6E1426",
    page_bg="#181818",
    panel_bg="#181818",
    panel_edge="#252525",
    surface="#24161A",
    surface_hover="#321B21",
    surface_muted="#262626",
    border="#824A56",
    text="#F4F0F1",
    text_muted="#C9BDC0",
    text_subtle="#958A8E",
    success="#4FD08A",
    danger="#FF7084",
)

font_sizes = SimpleNamespace(
    title=18,
    section=15,
    body=13,
    small=11,
    number=15,
)

sizes = SimpleNamespace(
    card_width=352,
    card_radius=0,
    control_radius=12,
    input_height=40,
    action_height=42,
    icon_button_size=36,
    page_padding=0,
    internal_padding=16,
    result_group_gap=12,
    result_line_gap=6,
)

window = SimpleNamespace(
    default_width=375,
    default_height=740,
    min_width=340,
    min_height=560,
)

constants = SimpleNamespace(
    app_title="YouTube Playlist Tracker",
    colors=colors,
    font_sizes=font_sizes,
    sizes=sizes,
    window=window,
    playback_speeds=(1.25, 1.5, 1.75, 2.0),
)
