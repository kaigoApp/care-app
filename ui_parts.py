
from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional, Union

import flet as ft

COLOR_TEAL = "#1A7F72"
COLOR_TEAL_DARK = "#135D54"
COLOR_TEAL_LIGHT = "#CFE9E3"
COLOR_TEAL_SOFT = "#EEF7F5"
COLOR_WHITE = "#FFFFFF"
COLOR_BLACK = "#18322F"
COLOR_GRAY_TEXT = "#6C7F7C"
COLOR_GRAY_BORDER = "#DCE8E4"
COLOR_GRAY_BG = "#F6FAF9"
COLOR_ALERT_RED = "#B84747"
COLOR_ALERT_SOFT = "#FFF1F1"
COLOR_BLUE = "#2E67C7"
COLOR_BLUE_SOFT = "#EEF4FF"
COLOR_ORANGE = "#C8892B"
COLOR_ORANGE_SOFT = "#FFF7EA"
COLOR_GREEN = "#2B8F65"
COLOR_GREEN_SOFT = "#ECF8F1"
COLOR_SLATE_SOFT = "#F3F7F6"
COLOR_VIOLET_SOFT = "#F4F1FF"

SPACE_XS = 4
SPACE_SM = 10
SPACE_MD = 14
SPACE_LG = 20
SPACE_XL = 28

FONT_SIZE_XS = 11
FONT_SIZE_SM = 13
FONT_SIZE_MD = 16
FONT_SIZE_LG = 20
FONT_SIZE_XL = 24

RADIUS_SM = 10
RADIUS_MD = 18
RADIUS_LG = 26

NORMAL_TEXT_COLOR = COLOR_BLACK
DANGER_TEXT_COLOR = COLOR_ALERT_RED

FloatChangeHandler = Callable[[str], None]
BoolChangeHandler = Callable[[bool], None]


def _safe_text(value: object, default: str = "-") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_display_text(value: str) -> str:
    mapping = {
        "菴捺ｸｩ": "体温",
        "譛鬮倩｡蝨ｧ": "最高血圧",
        "譛菴手｡蝨ｧ": "最低血圧",
        "險倬鹸譎ょ綾": "記録時刻",
        "貂ｬ螳壽凾蛻ｻ": "測定時刻",
        "蟾｡隕匁凾蛻ｻ": "巡視時刻",
    }
    return mapping.get(value, value)


def _format_dt_short(value: object) -> str:
    if not value:
        return "未記録"
    text = str(value)
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ):
        try:
            return datetime.strptime(text, fmt).strftime("%m/%d %H:%M")
        except ValueError:
            continue
    return text


def _value_is_high_temperature(value: Optional[float]) -> bool:
    return value is not None and value >= 37.5


def _value_is_high_bp(systolic: Optional[int], diastolic: Optional[int]) -> bool:
    return (systolic is not None and systolic >= 140) or (diastolic is not None and diastolic >= 90)


def _value_is_low_spo2(value: Optional[int]) -> bool:
    return value is not None and value < 95


def _metric_color(is_alert: bool, accent: Optional[str] = None) -> str:
    return DANGER_TEXT_COLOR if is_alert else (accent or NORMAL_TEXT_COLOR)


def _step_for_label(label: str) -> float:
    return 0.1 if "体温" in label else 1.0


def _format_numeric(value: float, step: float) -> str:
    if step == 0.1:
        return f"{value:.1f}"
    return str(int(round(value)))


def _panel_shadow() -> ft.BoxShadow:
    return ft.BoxShadow(
        spread_radius=0,
        blur_radius=26,
        color="#18322F14",
        offset=ft.Offset(0, 10),
    )


def _toggle_button(
    label: str,
    selected: bool,
    on_click: Callable[[ft.ControlEvent], None],
    expand: bool = False,
    bgcolor_selected: str = COLOR_TEAL,
    text_selected: str = COLOR_WHITE,
    text_unselected: str = COLOR_TEAL,
    border_color: Optional[str] = None,
    compact: bool = False,
) -> ft.Control:
    height = 42 if compact else 48
    return ft.ElevatedButton(
        content=ft.Text(label, size=FONT_SIZE_SM if compact else FONT_SIZE_MD, weight=ft.FontWeight.W_700),
        on_click=on_click,
        height=height,
        expand=expand,
        style=ft.ButtonStyle(
            bgcolor=bgcolor_selected if selected else "#FCFEFD",
            color=text_selected if selected else text_unselected,
            side=ft.BorderSide(1, border_color or bgcolor_selected),
            elevation=0,
            shadow_color="#00000000",
            shape=ft.RoundedRectangleBorder(radius=18),
            padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_SM),
        ),
    )


def _build_input_panel_shell(title: str, subtitle: str, icon: str, content: list[ft.Control]) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Icon(icon, size=18, color=COLOR_TEAL),
                            width=42,
                            height=42,
                            bgcolor="#F3FBF8",
                            border=ft.Border.all(1, COLOR_TEAL_LIGHT),
                            border_radius=21,
                            alignment=ft.Alignment(0, 0),
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(title, size=FONT_SIZE_LG, weight=ft.FontWeight.W_800, color=COLOR_BLACK),
                                ft.Text(subtitle, size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    spacing=SPACE_SM,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    wrap=True,
                ),
                *content,
            ],
            spacing=SPACE_SM,
        ),
        bgcolor="#FFFEFC",
        border=ft.Border.all(1, COLOR_GRAY_BORDER),
        border_radius=RADIUS_LG,
        padding=ft.Padding.all(SPACE_LG),
        shadow=_panel_shadow(),
    )


def _badge(text: str, bg: str, color: str, icon: Optional[str] = None) -> ft.Container:
    row_controls: list[ft.Control] = []
    if icon:
        row_controls.append(ft.Icon(icon, size=12, color=color))
    row_controls.append(ft.Text(text, size=FONT_SIZE_XS, color=color, weight=ft.FontWeight.W_700))
    return ft.Container(
        content=ft.Row(controls=row_controls, spacing=4, tight=True),
        bgcolor=bg,
        border_radius=999,
        padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=6),
    )


