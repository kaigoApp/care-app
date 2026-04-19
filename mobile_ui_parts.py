from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from ui_parts import (
    COLOR_BLACK,
    COLOR_BLUE,
    COLOR_BLUE_SOFT,
    COLOR_GRAY_BORDER,
    COLOR_GRAY_TEXT,
    COLOR_SLATE_SOFT,
    COLOR_TEAL_DARK,
    COLOR_TEAL_SOFT,
    COLOR_WHITE,
    FONT_SIZE_LG,
    FONT_SIZE_MD,
    FONT_SIZE_SM,
    FONT_SIZE_XL,
    FONT_SIZE_XS,
    RADIUS_MD,
    SPACE_MD,
    SPACE_SM,
    _badge,
    _compose_time_value,
    _format_numeric,
    _normalize_display_text,
    _split_time_value,
    _step_for_label,
)

FloatChangeHandler = Callable[[str], None]


def _mobile_panel_shell(title: str, subtitle: str, icon: str, content: list[ft.Control]) -> ft.Container:
    return ft.Container(
        bgcolor=COLOR_WHITE,
        border=ft.Border.all(1, COLOR_GRAY_BORDER),
        border_radius=RADIUS_MD,
        padding=ft.Padding.all(SPACE_MD),
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            width=42,
                            height=42,
                            border_radius=21,
                            bgcolor=COLOR_TEAL_SOFT,
                            alignment=ft.Alignment(0, 0),
                            content=ft.Icon(icon, size=18, color=COLOR_TEAL_DARK),
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(title, size=FONT_SIZE_LG, weight=ft.FontWeight.W_900, color=COLOR_BLACK),
                                ft.Text(subtitle, size=FONT_SIZE_SM, color=COLOR_GRAY_TEXT),
                            ],
                            spacing=4,
                            tight=True,
                        ),
                    ],
                    spacing=SPACE_SM,
                    wrap=True,
                ),
                *content,
            ],
            spacing=SPACE_MD,
            tight=True,
        ),
    )


def _white_value_box(content: ft.Control) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=COLOR_WHITE,
        border=ft.Border.all(1, COLOR_GRAY_BORDER),
        border_radius=14,
        padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
        alignment=ft.Alignment(0, 0),
    )


def _mobile_chip_button(
    label: str,
    selected: bool,
    on_click: Callable[[ft.ControlEvent], None],
    min_width: int = 72,
) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            label,
            size=FONT_SIZE_SM,
            weight=ft.FontWeight.W_800,
            color=COLOR_WHITE if selected else COLOR_TEAL_DARK,
            text_align=ft.TextAlign.CENTER,
        ),
        bgcolor=COLOR_TEAL_DARK if selected else COLOR_WHITE,
        border=ft.Border.all(1, COLOR_TEAL_DARK),
        border_radius=14,
        padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
        alignment=ft.Alignment(0, 0),
        ink=False,
        on_click=on_click,
        width=min_width,
    )


def _mobile_save_button(label: str, on_click: Optional[Callable[[ft.ControlEvent], None]]) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.SAVE_OUTLINED, size=16, color=COLOR_WHITE),
                ft.Text(label, size=FONT_SIZE_SM, weight=ft.FontWeight.W_800, color=COLOR_WHITE),
            ],
            spacing=6,
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor=COLOR_TEAL_DARK,
        border_radius=14,
        padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
        alignment=ft.Alignment(0, 0),
        ink=False,
        on_click=on_click,
    )


def _mobile_safe_time_input_row(label: str, value: str, on_change: Callable[[str], None]) -> ft.Control:
    current_value = _compose_time_value(*_split_time_value(value))
    time_text = ft.Text(current_value, size=FONT_SIZE_LG, weight=ft.FontWeight.W_900, color=COLOR_TEAL_DARK)

    def adjust_minutes(delta: int) -> None:
        hour_text, minute_text = _split_time_value(time_text.value)
        total = (int(hour_text) * 60 + int(minute_text) + delta) % (24 * 60)
        hour = total // 60
        minute = (total % 60) // 5 * 5
        time_text.value = f"{hour}:{minute:02d}"
        on_change(time_text.value)
        time_text.update()

    return ft.Column(
        controls=[
            ft.Text(_normalize_display_text(label), size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT, weight=ft.FontWeight.W_700),
            _white_value_box(time_text),
            ft.Row(
                controls=[
                    _mobile_chip_button("-1\u6642\u9593", False, lambda e: adjust_minutes(-60), min_width=70),
                    _mobile_chip_button("-5\u5206", False, lambda e: adjust_minutes(-5), min_width=62),
                    _mobile_chip_button("+5\u5206", True, lambda e: adjust_minutes(5), min_width=62),
                    _mobile_chip_button("+1\u6642\u9593", False, lambda e: adjust_minutes(60), min_width=70),
                ],
                spacing=SPACE_SM,
                wrap=True,
            ),
        ],
        spacing=6,
        tight=True,
    )


