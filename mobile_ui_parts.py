from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from ui_parts import (
    COLOR_BLACK,
    COLOR_BLUE,
    COLOR_BLUE_SOFT,
    COLOR_GRAY_BG,
    COLOR_GRAY_BORDER,
    COLOR_GRAY_TEXT,
    COLOR_SLATE_SOFT,
    COLOR_TEAL_DARK,
    COLOR_TEAL_LIGHT,
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
    _build_input_panel_shell,
    _compose_time_value,
    _format_numeric,
    _normalize_display_text,
    _panel_save_button,
    _split_time_value,
    _step_for_label,
    _toggle_button,
)

FloatChangeHandler = Callable[[str], None]


def _display_box(content: ft.Control, bg: str = COLOR_GRAY_BG) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=bg,
        border=ft.Border.all(1, COLOR_GRAY_BORDER),
        border_radius=14,
        padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
        alignment=ft.Alignment(0, 0),
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
            _display_box(time_text, COLOR_TEAL_SOFT),
            ft.Row(
                controls=[
                    _toggle_button("-1時間", False, lambda e: adjust_minutes(-60), compact=True),
                    _toggle_button("-5分", False, lambda e: adjust_minutes(-5), compact=True),
                    _toggle_button("+5分", True, lambda e: adjust_minutes(5), compact=True),
                    _toggle_button("+1時間", False, lambda e: adjust_minutes(60), compact=True),
                ],
                spacing=SPACE_SM,
                wrap=True,
            ),
        ],
        spacing=6,
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
                _display_box(value_text),
                ft.Row(
                    controls=[
                        _toggle_button("-1" if step == 1.0 else "-0.1", False, lambda e: adjust(-step), compact=True),
                        _toggle_button("+1" if step == 1.0 else "+0.1", True, lambda e: adjust(step), compact=True),
                    ],
                    spacing=SPACE_SM,
                    wrap=True,
                ),
            ],
            spacing=8,
        ),
        bgcolor=COLOR_WHITE,
        border=ft.Border.all(1, COLOR_GRAY_BORDER),
        border_radius=RADIUS_MD,
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
        _mobile_safe_time_input_row("測定時刻", record_time, on_record_time_change),
        temperature_control,
        systolic_control,
        diastolic_control,
        spo2_control,
    ]
    if on_save is not None:
        content.append(ft.Row(controls=[_panel_save_button("バイタルを保存", on_save)], alignment=ft.MainAxisAlignment.END))
    container = _build_input_panel_shell("バイタル入力", "体温・血圧・SpO2をボタンで調整して記録", ft.Icons.MONITOR_HEART, content)
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
        "特変なく過ごされています。",
        "穏やかに過ごされています。",
        "声かけに応じられています。",
        "表情や発語に大きな変化はありません。",
        "見守りを継続しています。",
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
        controls=[_toggle_button(label, active_category == label, lambda e, item=label: on_category_select(item), compact=True) for label in categories],
        spacing=SPACE_SM,
        wrap=True,
    )
    note_buttons = ft.Column(
        controls=[_toggle_button(text, selected_note == text, lambda e, item=text: choose_note(item), compact=True) for text in quick_notes],
        spacing=SPACE_SM,
    )
    meta_row = ft.Row(
        controls=[
            _badge(active_category or "未選択", COLOR_TEAL_SOFT, COLOR_TEAL_DARK, ft.Icons.LABEL),
            _badge(recorded_at_text, COLOR_BLUE_SOFT, COLOR_BLUE, ft.Icons.SCHEDULE),
            _badge(staff_name or "担当者未設定", COLOR_SLATE_SOFT, COLOR_GRAY_TEXT, ft.Icons.PERSON),
        ],
        spacing=SPACE_SM,
        wrap=True,
    )
    content: list[ft.Control] = [
        ft.Text("区分", size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT, weight=ft.FontWeight.W_700),
        category_buttons,
        _mobile_safe_time_input_row("記録時刻", record_time, on_record_time_change),
        meta_row,
        ft.Text("支援内容", size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT, weight=ft.FontWeight.W_700),
        ft.Container(content=note_preview, bgcolor=COLOR_GRAY_BG, border=ft.Border.all(1, COLOR_GRAY_BORDER), border_radius=14, padding=ft.Padding.all(SPACE_MD)),
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
                content=ft.Text("記録を編集中です。内容を選び直して更新してください。", size=FONT_SIZE_SM, color=COLOR_BLUE, weight=ft.FontWeight.W_700),
            ),
        )
    if on_save is not None:
        actions: list[ft.Control] = []
        if is_editing and on_cancel is not None:
            actions.append(ft.TextButton("キャンセル", on_click=on_cancel, style=ft.ButtonStyle(color=COLOR_GRAY_TEXT)))
        actions.append(_panel_save_button("記録を更新" if is_editing else "記録を保存", save_selected_note))
        content.append(ft.Row(controls=actions, alignment=ft.MainAxisAlignment.END, spacing=SPACE_SM, wrap=True))
    container = _build_input_panel_shell("支援経過入力", "スマホ版は定型文を選んで保存します", ft.Icons.EDIT_NOTE, content)
    container.data = {"selected_category": active_category, "record_time": record_time, "is_editing": is_editing}
    return container