def _avatar_text(name: str) -> str:
    text = (name or "?").strip()
    return text[:1] if text else "?"


def _panel_save_button(label: str, on_click: Optional[Callable[[ft.ControlEvent], None]]) -> ft.Control:
    return ft.ElevatedButton(
        content=ft.Row(
            controls=[ft.Icon(ft.Icons.SAVE_OUTLINED, size=16), ft.Text(label, size=FONT_SIZE_SM, weight=ft.FontWeight.W_700)],
            spacing=6,
            tight=True,
        ),
        on_click=on_click,
        height=46,
        style=ft.ButtonStyle(
            bgcolor=COLOR_TEAL,
            color=COLOR_WHITE,
            elevation=0,
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_SM),
        ),
    )


def _meta_badge(text: str, bg: str = COLOR_SLATE_SOFT, color: str = COLOR_GRAY_TEXT) -> ft.Container:
    return ft.Container(
        content=ft.Text(text, size=FONT_SIZE_XS, color=color, weight=ft.FontWeight.W_700),
        bgcolor=bg,
        border_radius=999,
        padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=7),
        border=ft.Border.all(1, "#E7EFEC"),
    )


def _split_time_value(value: str) -> tuple[str, str]:
    text = (value or "").strip().replace("：", ":")
    if ":" in text:
        hour_text, minute_text = text.split(":", 1)
    else:
        hour_text, minute_text = text, "0"

    try:
        hour = int(hour_text)
    except ValueError:
        hour = 0
    try:
        minute = int(minute_text)
    except ValueError:
        minute = 0

    hour = max(0, min(23, hour))
    minute = max(0, min(55, (minute // 5) * 5))
    return str(hour), str(minute)


def _compose_time_value(hour_text: str, minute_text: str) -> str:
    hour, minute = _split_time_value(f"{hour_text}:{minute_text}")
    return f"{int(hour)}:{int(minute):02d}"


def _legacy_time_input_row(
    label: str,
    value: str,
    on_change: Callable[[str], None],
) -> ft.Control:
    hour_value, minute_value = _split_time_value(value)

    hour_dropdown = ft.Dropdown(
        label=f"{label}（時）",
        expand=True,
        height=56,
        value=hour_value,
        border_color=COLOR_GRAY_BORDER,
        content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_SM),
        options=[ft.DropdownOption(key=str(hour), text=str(hour)) for hour in range(0, 24)],
    )
    minute_dropdown = ft.Dropdown(
        label="分",
        expand=True,
        height=56,
        value=minute_value,
        border_color=COLOR_GRAY_BORDER,
        content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_SM),
        options=[ft.DropdownOption(key=str(minute), text=str(minute)) for minute in range(0, 60, 5)],
    )

    def handle_time_change(e: ft.ControlEvent) -> None:
        current_hour = hour_dropdown.value or hour_value
        current_minute = minute_dropdown.value or minute_value
        on_change(_compose_time_value(current_hour, current_minute))

    hour_dropdown.on_change = handle_time_change
    minute_dropdown.on_change = handle_time_change

    return ft.Column(
        controls=[
            ft.Row(
                controls=[hour_dropdown, minute_dropdown],
                spacing=SPACE_SM,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text("時:1〜24 / 分:0〜55（5分刻み）", size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT, weight=ft.FontWeight.W_700),
        ],
        spacing=6,
    )


def _mobile_safe_time_input_row(
    label: str,
    value: str,
    on_change: Callable[[str], None],
) -> ft.Control:
    hour_value, minute_value = _split_time_value(value)

    hour_field = ft.TextField(
        label=f"{label} (時)",
        value=hour_value,
        adaptive=True,
        width=124,
        height=56,
        filled=False,
        bgcolor=COLOR_WHITE,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color=COLOR_GRAY_BORDER,
        content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_SM),
    )
    minute_field = ft.TextField(
        label="分",
        value=minute_value,
        adaptive=True,
        width=124,
        height=56,
        filled=False,
        bgcolor=COLOR_WHITE,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color=COLOR_GRAY_BORDER,
        content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_SM),
    )

    def handle_time_change(_e: ft.ControlEvent) -> None:
        composed = _compose_time_value(hour_field.value or "0", minute_field.value or "0")
        normalized_hour, normalized_minute = _split_time_value(composed)
        hour_field.value = normalized_hour
        minute_field.value = normalized_minute
        hour_field.update()
        minute_field.update()
        on_change(composed)

    hour_field.on_blur = handle_time_change
    minute_field.on_blur = handle_time_change
    hour_field.on_submit = handle_time_change
    minute_field.on_submit = handle_time_change

    return ft.Column(
        controls=[
            ft.Row(
                controls=[hour_field, minute_field],
                spacing=SPACE_SM,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text("時: 0〜23 / 分: 0〜55（5分刻み）", size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT, weight=ft.FontWeight.W_700),
        ],
        spacing=6,
    )


_time_input_row = _mobile_safe_time_input_row


_time_input_row = _mobile_safe_time_input_row


def create_shared_header(
    title: str,
    subtitle: str,
    staff_text: str = "",
    back_label: Optional[str] = None,
    on_back: Optional[Callable[[ft.ControlEvent], None]] = None,
    meta_items: Optional[list[str]] = None,
    actions: Optional[list[ft.Control]] = None,
) -> ft.Container:
    meta_controls = [_meta_badge(item, COLOR_TEAL_SOFT, COLOR_TEAL_DARK) for item in (meta_items or []) if (item or "").strip()]
    action_controls: list[ft.Control] = []
    if back_label and on_back:
        action_controls.append(create_resident_button(back_label, False, on_click=on_back))
    action_controls.extend(actions or [])

    controls: list[ft.Control] = [
        ft.Text(title, size=FONT_SIZE_XL + 2, weight=ft.FontWeight.W_900, color=COLOR_BLACK),
        ft.Text(subtitle, size=FONT_SIZE_SM, color=COLOR_GRAY_TEXT),
    ]
    if staff_text:
        controls.append(ft.Text(staff_text, size=FONT_SIZE_MD, color=COLOR_TEAL, weight=ft.FontWeight.W_700))
    if meta_controls:
        controls.append(ft.Row(controls=meta_controls, spacing=SPACE_SM, wrap=True))
    if action_controls:
        controls.append(ft.Row(controls=action_controls, spacing=SPACE_SM, wrap=True))

    return ft.Container(
        content=ft.Column(controls=controls, spacing=SPACE_MD),
        bgcolor="#FFFEFC",
        border_radius=RADIUS_LG,
        padding=ft.Padding.all(SPACE_XL),
        border=ft.Border.all(1, COLOR_GRAY_BORDER),
        shadow=_panel_shadow(),
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=["#FFFEFC", "#F8FCFB"],
        ),
    )