def create_vital_input_field(label: str, value: str, on_change: FloatChangeHandler) -> ft.Container:
    display_label = _normalize_display_text(label)
    step = _step_for_label(display_label)
    value_text = ft.Text(str(value), size=FONT_SIZE_XL, weight=ft.FontWeight.W_900, color=COLOR_BLACK)

    def adjust(delta: float) -> None:
        raw = (value_text.value or "").strip()
        try:
            current = float(raw) if raw else 0.0
        except ValueError:
            current = 0.0
        new_value = max(0.0, current + delta)
        value_text.value = _format_numeric(new_value, step)
        on_change(value_text.value)
        value_text.update()

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(display_label, size=FONT_SIZE_MD, weight=ft.FontWeight.W_700, color=COLOR_BLACK),
                _white_value_box(value_text),
                ft.Row(
                    controls=[
                        _mobile_chip_button("-1" if step == 1.0 else "-0.1", False, lambda e: adjust(-step), min_width=74),
                        _mobile_chip_button("+1" if step == 1.0 else "+0.1", True, lambda e: adjust(step), min_width=74),
                    ],
                    spacing=SPACE_SM,
                    wrap=True,
                ),
            ],
            spacing=8,
            tight=True,
        ),
        bgcolor=COLOR_WHITE,
        border=ft.Border.all(1, COLOR_GRAY_BORDER),
        border_radius=14,
        padding=ft.Padding.all(SPACE_MD),
    )


def create_vital_panel(
    temperature_control: ft.Control,
    systolic_control: ft.Control,
    diastolic_control: ft.Control,
    spo2_control: ft.Control,
    record_time: str,
    on_record_time_change: Callable[[str], None],
    on_save: Optional[Callable[[ft.ControlEvent], None]] = None,
) -> ft.Container:
    content: list[ft.Control] = [
        _mobile_safe_time_input_row("\u6e2c\u5b9a\u6642\u523b", record_time, on_record_time_change),
        temperature_control,
        systolic_control,
        diastolic_control,
        spo2_control,
    ]
    if on_save is not None:
        content.append(ft.Row(controls=[_mobile_save_button("\u30d0\u30a4\u30bf\u30eb\u3092\u4fdd\u5b58", on_save)], alignment=ft.MainAxisAlignment.END))

    container = _mobile_panel_shell(
        "\u30d0\u30a4\u30bf\u30eb\u5165\u529b",
        "\u4f53\u6e29\u30fb\u8840\u5727\u30fbSpO2\u3092\u30dc\u30bf\u30f3\u3067\u8abf\u6574\u3057\u3066\u8a18\u9332",
        ft.Icons.MONITOR_HEART,
        content,
    )
    container.data = {"record_time": record_time}
    return container