def create_resident_button(name: str, is_selected: bool, on_click: Optional[Callable[[ft.ControlEvent], None]] = None) -> ft.Control:
    return ft.ElevatedButton(
        content=ft.Text(name, size=FONT_SIZE_MD, weight=ft.FontWeight.W_700),
        on_click=on_click,
        height=52,
        style=ft.ButtonStyle(
            bgcolor=COLOR_TEAL if is_selected else "#FCFEFD",
            color=COLOR_WHITE if is_selected else COLOR_TEAL,
            side=ft.BorderSide(1, COLOR_TEAL),
            elevation=0,
            shadow_color="#00000000",
            shape=ft.RoundedRectangleBorder(radius=18),
            padding=ft.Padding.symmetric(horizontal=SPACE_XL, vertical=SPACE_MD),
        ),
    )


def create_app_brand_hero(
    title: str,
    subtitle: str,
    description: str,
    badges: Optional[list[str]] = None,
) -> ft.Container:
    badge_controls = [_meta_badge(item, COLOR_VIOLET_SOFT if index == 0 else COLOR_TEAL_SOFT, COLOR_TEAL_DARK) for index, item in enumerate(badges or [])]

    mark = ft.Container(
        width=110,
        height=110,
        border_radius=36,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=["#1A7F72", "#2DAA98", "#8C7CF7"],
        ),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=30,
            color="#1A7F7233",
            offset=ft.Offset(0, 14),
        ),
        content=ft.Stack(
            controls=[
                ft.Container(
                    width=44,
                    height=44,
                    left=14,
                    top=16,
                    border_radius=18,
                    bgcolor="#FFFFFF22",
                ),
                ft.Container(
                    width=30,
                    height=30,
                    right=16,
                    top=20,
                    border_radius=15,
                    bgcolor="#FFFFFF18",
                ),
                ft.Container(
                    width=70,
                    height=70,
                    left=20,
                    top=22,
                    border_radius=24,
                    bgcolor="#FFFFFF18",
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, size=34, color=COLOR_WHITE),
                ),
                ft.Container(
                    right=14,
                    bottom=14,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                    border_radius=999,
                    bgcolor="#FFFFFF26",
                    content=ft.Text("AI", color=COLOR_WHITE, size=FONT_SIZE_SM, weight=ft.FontWeight.W_900),
                ),
            ]
        ),
    )

    return ft.Container(
        content=ft.ResponsiveRow(
            controls=[
                ft.Container(col={"xs": 12, "md": 4}, content=mark, alignment=ft.Alignment(-1, 0)),
                ft.Container(
                    col={"xs": 12, "md": 8},
                    content=ft.Column(
                        controls=[
                            _badge("Care AI Note", COLOR_BLUE_SOFT, COLOR_BLUE, ft.Icons.BOLT_ROUNDED),
                            ft.Text(title, size=32, weight=ft.FontWeight.W_900, color=COLOR_BLACK),
                            ft.Text(subtitle, size=FONT_SIZE_LG, weight=ft.FontWeight.W_700, color=COLOR_TEAL_DARK),
                            ft.Text(description, size=FONT_SIZE_MD, color=COLOR_GRAY_TEXT),
                            ft.Row(controls=badge_controls, wrap=True, spacing=SPACE_SM),
                        ],
                        spacing=SPACE_SM,
                    ),
                ),
            ],
            columns=12,
            run_spacing=SPACE_MD,
            spacing=SPACE_LG,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor="#FFFEFC",
        border=ft.Border.all(1, COLOR_GRAY_BORDER),
        border_radius=32,
        padding=ft.Padding.all(SPACE_XL),
        shadow=_panel_shadow(),
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=["#FFFEFC", "#F7FCFB", "#F1F8F6"],
        ),
    )


def create_staff_login_card(name: str, role: str, on_click: Optional[Callable[[ft.ControlEvent], None]] = None) -> ft.Container:
    role_text = _safe_text(role, "スタッフ")
    accent_bg = COLOR_VIOLET_SOFT if "管理" in role_text else COLOR_TEAL_SOFT
    accent_color = "#6A55D6" if "管理" in role_text else COLOR_TEAL_DARK

    return ft.Container(
        bgcolor="#FFFEFC",
        border=ft.Border.all(1, COLOR_GRAY_BORDER),
        border_radius=28,
        padding=ft.Padding.all(SPACE_XL),
        shadow=_panel_shadow(),
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            width=56,
                            height=56,
                            border_radius=20,
                            gradient=ft.LinearGradient(
                                begin=ft.Alignment(-1, -1),
                                end=ft.Alignment(1, 1),
                                colors=["#1A7F72", "#43B8A8"],
                            ),
                            alignment=ft.Alignment(0, 0),
                            content=ft.Text(_avatar_text(name), size=FONT_SIZE_LG, weight=ft.FontWeight.W_900, color=COLOR_WHITE),
                        ),
                        ft.Column(
                            controls=[
                                _meta_badge(role_text, accent_bg, accent_color),
                                ft.Text(name, size=FONT_SIZE_XL, weight=ft.FontWeight.W_900, color=COLOR_BLACK),
                            ],
                            spacing=6,
                            expand=True,
                        ),
                    ],
                    spacing=SPACE_MD,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text("担当の利用者記録、支援経過、当日状況の入力をすぐに開始できます。", size=FONT_SIZE_SM, color=COLOR_GRAY_TEXT),
                ft.Row(
                    controls=[
                        _badge("記録入力", COLOR_TEAL_SOFT, COLOR_TEAL_DARK, ft.Icons.EDIT_NOTE_ROUNDED),
                        _badge("AI下書き", COLOR_BLUE_SOFT, COLOR_BLUE, ft.Icons.AUTO_AWESOME_ROUNDED),
                    ],
                    spacing=SPACE_SM,
                    wrap=True,
                ),
                ft.ElevatedButton(
                    content=ft.Row(
                        controls=[
                            ft.Text("この職員で開始", size=FONT_SIZE_MD, weight=ft.FontWeight.W_800),
                            ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, size=18),
                        ],
                        spacing=8,
                        tight=True,
                    ),
                    on_click=on_click,
                    height=52,
                    style=ft.ButtonStyle(
                        bgcolor=COLOR_TEAL,
                        color=COLOR_WHITE,
                        elevation=0,
                        shadow_color="#00000000",
                        shape=ft.RoundedRectangleBorder(radius=18),
                    ),
                ),
            ],
            spacing=SPACE_MD,
        ),
    )


def create_vital_input_field(label: str, value: str, on_change: FloatChangeHandler) -> ft.Container:
    display_label = _normalize_display_text(label)
    step = _step_for_label(display_label)
    field = ft.TextField(
        value=str(value),
        adaptive=True,
        height=52,
        filled=False,
        bgcolor=COLOR_WHITE,
        text_size=FONT_SIZE_LG,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color=COLOR_GRAY_BORDER,
        content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_SM),
        on_change=lambda e: on_change(e.control.value or ""),
    )

    def adjust(delta: float) -> None:
        raw = (field.value or "").strip()
        try:
            current = float(raw) if raw else 0.0
        except ValueError:
            current = 0.0
        new_value = max(0.0, current + delta)
        field.value = _format_numeric(new_value, step)
        on_change(field.value)
        field.update()

    minus_button = ft.IconButton(
        icon=ft.Icons.REMOVE,
        icon_color=COLOR_TEAL,
        bgcolor=COLOR_WHITE,
        style=ft.ButtonStyle(side=ft.BorderSide(1, COLOR_TEAL_LIGHT), elevation=0),
        on_click=lambda e: adjust(-step),
    )
    plus_button = ft.IconButton(
        icon=ft.Icons.ADD,
        icon_color=COLOR_WHITE,
        bgcolor=COLOR_TEAL,
        style=ft.ButtonStyle(elevation=0),
        on_click=lambda e: adjust(step),
    )

    container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(display_label, size=FONT_SIZE_MD, weight=ft.FontWeight.W_700, color=COLOR_BLACK),
                field,
                ft.Row(
                    controls=[minus_button, plus_button],
                    spacing=SPACE_SM,
                    alignment=ft.MainAxisAlignment.END,
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
    container.data = {"field": field, "label": label}
    return container


def create_alert_dialog(message: str) -> ft.AlertDialog:
    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=COLOR_WHITE,
        title=ft.Row(
            controls=[
                ft.Container(width=34, height=34, border_radius=17, bgcolor=COLOR_ALERT_SOFT, alignment=ft.Alignment(0, 0), content=ft.Icon(ft.Icons.ERROR_OUTLINE, color=COLOR_ALERT_RED, size=18)),
                ft.Text("確認してください", color=COLOR_BLACK, weight=ft.FontWeight.W_800),
            ],
            spacing=8,
        ),
        content=ft.Text(message, color=COLOR_BLACK, size=FONT_SIZE_MD),
    )

    def close_dialog(e: ft.ControlEvent) -> None:
        dialog.open = False
        if dialog.page:
            dialog.page.update()

    dialog.actions = [
        ft.TextButton(
            "閉じる",
            on_click=close_dialog,
            style=ft.ButtonStyle(
                color=COLOR_WHITE,
                bgcolor=COLOR_TEAL,
                padding=ft.Padding.symmetric(horizontal=SPACE_LG, vertical=SPACE_SM),
            ),
        )
    ]
    return dialog


def create_meal_panel(
    selected_time: str,
    intake_value: int,
    is_self_cooking: bool,
    record_time: str,
    on_time_select: Callable[[str], None],
    on_intake_select: Callable[[int], None],
    on_self_cooking_change: BoolChangeHandler,
    on_record_time_change: Callable[[str], None],
    on_save: Optional[Callable[[ft.ControlEvent], None]] = None,
) -> ft.Container:
    time_buttons = ft.Row(
        controls=[_toggle_button(label, selected_time == label, lambda e, item=label: on_time_select(item), expand=True, compact=True) for label in ["朝", "昼", "夕"]],
        spacing=SPACE_SM,
        wrap=True,
    )
    intake_dropdown = ft.Dropdown(
        label="摂取量",
        value=str(intake_value),
        border_color=COLOR_GRAY_BORDER,
        content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_SM),
        options=[ft.DropdownOption(key=str(value), text=f"{value}/10") for value in range(1, 11)],
    )
    intake_dropdown.on_change = lambda e: on_intake_select(int(e.control.value or intake_value))
    checkbox = ft.Checkbox(label="自炊", value=is_self_cooking, active_color=COLOR_TEAL, on_change=lambda e: on_self_cooking_change(bool(e.control.value)))
    content: list[ft.Control] = [
        _time_input_row("記録時刻", record_time, on_record_time_change),
        ft.Text("時間帯", size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT),
        time_buttons,
        intake_dropdown,
        checkbox,
    ]
    if on_save is not None:
        content.append(ft.Row(controls=[_panel_save_button("食事を保存", on_save)], alignment=ft.MainAxisAlignment.END))
    container = _build_input_panel_shell("食事", "時間帯と摂取量をその場で記録", ft.Icons.RESTAURANT, content)
    container.data = {"selected_time": selected_time, "intake_value": intake_value, "is_self_cooking": is_self_cooking, "record_time": record_time}
    return container