def create_support_progress_panel(
    selected_category: str,
    note_text: str,
    categories: list[str],
    record_time: str,
    recorded_at_text: str,
    staff_name: str,
    on_category_select: Callable[[str], None],
    on_text_change: Callable[[str], None],
    on_record_time_change: Callable[[str], None],
    on_save: Optional[Callable[[ft.ControlEvent], None]] = None,
    is_editing: bool = False,
    on_cancel: Optional[Callable[[ft.ControlEvent], None]] = None,
) -> ft.Container:
    active_category = selected_category or (categories[0] if categories else "")
    quick_notes = [
        "\u7279\u5909\u306a\u304f\u904e\u3054\u3055\u308c\u3066\u3044\u307e\u3059\u3002",
        "\u7a4f\u3084\u304b\u306b\u904e\u3054\u3055\u308c\u3066\u3044\u307e\u3059\u3002",
        "\u58f0\u304b\u3051\u306b\u5fdc\u3058\u3089\u308c\u3066\u3044\u307e\u3059\u3002",
        "\u8868\u60c5\u3084\u767a\u8a9e\u306b\u5927\u304d\u306a\u5909\u5316\u306f\u3042\u308a\u307e\u305b\u3093\u3002",
        "\u898b\u5b88\u308a\u3092\u7d99\u7d9a\u3057\u3066\u3044\u307e\u3059\u3002",
    ]
    selected_note = note_text or quick_notes[0]
    note_preview = ft.Text(selected_note, size=FONT_SIZE_MD, color=COLOR_BLACK)

    def choose_note(text: str) -> None:
        note_preview.value = text
        on_text_change(text)
        note_preview.update()

    def save_selected_note(e: ft.ControlEvent) -> None:
        on_text_change(note_preview.value or quick_notes[0])
        if on_save is not None:
            on_save(e)

    category_buttons = ft.Row(
        controls=[
            _mobile_chip_button(label, active_category == label, lambda e, item=label: on_category_select(item), min_width=72)
            for label in categories
        ],
        spacing=SPACE_SM,
        wrap=True,
    )
    note_buttons = ft.Column(
        controls=[_mobile_chip_button(text, selected_note == text, lambda e, item=text: choose_note(item), min_width=220) for text in quick_notes],
        spacing=SPACE_SM,
        tight=True,
    )
    meta_row = ft.Row(
        controls=[
            _badge(active_category or "\u672a\u9078\u629e", COLOR_TEAL_SOFT, COLOR_TEAL_DARK, ft.Icons.LABEL),
            _badge(recorded_at_text, COLOR_BLUE_SOFT, COLOR_BLUE, ft.Icons.SCHEDULE),
            _badge(staff_name or "\u62c5\u5f53\u8005\u672a\u8a2d\u5b9a", COLOR_SLATE_SOFT, COLOR_GRAY_TEXT, ft.Icons.PERSON),
        ],
        spacing=SPACE_SM,
        wrap=True,
    )

    content: list[ft.Control] = [
        ft.Text("\u533a\u5206", size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT, weight=ft.FontWeight.W_700),
        category_buttons,
        _mobile_safe_time_input_row("\u8a18\u9332\u6642\u523b", record_time, on_record_time_change),
        meta_row,
        ft.Text("\u652f\u63f4\u5185\u5bb9", size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT, weight=ft.FontWeight.W_700),
        _white_value_box(note_preview),
        note_buttons,
    ]
    if is_editing:
        content.insert(
            0,
            ft.Container(
                bgcolor="#EFF6FF",
                border=ft.Border.all(1, "#BFDBFE"),
                border_radius=12,
                padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
                content=ft.Text(
                    "\u8a18\u9332\u3092\u7de8\u96c6\u4e2d\u3067\u3059\u3002\u5185\u5bb9\u3092\u9078\u3073\u76f4\u3057\u3066\u66f4\u65b0\u3057\u3066\u304f\u3060\u3055\u3044\u3002",
                    size=FONT_SIZE_SM,
                    color=COLOR_BLUE,
                    weight=ft.FontWeight.W_700,
                ),
            ),
        )
    if on_save is not None:
        actions: list[ft.Control] = []
        if is_editing and on_cancel is not None:
            actions.append(_mobile_chip_button("\u30ad\u30e3\u30f3\u30bb\u30eb", False, on_cancel, min_width=96))
        actions.append(_mobile_save_button("\u8a18\u9332\u3092\u66f4\u65b0" if is_editing else "\u8a18\u9332\u3092\u4fdd\u5b58", save_selected_note))
        content.append(ft.Row(controls=actions, alignment=ft.MainAxisAlignment.END, spacing=SPACE_SM, wrap=True))

    container = _mobile_panel_shell(
        "\u652f\u63f4\u7d4c\u904e\u5165\u529b",
        "\u30b9\u30de\u30db\u3067\u306f\u5b9a\u578b\u6587\u3092\u9078\u3093\u3067\u5b89\u5168\u306b\u4fdd\u5b58\u3057\u307e\u3059\u3002",
        ft.Icons.EDIT_NOTE,
        content,
    )
    container.data = {"selected_category": active_category, "record_time": record_time, "is_editing": is_editing}
    return container