def create_medication_panel(
    selected_timing: str,
    is_completed: bool,
    record_time: str,
    on_timing_select: Callable[[str], None],
    on_completed_change: BoolChangeHandler,
    on_record_time_change: Callable[[str], None],
    on_save: Optional[Callable[[ft.ControlEvent], None]] = None,
) -> ft.Container:
    timing_buttons = ft.Row(
        controls=[_toggle_button(label, selected_timing == label, lambda e, item=label: on_timing_select(item), compact=True) for label in ["食前", "食後", "就寝前", "頓服"]],
        spacing=SPACE_SM,
        scroll=ft.ScrollMode.AUTO,
    )
    checkbox = ft.Checkbox(label="服薬完了", value=is_completed, active_color=COLOR_ORANGE, on_change=lambda e: on_completed_change(bool(e.control.value)))
    content: list[ft.Control] = [
        _time_input_row("記録時刻", record_time, on_record_time_change),
        ft.Text("タイミング", size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT),
        timing_buttons,
        checkbox,
    ]
    if on_save is not None:
        content.append(ft.Row(controls=[_panel_save_button("服薬を保存", on_save)], alignment=ft.MainAxisAlignment.END))
    container = _build_input_panel_shell("服薬", "服薬タイミングと実施有無を記録", ft.Icons.MEDICATION, content)
    container.data = {"selected_timing": selected_timing, "is_completed": is_completed, "record_time": record_time}
    return container


def create_bathing_input_panel(
    selected_status: str,
    record_time: str,
    on_status_select: Callable[[str], None],
    on_record_time_change: Callable[[str], None],
    on_save: Optional[Callable[[ft.ControlEvent], None]] = None,
) -> ft.Container:
    status_buttons = ft.Row(
        controls=[
            _toggle_button(label, selected_status == label, lambda e, item=label: on_status_select(item), expand=True, compact=True)
            for label in ["未実施", "シャワー", "浴槽"]
        ],
        spacing=SPACE_SM,
        wrap=True,
    )
    status_note = {"未実施": "本日は未実施で記録されます。", "シャワー": "シャワー浴として記録されます。", "浴槽": "浴槽入浴として記録されます。"}.get(selected_status, "入浴状態を選択してください。")
    content: list[ft.Control] = [
        _time_input_row("記録時刻", record_time, on_record_time_change),
        status_buttons,
        ft.Container(content=ft.Text(status_note, size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT), bgcolor=COLOR_BLUE_SOFT, border_radius=RADIUS_MD, padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_SM)),
    ]
    if on_save is not None:
        content.append(ft.Row(controls=[_panel_save_button("入浴を保存", on_save)], alignment=ft.MainAxisAlignment.END))
    container = _build_input_panel_shell("入浴", "本日の入浴状態を簡単に記録", ft.Icons.BATHTUB, content)
    container.data = {"selected_status": selected_status, "record_time": record_time}
    return container


def create_patrol_input_panel(
    selected_time: str,
    selected_sleep: str,
    on_time_select: Callable[[str], None],
    on_sleep_select: Callable[[str], None],
    on_safety_change: FloatChangeHandler,
    on_save: Optional[Callable[[ft.ControlEvent], None]] = None,
) -> ft.Container:
    sleep_buttons = ft.Row(
        controls=[_toggle_button(label, selected_sleep == label, lambda e, item=label: on_sleep_select(item), expand=True, compact=True) for label in ["眠れている", "覚醒"]],
        spacing=SPACE_SM,
        wrap=True,
    )
    safety_field = ft.TextField(
        label="安全確認（室温・転倒リスクなど）",
        value="",
        adaptive=True,
        multiline=True,
        min_lines=2,
        max_lines=4,
        filled=False,
        bgcolor=COLOR_WHITE,
        border_color=COLOR_GRAY_BORDER,
        content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_SM),
        on_change=lambda e: on_safety_change(e.control.value or ""),
    )
    content: list[ft.Control] = [
        _time_input_row("巡視時刻", selected_time, on_time_select),
        ft.Text("睡眠状態", size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT),
        sleep_buttons,
        safety_field,
    ]
    if on_save is not None:
        content.append(ft.Row(controls=[_panel_save_button("巡視を保存", on_save)], alignment=ft.MainAxisAlignment.END))
    container = _build_input_panel_shell("夜間巡視", "時刻・睡眠状態・安全確認を記録", ft.Icons.NIGHTLIGHT, content)
    container.data = {"selected_time": selected_time, "selected_sleep": selected_sleep, "safety_field": safety_field}
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
    category_dropdown = ft.Dropdown(
        label="区分",
        value=selected_category or (categories[0] if categories else ""),
        border_color=COLOR_GRAY_BORDER,
        content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_SM),
        options=[ft.DropdownOption(key=label, text=label) for label in categories],
    )
    category_dropdown.on_change = lambda e: on_category_select(e.control.value or "")

    note_field = ft.TextField(
        label="支援内容",
        value=note_text,
        multiline=True,
        min_lines=6,
        border_color=COLOR_GRAY_BORDER,
        content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_SM),
        hint_text="例: 食後に服薬確認。体調や様子、安全確認などを記録。",
        on_change=lambda e: on_text_change(e.control.value or ""),
    )
    meta_row = ft.Row(
        controls=[
            _badge(selected_category or "未選択", COLOR_TEAL_SOFT, COLOR_TEAL_DARK, ft.Icons.LABEL),
            _badge(recorded_at_text, COLOR_BLUE_SOFT, COLOR_BLUE, ft.Icons.SCHEDULE),
            _badge(staff_name or "職員未選択", COLOR_SLATE_SOFT, COLOR_GRAY_TEXT, ft.Icons.PERSON),
        ],
        spacing=SPACE_SM,
        wrap=True,
    )
    content: list[ft.Control] = []
    if is_editing:
        content.append(
            ft.Container(
                bgcolor="#EFF6FF",
                border=ft.Border.all(1, "#BFDBFE"),
                border_radius=12,
                padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
                content=ft.Text("支援経過記録を編集中です。内容を確認して更新してください。", size=FONT_SIZE_SM, color=COLOR_BLUE, weight=ft.FontWeight.W_700),
            )
        )
    content.extend([
        category_dropdown,
        _time_input_row("記録時刻", record_time, on_record_time_change),
        meta_row,
        note_field,
    ])
    if on_save is not None:
        actions: list[ft.Control] = []
        if is_editing and on_cancel is not None:
            actions.append(ft.TextButton("キャンセル", on_click=on_cancel, style=ft.ButtonStyle(color=COLOR_GRAY_TEXT)))
        actions.append(_panel_save_button("支援経過を更新" if is_editing else "支援経過を保存", on_save))
        content.append(ft.Row(controls=actions, alignment=ft.MainAxisAlignment.END, spacing=SPACE_SM, wrap=True))
    container = _build_input_panel_shell("支援経過入力", "区分を選択して支援内容を記録", ft.Icons.EDIT_NOTE, content)
    container.data = {"selected_category": selected_category, "note_field": note_field, "record_time": record_time, "is_editing": is_editing}
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
    category_buttons = ft.Row(
        controls=[
            _toggle_button(
                label,
                active_category == label,
                lambda e, item=label: on_category_select(item),
                compact=True,
            )
            for label in categories
        ],
        spacing=SPACE_SM,
        wrap=True,
    )

    note_field = ft.TextField(
        label="支援内容",
        value=note_text,
        adaptive=True,
        multiline=True,
        min_lines=4,
        max_lines=8,
        filled=False,
        bgcolor=COLOR_WHITE,
        border_color=COLOR_GRAY_BORDER,
        content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_SM),
        hint_text="例: 食後の服薬確認、表情や発語、夜間の巡視内容などを記録",
        on_change=lambda e: on_text_change(e.control.value or ""),
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
    content: list[ft.Control] = []
    if is_editing:
        content.append(
            ft.Container(
                bgcolor="#EFF6FF",
                border=ft.Border.all(1, "#BFDBFE"),
                border_radius=12,
                padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
                content=ft.Text("記録を編集中です。内容を確認して更新してください。", size=FONT_SIZE_SM, color=COLOR_BLUE, weight=ft.FontWeight.W_700),
            )
        )
    content.extend(
        [
            ft.Text("区分", size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT, weight=ft.FontWeight.W_700),
            category_buttons,
            _mobile_safe_time_input_row("記録時刻", record_time, on_record_time_change),
            meta_row,
            note_field,
        ]
    )
    if on_save is not None:
        actions: list[ft.Control] = []
        if is_editing and on_cancel is not None:
            actions.append(ft.TextButton("キャンセル", on_click=on_cancel, style=ft.ButtonStyle(color=COLOR_GRAY_TEXT)))
        actions.append(_panel_save_button("記録を更新" if is_editing else "記録を保存", on_save))
        content.append(ft.Row(controls=actions, alignment=ft.MainAxisAlignment.END, spacing=SPACE_SM, wrap=True))
    container = _build_input_panel_shell("支援経過入力", "区分を選択して支援内容を記録", ft.Icons.EDIT_NOTE, content)
    container.data = {"selected_category": active_category, "note_field": note_field, "record_time": record_time, "is_editing": is_editing}
    return container


def create_support_progress_record_card(record: dict, on_edit=None, on_delete=None) -> ft.Container:
    category = _safe_text(record.get("category"), "支援経過")
    content = _safe_text(record.get("content"), "記録なし")
    staff_name = _safe_text(record.get("staff_name"), "-")
    recorded_at = _format_dt_short(record.get("recorded_at"))
    is_auto = category == "支援経過" or str(record.get("content") or "").startswith("【自動連携:")
    bg = COLOR_TEAL_SOFT if is_auto else COLOR_WHITE
    border = COLOR_TEAL_LIGHT if is_auto else COLOR_GRAY_BORDER
    left = ft.Row(
        controls=[
            _badge(category, COLOR_WHITE if is_auto else COLOR_BLUE_SOFT, COLOR_TEAL_DARK if is_auto else COLOR_BLUE, ft.Icons.LABEL),
            _badge(recorded_at, COLOR_SLATE_SOFT, COLOR_GRAY_TEXT, ft.Icons.SCHEDULE),
            _badge(staff_name, COLOR_SLATE_SOFT, COLOR_GRAY_TEXT, ft.Icons.PERSON),
        ],
        spacing=SPACE_SM,
        wrap=True,
    )
    actions: list[ft.Control] = []
    if on_edit is not None:
        actions.append(ft.TextButton("編集", on_click=on_edit, style=ft.ButtonStyle(color=COLOR_TEAL)))
    if on_delete is not None:
        actions.append(ft.TextButton("削除", on_click=on_delete, style=ft.ButtonStyle(color=COLOR_ALERT_RED)))
    return ft.Container(
        bgcolor=bg,
        border=ft.Border.all(1, border),
        border_radius=RADIUS_MD,
        padding=ft.Padding.all(SPACE_MD),
        content=ft.Column(
            controls=[
                left,
                ft.Row(controls=actions, spacing=0, wrap=True, alignment=ft.MainAxisAlignment.END) if actions else ft.Container(),
                ft.Text(content, size=FONT_SIZE_MD, color=COLOR_BLACK),
            ],
            spacing=SPACE_SM,
        ),
    )


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
    category_buttons = ft.Row(
        controls=[
            _toggle_button(label, active_category == label, lambda e, item=label: on_category_select(item), compact=True)
            for label in categories
        ],
        spacing=SPACE_SM,
        wrap=True,
    )

    note_field = ft.TextField(
        label="支援内容",
        value=note_text,
        adaptive=True,
        multiline=True,
        min_lines=4,
        max_lines=8,
        filled=False,
        bgcolor=COLOR_WHITE,
        border_color=COLOR_GRAY_BORDER,
        content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_SM),
        hint_text="例: 食後の服薬確認、表情や発語、夜間の巡視内容などを記録",
        on_change=lambda e: on_text_change(e.control.value or ""),
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

    content: list[ft.Control] = []
    if is_editing:
        content.append(
            ft.Container(
                bgcolor="#EFF6FF",
                border=ft.Border.all(1, "#BFDBFE"),
                border_radius=12,
                padding=ft.Padding.symmetric(horizontal=SPACE_MD, vertical=SPACE_SM),
                content=ft.Text("記録を編集中です。内容を確認して更新してください。", size=FONT_SIZE_SM, color=COLOR_BLUE, weight=ft.FontWeight.W_700),
            )
        )

    content.extend(
        [
            ft.Text("区分", size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT, weight=ft.FontWeight.W_700),
            category_buttons,
            _mobile_safe_time_input_row("記録時刻", record_time, on_record_time_change),
            meta_row,
            note_field,
        ]
    )

    if on_save is not None:
        actions: list[ft.Control] = []
        if is_editing and on_cancel is not None:
            actions.append(ft.TextButton("キャンセル", on_click=on_cancel, style=ft.ButtonStyle(color=COLOR_GRAY_TEXT)))
        actions.append(_panel_save_button("記録を更新" if is_editing else "記録を保存", on_save))
        content.append(ft.Row(controls=actions, alignment=ft.MainAxisAlignment.END, spacing=SPACE_SM, wrap=True))

    container = _build_input_panel_shell("支援経過入力", "区分を選択して支援内容を記録", ft.Icons.EDIT_NOTE, content)
    container.data = {
        "selected_category": active_category,
        "note_field": note_field,
        "record_time": record_time,
        "is_editing": is_editing,
    }
    return container


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
        _time_input_row("測定時刻", record_time, on_record_time_change),
        temperature_control,
        systolic_control,
        diastolic_control,
        spo2_control,
    ]
    if on_save is not None:
        content.append(ft.Row(controls=[_panel_save_button("バイタルを保存", on_save)], alignment=ft.MainAxisAlignment.END))
    container = _build_input_panel_shell("バイタル", "体温・血圧・SpO2を記録", ft.Icons.MONITOR_HEART, content)
    container.data = {"temperature": temperature_control, "systolic": systolic_control, "diastolic": diastolic_control, "spo2": spo2_control, "record_time": record_time}
    return container


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
    container = _build_input_panel_shell("バイタル入力", "体温・血圧・SpO2を記録", ft.Icons.MONITOR_HEART, content)
    container.data = {
        "temperature": temperature_control,
        "systolic": systolic_control,
        "diastolic": diastolic_control,
        "spo2": spo2_control,
        "record_time": record_time,
    }
    return container


def _mobile_safe_time_input_row(
    label: str,
    value: str,
    on_change: Callable[[str], None],
) -> ft.Control:
    hour_value, minute_value = _split_time_value(value)

    hour_field = ft.TextField(
        label=f"{_normalize_display_text(label)} (時)",
        value=hour_value,
        adaptive=True,
        width=124,
        height=56,
        filled=False,
        bgcolor=COLOR_WHITE,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color=COLOR_GRAY_BORDER,
        content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_SM),
    )
    minute_field = ft.TextField(
        label="分",
        value=minute_value,
        adaptive=True,
        width=124,
        height=56,
        filled=False,
        bgcolor=COLOR_WHITE,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color=COLOR_GRAY_BORDER,
        content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_SM),
    )

    def handle_time_change(_e: ft.ControlEvent) -> None:
        composed = _compose_time_value(hour_field.value or "0", minute_field.value or "0")
        normalized_hour, normalized_minute = _split_time_value(composed)
        hour_field.value = normalized_hour
        minute_field.value = normalized_minute
        hour_field.update()
        minute_field.update()
        on_change(composed)

    hour_field.on_blur = handle_time_change
    minute_field.on_blur = handle_time_change
    hour_field.on_submit = handle_time_change
    minute_field.on_submit = handle_time_change

    return ft.Column(
        controls=[
            ft.Row(
                controls=[hour_field, minute_field],
                spacing=SPACE_SM,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text("時: 0〜23 / 分: 0〜55（5分刻み）", size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT, weight=ft.FontWeight.W_700),
        ],
        spacing=6,
    )


def _daily_chip_colors(kind: str, item: dict) -> tuple[str, str]:
    if kind == "meal":
        amount = item.get("amount")
        if amount is None:
            return (COLOR_SLATE_SOFT, COLOR_GRAY_TEXT)
        if amount >= 8:
            return (COLOR_GREEN_SOFT, COLOR_GREEN)
        if amount >= 5:
            return ("#FEF3C7", "#B45309")
        return ("#FEE2E2", "#B91C1C")
    if kind == "bath":
        status = _safe_text(item.get("status") or item.get("label"), "未記録")
        if status == "浴槽":
            return ("#DBEAFE", "#1D4ED8")
        if status == "シャワー":
            return ("#E0F2FE", "#0369A1")
        if status == "清拭":
            return ("#ECFEFF", "#0F766E")
        if status == "未実施":
            return (COLOR_SLATE_SOFT, "#64748B")
        return (COLOR_VIOLET_SOFT, "#6D28D9")
    if kind == "patrol":
        status = _safe_text(item.get("status") or item.get("sleep") or item.get("label"), "未記録")
        if status == "眠れている":
            return ("#EDE9FE", "#6D28D9")
        if status == "覚醒":
            return ("#FEF3C7", "#B45309")
        return (COLOR_SLATE_SOFT, COLOR_GRAY_TEXT)
    status = _safe_text(item.get("status") or item.get("label"), "未記録")
    if status == "完了":
        return (COLOR_ORANGE_SOFT, COLOR_ORANGE)
    if status == "未":
        return ("#FEE2E2", COLOR_ALERT_RED)
    return (COLOR_SLATE_SOFT, COLOR_GRAY_TEXT)


def _build_daily_status_chip(timing: str, item: dict, kind: str) -> ft.Container:
    value_text = _safe_text(item.get("label"), "未記録")
    bgcolor, text_color = _daily_chip_colors(kind, item)
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(timing, size=FONT_SIZE_XS, color=text_color, weight=ft.FontWeight.W_700),
                ft.Text(value_text, size=FONT_SIZE_XS, color=text_color, weight=ft.FontWeight.W_700),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        bgcolor=bgcolor,
        border_radius=999,
        padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=6),
    )


def _build_bath_status_section(title: str, bath_item: dict) -> ft.Column:
    bath_item = bath_item or {}
    status_text = _safe_text(bath_item.get("label") or bath_item.get("status"), "未記録")
    bgcolor, text_color = _daily_chip_colors("bath", bath_item)
    chips = [_badge(status_text, bgcolor, text_color, ft.Icons.BATHTUB)]
    if bath_item.get("recorded_at"):
        chips.append(_badge(_format_dt_short(bath_item.get("recorded_at")), COLOR_SLATE_SOFT, COLOR_GRAY_TEXT, ft.Icons.SCHEDULE))
    return ft.Column(
        controls=[ft.Text(title, size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT, weight=ft.FontWeight.W_700), ft.Row(controls=chips, spacing=SPACE_SM, wrap=True)],
        spacing=SPACE_XS,
    )


def _build_patrol_status_section(title: str, patrol_item: dict) -> ft.Column:
    patrol_item = patrol_item or {}
    status_text = _safe_text(patrol_item.get("sleep") or patrol_item.get("status") or patrol_item.get("label"), "未記録")
    time_text = _safe_text(patrol_item.get("time"), "時刻未記録")
    safety_text = _safe_text(patrol_item.get("safety"), "安全確認未記録")
    bgcolor, text_color = _daily_chip_colors("patrol", patrol_item)
    chips = [_badge(time_text, COLOR_SLATE_SOFT, COLOR_GRAY_TEXT, ft.Icons.SCHEDULE), _badge(status_text, bgcolor, text_color, ft.Icons.NIGHTLIGHT)]
    if safety_text not in {"未記録", "安全確認未記録", "記載なし"}:
        chips.append(_badge(safety_text, COLOR_BLUE_SOFT, COLOR_BLUE, ft.Icons.VERIFIED_USER))
    elif patrol_item.get("recorded_at"):
        chips.append(_badge(_format_dt_short(patrol_item.get("recorded_at")), COLOR_SLATE_SOFT, COLOR_GRAY_TEXT, ft.Icons.ACCESS_TIME))
    return ft.Column(
        controls=[ft.Text(title, size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT, weight=ft.FontWeight.W_700), ft.Row(controls=chips, spacing=SPACE_SM, wrap=True)],
        spacing=SPACE_XS,
    )


def _build_daily_status_section(title: str, status_map: dict, kind: str) -> ft.Column:
    if kind == "bath":
        return _build_bath_status_section(title, status_map)
    if kind == "patrol":
        return _build_patrol_status_section(title, status_map)
    chips = [_build_daily_status_chip(timing, status_map.get(timing, {}), kind) for timing in ("朝", "昼", "夕")]
    return ft.Column(
        controls=[ft.Text(title, size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT, weight=ft.FontWeight.W_700), ft.Row(controls=chips, spacing=SPACE_SM)],
        spacing=SPACE_XS,
    )


def create_resident_dashboard_card(resident: dict, on_click=None, daily_status: Optional[dict] = None) -> ft.Container:
    name = _safe_text(resident.get("name"), "利用者")
    unit_name = _safe_text(resident.get("unit_name"), "ユニット未設定")
    diagnosis = _safe_text(resident.get("diagnosis"), "未登録")
    care_level = _safe_text(resident.get("care_level"), "未登録")
    latest_time = _format_dt_short(resident.get("latest_recorded_at"))

    action = ft.TextButton(
        "開く",
        on_click=on_click,
        style=ft.ButtonStyle(color=COLOR_TEAL),
    ) if on_click is not None else ft.Container()

    return ft.Container(
        bgcolor="#FFFEFC",
        border=ft.Border.all(1, COLOR_GRAY_BORDER),
        border_radius=RADIUS_LG,
        padding=ft.Padding.all(SPACE_LG),
        margin=ft.Margin.only(bottom=SPACE_SM),
        shadow=_panel_shadow(),
        content=ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text(name, size=FONT_SIZE_LG, weight=ft.FontWeight.W_800, color=COLOR_BLACK),
                        ft.Text(unit_name, size=FONT_SIZE_SM, color=COLOR_GRAY_TEXT),
                        ft.Text(f"病症: {diagnosis}", size=FONT_SIZE_SM, color=COLOR_GRAY_TEXT),
                        ft.Text(f"区分: {care_level}", size=FONT_SIZE_SM, color=COLOR_GRAY_TEXT),
                        ft.Text(f"最終記録: {latest_time}", size=FONT_SIZE_XS, color=COLOR_GRAY_TEXT),
                    ],
                    spacing=4,
                    expand=True,
                ),
                action,
            ],
            spacing=SPACE_SM,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
