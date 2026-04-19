
from __future__ import annotations

from datetime import datetime, timedelta
import threading
from typing import Any, Dict, List, Optional

import flet as ft

import ai_service
import database
from record_service import save_daily_category_record
from state_models import AppState, DEFAULT_VITAL_VALUES, MasterResidentForm, MasterStaffForm
from ui_parts import (
    COLOR_BLACK,
    COLOR_GRAY_TEXT,
    COLOR_TEAL,
    COLOR_TEAL_SOFT,
    COLOR_WHITE,
    FONT_SIZE_LG,
    FONT_SIZE_MD,
    FONT_SIZE_SM,
    FONT_SIZE_XL,
    RADIUS_MD,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    create_alert_dialog,
    create_app_brand_hero,
    create_bathing_input_panel,
    create_meal_panel,
    create_medication_panel,
    create_patrol_input_panel,
    create_resident_button,
    create_resident_dashboard_card,
    create_shared_header,
    create_staff_login_card,
    create_support_progress_panel,
    create_support_progress_record_card,
    create_vital_input_field,
    create_vital_panel,
)
from mobile_ui_parts import (
    create_bathing_input_panel,
    create_meal_panel,
    create_medication_panel,
    create_patrol_input_panel,
    create_support_progress_panel,
    create_vital_input_field,
    create_vital_panel,
)

DEFAULT_SCENE = "朝"
ABNORMAL_RULES = {
    "temperature_high": 37.5,
    "systolic_high": 140,
    "diastolic_high": 90,
    "spo2_low": 95,
}
SUPPORT_PROGRESS_OPTIONS = ["ご様子", "通所", "受診", "訪問看護", "移動支援", "外出", "外泊"]
APP_BG = "#F3F8F7"
APP_BG_ALT = "#EAF3F1"
APP_SURFACE = "#FFFDFC"
APP_BORDER = "#DCE8E4"
APP_TEXT_MUTED = "#667A76"
APP_TIFFANY_DEEP = "#1A7F72"
APP_NAVY = "#173431"
APP_WARNING = "#D08A29"
MAX_CONTENT_WIDTH = 1180


def parse_float(text: str) -> Optional[float]:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_int(text: str) -> Optional[int]:
    value = parse_float(text)
    return None if value is None else int(round(value))


def current_time_hhmm() -> str:
    now = datetime.now()
    hour = now.hour
    minute = (now.minute // 5) * 5
    return f"{hour}:{minute:02d}"


def normalize_time_text(value: str) -> str:
    text = (value or "").strip().replace("：", ":")
    if not text:
        return ""
    if ":" in text:
        hour_text, minute_text = text.split(":", 1)
    elif len(text) in (3, 4) and text.isdigit():
        hour_text, minute_text = text[:-2], text[-2:]
    else:
        raise ValueError(f"時刻 '{value}' は HH:MM 形式で入力してください。")
    try:
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError as exc:
        raise ValueError(f"時刻 '{value}' は HH:MM 形式で入力してください。") from exc
    if hour < 0 or hour > 23:
        raise ValueError("時は 1〜24 の範囲で選択してください。")
    if minute < 0 or minute > 55 or minute % 5 != 0:
        raise ValueError("分は 0〜55 の5分刻みで選択してください。")
    return f"{hour}:{minute:02d}"


def build_recorded_at_from_selected_date(selected_date, time_text: str) -> str:
    normalized = normalize_time_text(time_text)
    if not normalized:
        raise ValueError("時刻を入力してください。")
    hour_text, minute_text = normalized.split(":", 1)
    hour = int(hour_text)
    minute = int(minute_text)
    parsed_time = datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
    return datetime.combine(selected_date, parsed_time).strftime("%Y-%m-%d %H:%M:%S")


def normalize_daily_timing_label(value: str) -> str:
    mapping = {"朝": "朝", "昼": "昼", "夜": "夕", "夕": "夕"}
    return mapping.get((value or "").strip(), "朝")


def build_friendly_ai_error(message: str) -> str:
    text = str(message or "")
    if "APIキー" in text:
        return "AI設定が未完了です。APIキーをご確認ください。"
    if "利用上限" in text or "課金" in text or "レート制限" in text:
        return "AIの利用上限に達している可能性があります。"
    if "通信" in text or "ネットワーク" in text or "タイムアウト" in text:
        return "通信に失敗しました。ネットワーク状態をご確認ください。"
    return text or "AI下書きの作成に失敗しました。"


def main(page: ft.Page) -> None:
    database.init_db()
    database.ensure_default_master_data()

    page.title = "福祉記録アプリ"
    page.bgcolor = APP_BG
    page.padding = 16
    page.scroll = ft.ScrollMode.AUTO
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        font_family="Bahnschrift",
        color_scheme=ft.ColorScheme(primary=APP_TIFFANY_DEEP),
    )

    state = AppState()
    root = ft.Container(expand=True)
    message_overlay: Optional[ft.Container] = None

    def show_dialog(dialog: ft.AlertDialog) -> None:
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_message(message: str, bgcolor: str = APP_TIFFANY_DEEP) -> None:
        token = datetime.now().timestamp()
        state.refs["flash_message"] = message
        state.refs["flash_token"] = token
        render_screen()

        def clear_flash() -> None:
            if state.refs.get("flash_token") != token:
                return
            state.refs.pop("flash_message", None)
            state.refs.pop("flash_token", None)
            render_screen()

        threading.Timer(2.2, clear_flash).start()

    def build_flash_message() -> Optional[ft.Control]:
        message = state.refs.get("flash_message")
        if not message:
            return None
        return ft.Container(
            bgcolor=APP_TIFFANY_DEEP,
            border_radius=18,
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=18, color="#0F172A22", offset=ft.Offset(0, 8)),
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=30,
                        height=30,
                        border_radius=15,
                        bgcolor="#FFFFFF33",
                        alignment=ft.Alignment(0, 0),
                        content=ft.Icon(ft.Icons.CHECK_CIRCLE, color=COLOR_WHITE, size=17),
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("\u4fdd\u5b58\u3057\u307e\u3057\u305f", color=COLOR_WHITE, weight=ft.FontWeight.W_900, size=FONT_SIZE_SM),
                            ft.Text(str(message), color=COLOR_WHITE, size=FONT_SIZE_SM),
                        ],
                        spacing=2,
                        tight=True,
                    ),
                ],
                spacing=12,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def build_banner(message: str, kind: str = "info") -> ft.Control:
        styles = {
            "info": ("#EDF6FF", "#BFDBFE", "#1D4ED8", ft.Icons.INFO_OUTLINE),
            "success": ("#ECFDF5", "#A7F3D0", "#166534", ft.Icons.CHECK_CIRCLE_OUTLINE),
            "warning": ("#FFF7ED", "#FED7AA", "#B45309", ft.Icons.WARNING_AMBER_OUTLINED),
            "error": ("#FEF2F2", "#FECACA", "#991B1B", ft.Icons.ERROR_OUTLINE),
        }
        bg, border, color, icon = styles[kind]
        return ft.Container(
            bgcolor=bg,
            border=ft.Border.all(1, border),
            border_radius=14,
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            content=ft.Column(
                controls=[
                    ft.Icon(icon, size=18, color=color),
                    ft.Text(message, color=color, weight=ft.FontWeight.W_700, expand=True),
                ],
                spacing=8,
            ),
        )

    def build_centered_container(control: ft.Control, width: int = MAX_CONTENT_WIDTH) -> ft.Control:
        target_width = width
        viewport_width = getattr(page, "width", None)
        if isinstance(viewport_width, (int, float)) and viewport_width > 0:
            target_width = min(width, max(280, int(viewport_width) - 24))
        try:
            control.width = target_width
        except Exception:
            pass
        return ft.Row(controls=[control], alignment=ft.MainAxisAlignment.CENTER, wrap=True)

    def build_filled_button(label: str, on_click: Any, disabled: bool = False, icon: Optional[str] = None) -> ft.Control:
        return ft.ElevatedButton(
            content=ft.Row(
                controls=([ft.Icon(icon, size=16)] if icon else []) + [ft.Text(label, weight=ft.FontWeight.W_700)],
                spacing=8,
                tight=True,
            ),
            on_click=on_click,
            disabled=disabled,
            height=48,
            style=ft.ButtonStyle(
                bgcolor=APP_TIFFANY_DEEP,
                color=COLOR_WHITE,
                elevation=0,
                shadow_color="#00000000",
                shape=ft.RoundedRectangleBorder(radius=18),
                padding=ft.Padding.symmetric(horizontal=22, vertical=14),
            ),
        )

    def build_outline_button(label: str, on_click: Any, icon: Optional[str] = None) -> ft.Control:
        return ft.ElevatedButton(
            content=ft.Row(
                controls=([ft.Icon(icon, size=16)] if icon else []) + [ft.Text(label, weight=ft.FontWeight.W_700)],
                spacing=8,
                tight=True,
            ),
            on_click=on_click,
            height=48,
            style=ft.ButtonStyle(
                bgcolor="#FCFEFD",
                color=APP_TIFFANY_DEEP,
                elevation=0,
                side=ft.BorderSide(1, APP_TIFFANY_DEEP),
                shadow_color="#00000000",
                shape=ft.RoundedRectangleBorder(radius=18),
                padding=ft.Padding.symmetric(horizontal=22, vertical=14),
            ),
        )

    def build_card_column(controls: List[ft.Control], title: Optional[str] = None) -> ft.Control:
        inner_controls: List[ft.Control] = []
        if title:
            inner_controls.append(ft.Text(title, size=FONT_SIZE_LG, weight=ft.FontWeight.W_900, color=APP_NAVY))
        inner_controls.extend(controls)
        return ft.Container(
            bgcolor=APP_SURFACE,
            border=ft.Border.all(1, APP_BORDER),
            border_radius=26,
            padding=22,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[APP_SURFACE, "#F8FCFB"],
            ),
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=24, color="#17343112", offset=ft.Offset(0, 10)),
            content=ft.Column(controls=inner_controls, spacing=SPACE_MD),
        )

    def build_screen_shell(header: ft.Control, body_controls: List[ft.Control]) -> ft.Control:
        controls = [build_centered_container(header)]
        flash = build_flash_message()
        if flash is not None:
            controls.append(build_centered_container(flash))
        controls.extend(build_centered_container(control) for control in body_controls)
        return ft.Container(
            expand=True,
            padding=ft.Padding.symmetric(horizontal=10, vertical=12),
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[APP_BG, APP_BG_ALT, "#F7FBFA"],
            ),
            content=ft.Column(
                controls=controls,
                spacing=SPACE_MD,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        )

    def build_abnormal_messages(temperature, systolic_bp, diastolic_bp, spo2) -> List[str]:
        messages: List[str] = []
        if temperature is not None and temperature >= ABNORMAL_RULES["temperature_high"]:
            messages.append(f"体温が {temperature:.1f}℃ です。37.5℃以上です。")
        if systolic_bp is not None and systolic_bp >= ABNORMAL_RULES["systolic_high"]:
            messages.append(f"最高血圧が {systolic_bp} mmHg です。")
        if diastolic_bp is not None and diastolic_bp >= ABNORMAL_RULES["diastolic_high"]:
            messages.append(f"最低血圧が {diastolic_bp} mmHg です。")
        if spo2 is not None and spo2 < ABNORMAL_RULES["spo2_low"]:
            messages.append(f"SpO2が {spo2}% です。95%未満です。")
        return messages

    def current_staff_text() -> str:
        if not state.staff:
            return "職員未選択"
        return f"{state.staff.get('name')}（{state.staff.get('role') or '-'}）でログイン中"

    def current_resident_text() -> str:
        resident = state.resident
        if not resident:
            return "利用者未選択"
        return f"利用者: {resident['name']}"

    def resident_meta_items(resident: Optional[Dict[str, Any]]) -> List[str]:
        if not resident:
            return []
        diagnosis = (resident.get("diagnosis") or "").strip() or "未登録"
        care_level = (resident.get("care_level") or "").strip() or "未登録"
        unit_name = resident.get("unit_name") or "ユニット未設定"
        return [f"ユニット: {unit_name}", f"病症: {diagnosis}", f"区分: {care_level}"]

    def format_selected_date(value) -> str:
        weekdays = "月火水木金土日"
        return value.strftime(f"%Y年%m月%d日({weekdays[value.weekday()]})")

    def get_selected_recorded_at(time_text: str) -> str:
        return build_recorded_at_from_selected_date(state.selected_date, time_text)

    def extract_record_time(recorded_at) -> str:
        text = str(recorded_at or "").strip()
        if not text:
            return current_time_hhmm()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(text, fmt).strftime("%H:%M")
            except ValueError:
                continue
        return current_time_hhmm()

    def refresh_dashboard_data() -> None:
        target_date_str = state.selected_date.strftime("%Y-%m-%d")
        residents = database.list_residents_with_latest_status()
        for resident in residents:
            resident["daily_status"] = database.get_resident_daily_status(resident["id"], target_date=target_date_str)
        state.dashboard_residents = residents

    def refresh_master_data() -> None:
        units = database.list_units()
        state.master_units = units
        state.master_staff_list = database.list_staff()
        state.master_resident_list = database.list_residents()
        if state.master_resident_form.unit_id is None and units:
            state.master_resident_form.unit_id = units[0]["id"]

    def refresh_support_progress_data() -> None:
        resident = state.resident
        if not resident:
            state.support_progress_records = []
            return
        selected_date = state.selected_date.strftime("%Y-%m-%d")
        state.support_progress_records = database.list_support_progress_records(
            resident_id=resident["id"],
            date_from=f"{selected_date} 00:00:00",
            date_to=f"{selected_date} 23:59:59",
            limit=100,
        )

    def reset_support_progress_form() -> None:
        state.support_progress.category = "ご様子"
        state.support_progress.content = ""
        state.support_progress.record_time = current_time_hhmm()
        state.support_progress.edit_id = None
        state.support_progress.ai_generated = False

    def reset_input_values() -> None:
        state.vital_values = DEFAULT_VITAL_VALUES.copy()
        state.meal.time = "朝"
        state.meal.intake = 10
        state.meal.self_cooking = False
        state.meal.record_time = current_time_hhmm()
        state.medication.timing = "食後"
        state.medication.completed = True
        state.medication.record_time = current_time_hhmm()
        state.bathing.status = "未実施"
        state.bathing.record_time = current_time_hhmm()
        state.patrol.time = "22:00"
        state.patrol.sleep = "眠れている"
        state.patrol.safety = ""
        reset_support_progress_form()
        state.refs = {}

    def reset_staff_form() -> None:
        state.master_staff_form = MasterStaffForm()
        state.master_staff_edit_id = None

    def reset_resident_form() -> None:
        unit_id = state.master_units[0]["id"] if state.master_units else None
        state.master_resident_form = MasterResidentForm(unit_id=unit_id)
        state.master_resident_edit_id = None

    def refresh_selected_resident() -> None:
        resident = state.resident
        if not resident:
            return
        resident_id = resident.get("id")
        refresh_dashboard_data()
        for item in state.dashboard_residents:
            if item.get("id") == resident_id:
                state.resident = item
                break
        refresh_support_progress_data()

    def change_selected_date(days: int) -> None:
        state.selected_date = state.selected_date + timedelta(days=days)
        refresh_dashboard_data()
        refresh_support_progress_data()
        render_screen()

    def move_to_prev_date(e=None):
        change_selected_date(-1)

    def move_to_next_date(e=None):
        change_selected_date(1)

    def move_to_today(e=None):
        state.selected_date = datetime.now().date()
        refresh_dashboard_data()
        refresh_support_progress_data()
        render_screen()

    def go_to_staff_select(e=None):
        state.screen = "staff_select"
        state.resident = None
        render_screen()

    def go_to_dashboard(e=None):
        refresh_dashboard_data()
        state.screen = "dashboard"
        render_screen()

    def go_to_resident_input(e=None):
        state.screen = "resident_input"
        render_screen()

    def go_to_master_admin(e=None):
        refresh_master_data()
        state.screen = "master_admin"
        render_screen()

    def go_to_support_progress(e=None):
        reset_support_progress_form()
        refresh_support_progress_data()
        state.screen = "support_progress"
        render_screen()

    def select_staff(staff: Dict[str, Any]) -> None:
        state.staff = staff
        reset_input_values()
        go_to_dashboard()

    def open_resident_input(resident: Dict[str, Any]) -> None:
        state.resident = resident
        reset_input_values()
        refresh_support_progress_data()
        state.screen = "resident_input"
        render_screen()

    def _validate_save_context() -> tuple[Optional[Dict[str, Any]], Optional[int]]:
        resident = state.resident
        staff_id = state.staff.get("id") if state.staff else None
        if not resident:
            show_dialog(create_alert_dialog("利用者が選択されていません。"))
            return None, None
        if not staff_id:
            show_dialog(create_alert_dialog("職員情報がありません。ログインし直してください。"))
            return None, None
        return resident, int(staff_id)

    def _refresh_after_section_save(message: str) -> None:
        refresh_selected_resident()
        render_screen()
        show_message(message)

    def save_meal_record(e=None) -> None:
        resident, staff_id = _validate_save_context()
        if not resident or not staff_id:
            return
        meal = state.meal
        try:
            meal_parts = [f"時刻:{normalize_time_text(meal.record_time)}", meal.time, f"{meal.intake}/10"]
            if meal.self_cooking:
                meal_parts.append("自炊")
            meal_content = " | ".join(meal_parts)
            recorded_at = build_recorded_at_from_selected_date(state.selected_date, meal.record_time)
            save_daily_category_record(
                resident_id=resident["id"],
                staff_id=staff_id,
                category="食事",
                source_category="食事",
                content=meal_content,
                recorded_at=recorded_at,
            )
        except Exception as exc:
            show_dialog(create_alert_dialog(f"食事の保存に失敗しました。\n{exc}"))
            return
        _refresh_after_section_save(f"保存しました：{resident['name']} さんの食事記録")

    def save_medication_record(e=None) -> None:
        resident, staff_id = _validate_save_context()
        if not resident or not staff_id:
            return
        medication = state.medication
        try:
            meal_timing = normalize_daily_timing_label(state.meal.time)
            medication_status = "完了" if medication.completed else "未"
            medication_content = f"時刻:{normalize_time_text(medication.record_time)} | {meal_timing} | {medication.timing} | {medication_status}"
            recorded_at = build_recorded_at_from_selected_date(state.selected_date, medication.record_time)
            save_daily_category_record(
                resident_id=resident["id"],
                staff_id=staff_id,
                category="服薬",
                source_category="服薬",
                content=medication_content,
                recorded_at=recorded_at,
            )
        except Exception as exc:
            show_dialog(create_alert_dialog(f"服薬の保存に失敗しました。\n{exc}"))
            return
        _refresh_after_section_save(f"保存しました：{resident['name']} さんの服薬記録")

    def save_bathing_record(e=None) -> None:
        resident, staff_id = _validate_save_context()
        if not resident or not staff_id:
            return
        try:
            bath_status = (state.bathing.status or "未実施").strip() or "未実施"
            bath_content = f"時刻:{normalize_time_text(state.bathing.record_time)} | {bath_status}"
            recorded_at = build_recorded_at_from_selected_date(state.selected_date, state.bathing.record_time)
            save_daily_category_record(
                resident_id=resident["id"],
                staff_id=staff_id,
                category="入浴",
                source_category="入浴",
                content=bath_content,
                recorded_at=recorded_at,
            )
        except Exception as exc:
            show_dialog(create_alert_dialog(f"入浴の保存に失敗しました。\n{exc}"))
            return
        _refresh_after_section_save(f"保存しました：{resident['name']} さんの入浴記録")

    def save_patrol_record(e=None) -> None:
        resident, staff_id = _validate_save_context()
        if not resident or not staff_id:
            return
        try:
            patrol_content = f"時刻:{state.patrol.time} | 睡眠:{state.patrol.sleep} | 安全確認:{state.patrol.safety.strip() or '記載なし'}"
            recorded_at = build_recorded_at_from_selected_date(state.selected_date, state.patrol.time)
            save_daily_category_record(
                resident_id=resident["id"],
                staff_id=staff_id,
                category="巡視",
                source_category="巡視",
                content=patrol_content,
                recorded_at=recorded_at,
            )
        except Exception as exc:
            show_dialog(create_alert_dialog(f"巡視の保存に失敗しました。\n{exc}"))
            return
        _refresh_after_section_save(f"保存しました：{resident['name']} さんの巡視記録")

    def save_vital_record(e=None) -> None:
        resident, staff_id = _validate_save_context()
        if not resident or not staff_id:
            return
        temperature = parse_float(state.vital_values.get("temperature", ""))
        systolic_bp = parse_int(state.vital_values.get("systolic", ""))
        diastolic_bp = parse_int(state.vital_values.get("diastolic", ""))
        spo2 = parse_int(state.vital_values.get("spo2", ""))
        try:
            database.create_vital(
                resident_id=resident["id"],
                staff_id=staff_id,
                temperature=temperature,
                systolic_bp=systolic_bp,
                diastolic_bp=diastolic_bp,
                pulse=None,
                spo2=spo2,
                scene=DEFAULT_SCENE,
                note="",
                recorded_at=build_recorded_at_from_selected_date(
                    state.selected_date,
                    state.refs.get("vital_record_time", current_time_hhmm()),
                ),
            )
        except Exception as exc:
            show_dialog(create_alert_dialog(f"バイタルの保存に失敗しました。\n{exc}"))
            return
        abnormal_messages = build_abnormal_messages(temperature, systolic_bp, diastolic_bp, spo2)
        refresh_selected_resident()
        render_screen()
        if abnormal_messages:
            show_dialog(create_alert_dialog("\n".join(abnormal_messages)))
        else:
            show_message(f"保存しました：{resident['name']} さんのバイタル記録")

    def generate_ai_support_progress_draft(e=None) -> None:
        if state.support_progress.ai_busy:
            return
        resident = state.resident
        if not resident:
            show_dialog(create_alert_dialog("利用者が選択されていません。"))
            return
        state.support_progress.ai_busy = True
        state.support_progress.ai_last_error = ""
        render_screen()
        try:
            context = database.get_support_progress_ai_context(resident_id=int(resident["id"]), target_date=state.selected_date)
            draft = ai_service.generate_support_progress_draft(context)
            if not state.support_progress.category.strip():
                state.support_progress.category = "ご様子"
            state.support_progress.content = draft
            state.support_progress.ai_generated = True
            state.support_progress.ai_last_error = ""
            show_message("AI下書きを反映しました。内容を確認してから保存してください。")
        except ai_service.AIServiceError as exc:
            state.support_progress.ai_last_error = build_friendly_ai_error(str(exc))
        except Exception:
            state.support_progress.ai_last_error = "AI下書きの作成に失敗しました。時間をおいて再度お試しください。"
        finally:
            state.support_progress.ai_busy = False
            render_screen()

    def clear_ai_draft(e=None) -> None:
        state.support_progress.content = ""
        state.support_progress.ai_generated = False
        state.support_progress.ai_last_error = ""
        render_screen()

    def is_auto_support_progress_record(item: Optional[Dict[str, Any]]) -> bool:
        if not item:
            return False
        category = (item.get("category") or "").strip()
        content = str(item.get("content") or "")
        return category == "支援経過" or content.startswith("【自動連携:")

    def begin_edit_support_progress(item: Dict[str, Any]) -> None:
        if is_auto_support_progress_record(item):
            show_dialog(create_alert_dialog("自動連携で作成された支援経過は編集できません。元の記録を修正してください。"))
            return
        state.support_progress.edit_id = item["id"]
        state.support_progress.category = (item.get("category") or "ご様子").strip() or "ご様子"
        state.support_progress.content = item.get("content") or ""
        state.support_progress.record_time = extract_record_time(item.get("recorded_at"))
        state.support_progress.ai_generated = False
        render_screen()

    def cancel_support_progress_edit(e=None) -> None:
        reset_support_progress_form()
        render_screen()

    def save_support_progress_record(e=None) -> None:
        resident, staff_id = _validate_save_context()
        if not resident or not staff_id:
            return
        category = (state.support_progress.category or "ご様子").strip() or "ご様子"
        content = (state.support_progress.content or "").strip()
        if not content:
            show_dialog(create_alert_dialog("支援経過の内容を入力してください。"))
            return
        edit_id = state.support_progress.edit_id
        try:
            recorded_at = get_selected_recorded_at(state.support_progress.record_time)
            if edit_id:
                updated = database.update_daily_record(
                    int(edit_id),
                    category=category,
                    content=content,
                    recorded_at=recorded_at,
                )
                if not updated:
                    show_dialog(create_alert_dialog("支援経過の更新に失敗しました。対象データが見つかりませんでした。"))
                    return
                message = f"保存しました：{resident['name']} さんの支援経過を更新"
            else:
                database.create_support_progress_record(
                    resident_id=resident["id"],
                    staff_id=staff_id,
                    category=category,
                    content=content,
                    recorded_at=recorded_at,
                )
                message = f"保存しました：{resident['name']} さんの支援経過"
        except Exception as exc:
            show_dialog(create_alert_dialog(f"支援経過の保存に失敗しました。\n{exc}"))
            return
        reset_support_progress_form()
        refresh_support_progress_data()
        refresh_selected_resident()
        render_screen()
        show_message(message)

    def delete_support_progress_record(item: Dict[str, Any]) -> None:
        record_id = item.get("id")
        if not record_id:
            show_dialog(create_alert_dialog("削除対象の支援経過記録が見つかりません。"))
            return
        try:
            deleted = database.delete_daily_record(int(record_id))
        except Exception as exc:
            show_dialog(create_alert_dialog(f"支援経過記録の削除に失敗しました。\n{exc}"))
            return
        if not deleted:
            show_dialog(create_alert_dialog("支援経過記録の削除に失敗しました。対象データが見つかりませんでした。"))
            return
        if state.support_progress.edit_id == int(record_id):
            reset_support_progress_form()
        refresh_support_progress_data()
        refresh_selected_resident()
        render_screen()
        show_message("支援経過記録を削除しました。")

    def begin_edit_staff(item: Dict[str, Any]) -> None:
        state.master_staff_edit_id = item["id"]
        state.master_staff_form.name = item.get("name") or ""
        state.master_staff_form.password = ""
        state.master_staff_form.role = item.get("role") or ""
        render_screen()

    def begin_edit_resident(item: Dict[str, Any]) -> None:
        state.master_resident_edit_id = item["id"]
        state.master_resident_form.name = item.get("name") or ""
        state.master_resident_form.unit_id = item.get("unit_id")
        state.master_resident_form.diagnosis = item.get("diagnosis") or ""
        state.master_resident_form.care_level = item.get("care_level") or ""
        render_screen()

    def save_staff_master(e=None) -> None:
        name = state.master_staff_form.name.strip()
        password = state.master_staff_form.password.strip()
        role = state.master_staff_form.role.strip()
        if not name or not role:
            show_dialog(create_alert_dialog("職員名と権限を入力してください。"))
            return
        try:
            if state.master_staff_edit_id:
                kwargs: Dict[str, Any] = {"name": name, "role": role}
                if password:
                    kwargs["password"] = password
                database.update_staff(state.master_staff_edit_id, **kwargs)
                if state.staff and state.staff.get("id") == state.master_staff_edit_id:
                    state.staff["name"] = name
                    state.staff["role"] = role
                message = f"保存しました：職員「{name}」を更新"
            else:
                if not password:
                    show_dialog(create_alert_dialog("新規登録時はパスワードが必要です。"))
                    return
                database.create_staff(name=name, password=password, role=role)
                message = f"保存しました：職員「{name}」を登録"
        except Exception as exc:
            show_dialog(create_alert_dialog(f"職員の保存に失敗しました。\n{exc}"))
            return
        refresh_master_data()
        reset_staff_form()
        refresh_dashboard_data()
        render_screen()
        show_message(message)

    def save_resident_master(e=None) -> None:
        name = state.master_resident_form.name.strip()
        diagnosis = state.master_resident_form.diagnosis.strip()
        care_level = state.master_resident_form.care_level.strip()
        unit_id = state.master_resident_form.unit_id
        if not name or not unit_id:
            show_dialog(create_alert_dialog("利用者名と所属ユニットを入力してください。"))
            return
        try:
            if state.master_resident_edit_id:
                database.update_resident(state.master_resident_edit_id, name=name, unit_id=int(unit_id), diagnosis=diagnosis, care_level=care_level)
                message = f"保存しました：利用者「{name}」を更新"
            else:
                database.create_resident(name=name, unit_id=int(unit_id), diagnosis=diagnosis, care_level=care_level)
                message = f"保存しました：利用者「{name}」を登録"
        except Exception as exc:
            show_dialog(create_alert_dialog(f"利用者の保存に失敗しました。\n{exc}"))
            return
        refresh_master_data()
        reset_resident_form()
        refresh_dashboard_data()
        refresh_selected_resident()
        render_screen()
        show_message(message)

    def request_delete_staff(item: Dict[str, Any]) -> None:
        if state.staff and item.get("id") == state.staff.get("id"):
            show_dialog(create_alert_dialog("ログイン中の職員は削除できません。"))
            return
        try:
            deleted = database.delete_staff(item["id"])
        except Exception as exc:
            show_dialog(create_alert_dialog(f"職員の削除に失敗しました。\n{exc}"))
            return
        if not deleted:
            show_dialog(create_alert_dialog("職員の削除に失敗しました。対象データが見つかりませんでした。"))
            return
        refresh_master_data()
        if state.master_staff_edit_id == item["id"]:
            reset_staff_form()
        render_screen()
        show_message(f"職員「{item.get('name') or '-'}」を削除しました。")

    def request_delete_resident(item: Dict[str, Any]) -> None:
        try:
            deleted = database.delete_resident(item["id"])
        except Exception as exc:
            show_dialog(create_alert_dialog(f"利用者の削除に失敗しました。\n{exc}"))
            return
        if not deleted:
            show_dialog(create_alert_dialog("利用者の削除に失敗しました。対象データが見つかりませんでした。"))
            return
        if state.resident and state.resident.get("id") == item["id"]:
            state.resident = None
        refresh_master_data()
        refresh_dashboard_data()
        if state.master_resident_edit_id == item["id"]:
            reset_resident_form()
        render_screen()
        show_message(f"利用者「{item.get('name') or '-'}」を削除しました。")

    def build_date_switcher() -> ft.Container:
        def nav_button(label: str, on_click: Any) -> ft.Control:
            return ft.ElevatedButton(
                content=ft.Text(label, size=FONT_SIZE_SM, weight=ft.FontWeight.W_700),
                on_click=on_click,
                height=42,
                style=ft.ButtonStyle(
                    bgcolor=COLOR_WHITE,
                    color=APP_WARNING,
                    side=ft.BorderSide(1, "#FDBA74"),
                    elevation=0,
                    shape=ft.RoundedRectangleBorder(radius=12),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=0),
                ),
            )

        return ft.Container(
            bgcolor="#FFFDFC",
            border_radius=RADIUS_MD,
            border=ft.Border.all(1, "#FDE7C3"),
            padding=ft.Padding.all(SPACE_LG),
            content=ft.Column(
                controls=[
                    ft.Container(
                        height=42,
                        bgcolor="#FFF8EF",
                        border=ft.Border.all(1, "#FDBA74"),
                        border_radius=16,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(
                            format_selected_date(state.selected_date),
                            size=FONT_SIZE_MD,
                            weight=ft.FontWeight.W_700,
                            color=APP_WARNING,
                        ),
                    ),
                    ft.Row(
                        controls=[
                            nav_button("前日", move_to_prev_date),
                            nav_button("本日", move_to_today),
                            nav_button("翌日", move_to_next_date),
                        ],
                        spacing=SPACE_SM,
                        wrap=True,
                    ),
                ],
                spacing=SPACE_SM,
            ),
        )

    def build_info_tile(title: str, value: str, subtle: bool = False) -> ft.Control:
        return ft.Container(
            bgcolor="#F6FBFA" if subtle else "#FFFEFC",
            border=ft.Border.all(1, APP_BORDER),
            border_radius=18,
            padding=16,
            content=ft.Column(
                controls=[ft.Text(title, size=FONT_SIZE_SM, color=APP_TEXT_MUTED), ft.Text(value, size=FONT_SIZE_LG, weight=ft.FontWeight.W_900, color=APP_NAVY)],
                spacing=6,
            ),
        )

    def build_resident_summary_card(resident: Dict[str, Any]) -> ft.Control:
        daily_status = database.get_resident_daily_status(
            resident["id"],
            target_date=state.selected_date.strftime("%Y-%m-%d"),
        )
        meal_labels = [item.get("label") or "未記録" for item in daily_status.get("meal", {}).values()]
        med_labels = [item.get("label") or "未記録" for item in daily_status.get("medication", {}).values()]
        bath_label = daily_status.get("bath", {}).get("label") or "未記録"
        patrol_label = daily_status.get("patrol", {}).get("label") or "未記録"
        resident_name = resident.get("name", "利用者")

        return build_card_column(
            [
                ft.Text(f"{resident_name} さんの当日サマリー", size=FONT_SIZE_LG + 2, weight=ft.FontWeight.W_900, color=APP_NAVY),
                ft.Text("本日の記録状況を確認できます。", size=FONT_SIZE_SM, color=APP_TEXT_MUTED),
                ft.Text(f"食事: {' / '.join(meal_labels) if meal_labels else '未記録'}", size=FONT_SIZE_MD, color=APP_NAVY),
                ft.Text(f"服薬: {' / '.join(med_labels) if med_labels else '未記録'}", size=FONT_SIZE_MD, color=APP_NAVY),
                ft.Text(f"入浴: {bath_label}", size=FONT_SIZE_MD, color=APP_NAVY),
                ft.Text(f"夜間巡視: {patrol_label}", size=FONT_SIZE_MD, color=APP_NAVY),
            ]
        )

    def build_today_summary_card(resident: Dict[str, Any]) -> ft.Control:
        rows = database.list_support_progress_records(
            resident_id=resident["id"],
            date_from=f"{state.selected_date.strftime('%Y-%m-%d')} 00:00:00",
            date_to=f"{state.selected_date.strftime('%Y-%m-%d')} 23:59:59",
            limit=5,
        )
        controls: List[ft.Control] = [ft.Text("本日の最新記録", size=FONT_SIZE_LG, weight=ft.FontWeight.W_900, color=APP_NAVY)]
        if not rows:
            controls.append(ft.Text("まだ記録はありません。必要なカードから順に保存してください。", color=APP_TEXT_MUTED))
        else:
            for row in rows[:5]:
                controls.append(
                    ft.Container(
                        bgcolor="#F8FCFB",
                        border=ft.Border.all(1, APP_BORDER),
                        border_radius=14,
                        padding=12,
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text(row.get("category") or "-", weight=ft.FontWeight.W_800, color=APP_TIFFANY_DEEP),
                                        ft.Text(str(row.get("recorded_at") or ""), size=FONT_SIZE_SM, color=APP_TEXT_MUTED),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Text(str(row.get("content") or ""), size=FONT_SIZE_SM, color=COLOR_BLACK),
                            ],
                            spacing=6,
                        ),
                    )
                )
        return build_card_column(controls)

    def build_ai_support_draft_card() -> ft.Control:
        status = ai_service.get_ai_status()
        ai_available = status.get("available") == "true"
        sp = state.support_progress
        controls: List[ft.Control] = [
            ft.Row(
                controls=[
                    ft.Container(width=48, height=48, border_radius=24, bgcolor="#E7FBF8", border=ft.Border.all(1, "#CDEDEA"), alignment=ft.Alignment(0, 0), content=ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, color=APP_TIFFANY_DEEP, size=24)),
                    ft.Column(
                        controls=[
                            ft.Text("AI支援経過 下書き", size=FONT_SIZE_LG + 2, weight=ft.FontWeight.W_900, color=APP_NAVY),
                            ft.Text("当日の入力済み記録から支援経過の本文を自動で下書きします。", size=FONT_SIZE_SM, color=APP_TEXT_MUTED),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        ]
        if sp.ai_busy:
            controls.append(build_banner("AIが下書きを生成中です…", "info"))
            controls.append(ft.ProgressBar())
        elif sp.ai_generated:
            controls.append(build_banner("下書きができました。内容を確認して問題なければ保存してください。", "success"))
        elif sp.ai_last_error:
            controls.append(build_banner(sp.ai_last_error, "error"))
        else:
            label = status.get("label") or ("利用可能" if ai_available else "未設定")
            message = status.get("message") or ""
            controls.append(build_banner(f"AI状態: {label} / {message}", "warning" if not ai_available else "info"))
        controls.append(
            ft.Row(
                controls=[
                    build_filled_button("AIで下書き", generate_ai_support_progress_draft, disabled=(not ai_available) or sp.ai_busy, icon=ft.Icons.AUTO_AWESOME_ROUNDED),
                    build_outline_button("下書きをクリア", clear_ai_draft, icon=ft.Icons.CLEANING_SERVICES_OUTLINED),
                ],
                spacing=SPACE_SM,
                wrap=True,
            )
        )
        return build_card_column(controls)

    def build_work_section(title: str, control: ft.Control, col: int = 6) -> ft.Control:
        return ft.Container(col={"xs": 12, "md": col}, content=build_card_column([control], title))

    def build_staff_select_screen() -> ft.Control:
        staff_list = database.list_staff()
        hero = create_app_brand_hero(
            title="福祉記録を、もっと軽やかに。",
            subtitle="AIアシスト付きのケア記録ワークスペース",
            description="日々の記録入力、支援経過、申し送りの下書きまでを、ひとつの画面体験として整えた福祉記録アプリです。",
            badges=["記録を最短導線で開始", "AI下書き対応", "現場向けの見やすいUI"],
        )

        staff_cards: List[ft.Control] = []
        for staff in staff_list:
            staff_cards.append(
                ft.Container(
                    col={"xs": 12, "md": 6},
                    content=create_staff_login_card(
                        staff["name"],
                        staff.get("role") or "スタッフ",
                        on_click=lambda e, item=staff: select_staff(item),
                    ),
                )
            )

        if not staff_cards:
            staff_cards.append(
                ft.Container(
                    col={"xs": 12},
                    content=build_card_column([ft.Text("職員データが見つかりません。", size=FONT_SIZE_MD, color=COLOR_GRAY_TEXT)]),
                )
            )

        overview = build_card_column(
            [
                ft.Text("Quick Start", size=FONT_SIZE_SM, weight=ft.FontWeight.W_700, color=APP_TEXT_MUTED),
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(col={"xs": 12, "md": 4}, content=build_info_tile("登録職員", f"{len(staff_list)} 名")),
                        ft.Container(col={"xs": 12, "md": 4}, content=build_info_tile("現在の状態", "職員を選択してください", subtle=True)),
                        ft.Container(col={"xs": 12, "md": 4}, content=build_info_tile("利用モード", "Care AI Note", subtle=True)),
                    ],
                    columns=12,
                    run_spacing=SPACE_SM,
                    spacing=SPACE_SM,
                ),
            ]
        )

        return build_screen_shell(
            hero,
            [
                overview,
                build_card_column(
                    [
                        ft.Row(
                            controls=[
                                ft.Text("ログインする職員を選択", size=FONT_SIZE_XL, weight=ft.FontWeight.W_900, color=APP_NAVY),
                                ft.Text("記録作業を始める担当者を選択してください。", size=FONT_SIZE_SM, color=APP_TEXT_MUTED),
                            ],
                            wrap=True,
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.ResponsiveRow(
                            controls=staff_cards,
                            columns=12,
                            run_spacing=SPACE_MD,
                            spacing=SPACE_MD,
                        ),
                    ]
                ),
            ],
        )

    def build_simple_dashboard_item(resident: Dict[str, Any]) -> ft.Control:
        return create_resident_dashboard_card(
            resident,
            on_click=lambda e, item=resident: open_resident_input(item),
            daily_status=resident.get("daily_status"),
        )

    def build_dashboard_screen() -> ft.Control:
        refresh_dashboard_data()
        recorded_count = sum(1 for resident in state.dashboard_residents if resident.get("latest_recorded_at"))
        items: List[ft.Control] = [
            ft.Text(f"利用者 {len(state.dashboard_residents)} 名", size=FONT_SIZE_LG, weight=ft.FontWeight.W_900, color=APP_NAVY),
            ft.Text("一覧から利用者を選ぶと、記録入力に進みます。", size=FONT_SIZE_SM, color=APP_TEXT_MUTED),
        ]
        if state.dashboard_residents:
            for resident in state.dashboard_residents:
                items.append(build_simple_dashboard_item(resident))
        else:
            items.append(ft.Text("利用者データが見つかりません。", size=FONT_SIZE_MD, color=COLOR_GRAY_TEXT))

        return build_screen_shell(
            create_shared_header(
                title="利用者一覧ダッシュボード",
                subtitle="その日の状態を見ながら、すぐに記録入力へ入れます。",
                staff_text=current_staff_text(),
                back_label="職員選択へ戻る",
                on_back=go_to_staff_select,
                actions=[create_resident_button("マスター管理", False, on_click=go_to_master_admin)],
            ),
            [
                build_card_column(
                    [
                        ft.ResponsiveRow(
                            controls=[
                                ft.Container(col={"xs": 12, "md": 3}, content=build_info_tile("表示日", format_selected_date(state.selected_date))),
                                ft.Container(col={"xs": 12, "md": 3}, content=build_info_tile("担当スタッフ", state.staff.get("name", "未選択") if state.staff else "未選択", subtle=True)),
                                ft.Container(col={"xs": 12, "md": 3}, content=build_info_tile("利用者数", f"{len(state.dashboard_residents)} 名")),
                                ft.Container(col={"xs": 12, "md": 3}, content=build_info_tile("記録あり", f"{recorded_count} 名", subtle=True)),
                            ],
                            columns=12,
                            run_spacing=SPACE_SM,
                            spacing=SPACE_SM,
                        )
                    ]
                ),
                build_date_switcher(),
                build_card_column(items),
            ],
        )

    def build_resident_input_screen() -> ft.Control:
        resident = state.resident or {}
        temperature_control = create_vital_input_field(
            "体温",
            state.vital_values.get("temperature", DEFAULT_VITAL_VALUES["temperature"]),
            lambda value: state.vital_values.__setitem__("temperature", value),
        )
        systolic_control = create_vital_input_field(
            "最高血圧",
            state.vital_values.get("systolic", DEFAULT_VITAL_VALUES["systolic"]),
            lambda value: state.vital_values.__setitem__("systolic", value),
        )
        diastolic_control = create_vital_input_field(
            "最低血圧",
            state.vital_values.get("diastolic", DEFAULT_VITAL_VALUES["diastolic"]),
            lambda value: state.vital_values.__setitem__("diastolic", value),
        )
        spo2_control = create_vital_input_field(
            "SPO2",
            state.vital_values.get("spo2", DEFAULT_VITAL_VALUES["spo2"]),
            lambda value: state.vital_values.__setitem__("spo2", value),
        )
        vital_record_time = state.refs.get("vital_record_time", current_time_hhmm())
        state.refs["vital_record_time"] = vital_record_time

        vital_section = create_vital_panel(
            temperature_control=temperature_control,
            systolic_control=systolic_control,
            diastolic_control=diastolic_control,
            spo2_control=spo2_control,
            record_time=vital_record_time,
            on_record_time_change=lambda value: state.refs.__setitem__("vital_record_time", value),
            on_save=save_vital_record,
        )
        meal_panel = create_meal_panel(
            selected_time=state.meal.time,
            intake_value=state.meal.intake,
            is_self_cooking=state.meal.self_cooking,
            record_time=state.meal.record_time,
            on_time_select=lambda value: setattr(state.meal, "time", value) or render_screen(),
            on_intake_select=lambda value: setattr(state.meal, "intake", value) or render_screen(),
            on_self_cooking_change=lambda value: setattr(state.meal, "self_cooking", value) or page.update(),
            on_record_time_change=lambda value: setattr(state.meal, "record_time", value),
            on_save=save_meal_record,
        )
        medication_panel = create_medication_panel(
            selected_timing=state.medication.timing,
            is_completed=state.medication.completed,
            record_time=state.medication.record_time,
            on_timing_select=lambda value: setattr(state.medication, "timing", value) or render_screen(),
            on_completed_change=lambda value: setattr(state.medication, "completed", value) or page.update(),
            on_record_time_change=lambda value: setattr(state.medication, "record_time", value),
            on_save=save_medication_record,
        )
        bathing_panel = create_bathing_input_panel(
            selected_status=state.bathing.status,
            record_time=state.bathing.record_time,
            on_status_select=lambda value: setattr(state.bathing, "status", value) or render_screen(),
            on_record_time_change=lambda value: setattr(state.bathing, "record_time", value),
            on_save=save_bathing_record,
        )
        patrol_panel = create_patrol_input_panel(
            selected_time=state.patrol.time,
            selected_sleep=state.patrol.sleep,
            on_time_select=lambda value: setattr(state.patrol, "time", value),
            on_sleep_select=lambda value: setattr(state.patrol, "sleep", value) or render_screen(),
            on_safety_change=lambda value: setattr(state.patrol, "safety", value),
            on_save=save_patrol_record,
        )
        patrol_panel.data["safety_field"].value = state.patrol.safety

        header = create_shared_header(
            title=f"{resident.get('name', '利用者')} の記録入力",
            subtitle="利用者情報と当日の状況を確認しながら入力できます。",
            staff_text=current_staff_text(),
            back_label="一覧へ戻る",
            on_back=go_to_dashboard,
            meta_items=resident_meta_items(resident),
            actions=[create_resident_button("支援経過", False, on_click=go_to_support_progress)],
        )

        return build_screen_shell(
            header,
            [
                build_date_switcher(),
                build_resident_summary_card(resident),
                build_card_column([vital_section], "バイタル"),
                build_card_column([meal_panel], "食事"),
                build_card_column([medication_panel], "服薬"),
                build_card_column([bathing_panel], "入浴"),
                build_card_column([patrol_panel], "夜間巡視"),
                build_card_column([build_ai_support_draft_card()], "AI補助"),
                build_today_summary_card(resident),
            ],
        )

    def build_support_progress_screen() -> ft.Control:
        resident = state.resident or {}
        refresh_support_progress_data()
        panel = create_support_progress_panel(
            selected_category=state.support_progress.category or "ご様子",
            note_text=state.support_progress.content or "",
            categories=SUPPORT_PROGRESS_OPTIONS,
            record_time=state.support_progress.record_time or current_time_hhmm(),
            recorded_at_text=f"{format_selected_date(state.selected_date)} {state.support_progress.record_time or current_time_hhmm()}",
            staff_name=state.staff.get("name") if state.staff else "職員未選択",
            on_category_select=lambda value: setattr(state.support_progress, "category", value) or render_screen(),
            on_text_change=lambda value: setattr(state.support_progress, "content", value),
            on_record_time_change=lambda value: setattr(state.support_progress, "record_time", value) or render_screen(),
            on_save=save_support_progress_record,
            is_editing=bool(state.support_progress.edit_id),
            on_cancel=cancel_support_progress_edit,
        )
        record_controls = [
            create_support_progress_record_card(
                record,
                on_edit=(None if is_auto_support_progress_record(record) else (lambda e, item=record: begin_edit_support_progress(item))),
                on_delete=lambda e, item=record: delete_support_progress_record(item),
            )
            for record in state.support_progress_records
        ]
        if not record_controls:
            record_controls = [ft.Text("選択日の支援経過記録はまだありません。", size=FONT_SIZE_MD, color=COLOR_GRAY_TEXT)]
        compose_controls = [build_ai_support_draft_card(), panel]
        if state.support_progress.ai_generated:
            compose_controls.insert(1, build_banner("下書き作成後は、文章を確認してから保存してください。", "success"))
        records_section = build_card_column(
            [
                ft.Text(f"{format_selected_date(state.selected_date)} の記録一覧", size=FONT_SIZE_LG, weight=ft.FontWeight.W_900, color=APP_NAVY),
                ft.Text("AI自動連携の記録は編集不可です。手入力した支援経過のみ編集できます。", size=FONT_SIZE_SM, color=APP_TEXT_MUTED),
                ft.Column(controls=record_controls, spacing=SPACE_SM),
            ]
        )
        compose_section = build_card_column(compose_controls)
        return build_screen_shell(
            create_shared_header(
                title=f"{resident.get('name', '利用者')} の支援経過記録",
                subtitle="AI下書き→確認→保存の流れで記録できます。",
                staff_text=current_staff_text(),
                back_label="記録入力へ戻る",
                on_back=go_to_resident_input,
                meta_items=resident_meta_items(resident),
            ),
            [build_date_switcher(), compose_section, records_section],
        )

    def build_staff_list_item(item: Dict[str, Any]) -> ft.Container:
        is_editing = state.master_staff_edit_id == item.get("id")
        return ft.Container(
            bgcolor="#ECFDF5" if is_editing else "#F8FAFC",
            border=ft.Border.all(1, "#CCFBF1" if is_editing else "#E5E7EB"),
            border_radius=14,
            padding=ft.Padding.all(SPACE_MD),
            content=ft.Row(
                controls=[
                    ft.Column(controls=[ft.Text(item.get("name") or "-", size=FONT_SIZE_MD, weight=ft.FontWeight.W_700), ft.Text(f"権限: {item.get('role') or '-'}", size=FONT_SIZE_SM, color=COLOR_GRAY_TEXT)], spacing=2, expand=True),
                    ft.TextButton("編集", on_click=lambda e, current=item: begin_edit_staff(current), style=ft.ButtonStyle(color=COLOR_TEAL)),
                    ft.TextButton("削除", on_click=lambda e, current=item: request_delete_staff(current), style=ft.ButtonStyle(color="#B91C1C")),
                ],
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def build_resident_list_item(item: Dict[str, Any]) -> ft.Container:
        is_editing = state.master_resident_edit_id == item.get("id")
        meta_lines = [f"所属ユニット: {item.get('unit_name') or '-'}", f"病症: {(item.get('diagnosis') or '').strip() or '未登録'}", f"区分: {(item.get('care_level') or '').strip() or '未登録'}"]
        return ft.Container(
            bgcolor="#EFF6FF" if is_editing else "#F8FAFC",
            border=ft.Border.all(1, "#DBEAFE" if is_editing else "#E5E7EB"),
            border_radius=14,
            padding=ft.Padding.all(SPACE_MD),
            content=ft.Row(
                controls=[
                    ft.Column(controls=[ft.Text(item.get("name") or "-", size=FONT_SIZE_MD, weight=ft.FontWeight.W_700)] + [ft.Text(line, size=FONT_SIZE_SM, color=COLOR_GRAY_TEXT) for line in meta_lines], spacing=2, expand=True),
                    ft.TextButton("編集", on_click=lambda e, current=item: begin_edit_resident(current), style=ft.ButtonStyle(color=COLOR_TEAL)),
                    ft.TextButton("削除", on_click=lambda e, current=item: request_delete_resident(current), style=ft.ButtonStyle(color="#B91C1C")),
                ],
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def build_staff_master_panel() -> ft.Control:
        form = state.master_staff_form
        controls = [
            ft.TextField(label="職員名", value=form.name, border_color="#E5E7EB", on_change=lambda e: setattr(state.master_staff_form, "name", e.control.value or "")),
            ft.TextField(label="パスワード", value=form.password, password=True, can_reveal_password=True, border_color="#E5E7EB", hint_text="新規登録時は必須 / 編集時は空欄で変更なし", on_change=lambda e: setattr(state.master_staff_form, "password", e.control.value or "")),
            ft.TextField(label="権限", value=form.role, border_color="#E5E7EB", on_change=lambda e: setattr(state.master_staff_form, "role", e.control.value or "")),
            ft.Row(controls=[build_filled_button("更新する" if state.master_staff_edit_id else "登録する", save_staff_master, icon=ft.Icons.SAVE_OUTLINED), build_outline_button("入力をクリア", lambda e: (reset_staff_form(), render_screen()), icon=ft.Icons.CLOSE)], spacing=SPACE_SM, wrap=True),
        ]
        items = [build_staff_list_item(item) for item in state.master_staff_list]
        return ft.Column(controls=[build_card_column([ft.Text("職員の新規登録・編集・削除を行います。", size=FONT_SIZE_SM, color=APP_TEXT_MUTED)] + controls, "職員管理"), build_card_column(items if items else [ft.Text("データがありません。", color=COLOR_GRAY_TEXT)], "登録済み職員")], spacing=SPACE_MD)

    def build_resident_master_panel() -> ft.Control:
        form = state.master_resident_form
        unit_options = [ft.DropdownOption(key=str(unit["id"]), text=unit.get("unit_name") or "-") for unit in state.master_units]
        unit_dropdown = ft.Dropdown(
            label="所属ユニット",
            value=str(form.unit_id) if form.unit_id is not None else None,
            options=unit_options,
            border_color="#E5E7EB",
        )
        try:
            unit_dropdown.on_change = lambda e: setattr(
                state.master_resident_form,
                "unit_id",
                int(e.control.value) if e.control.value else None,
            )
        except Exception:
            try:
                unit_dropdown.on_select = lambda e: setattr(
                    state.master_resident_form,
                    "unit_id",
                    int(e.control.value) if e.control.value else None,
                )
            except Exception:
                pass

        controls = [
            ft.TextField(label="利用者名", value=form.name, border_color="#E5E7EB", on_change=lambda e: setattr(state.master_resident_form, "name", e.control.value or "")),
            unit_dropdown,
            ft.TextField(label="病症", value=form.diagnosis, multiline=True, min_lines=2, border_color="#E5E7EB", on_change=lambda e: setattr(state.master_resident_form, "diagnosis", e.control.value or "")),
            ft.TextField(label="区分", value=form.care_level, border_color="#E5E7EB", hint_text="例: 区分3", on_change=lambda e: setattr(state.master_resident_form, "care_level", e.control.value or "")),
            ft.Row(controls=[build_filled_button("更新する" if state.master_resident_edit_id else "登録する", save_resident_master, icon=ft.Icons.SAVE_OUTLINED), build_outline_button("入力をクリア", lambda e: (reset_resident_form(), render_screen()), icon=ft.Icons.CLOSE)], spacing=SPACE_SM, wrap=True),
        ]
        items = [build_resident_list_item(item) for item in state.master_resident_list]
        return ft.Column(controls=[build_card_column([ft.Text("利用者の所属ユニット・病症・区分を登録・編集できます。", size=FONT_SIZE_SM, color=APP_TEXT_MUTED)] + controls, "利用者管理"), build_card_column(items if items else [ft.Text("データがありません。", color=COLOR_GRAY_TEXT)], "登録済み利用者")], spacing=SPACE_MD)

    def build_master_admin_screen() -> ft.Control:
        refresh_master_data()
        current_panel = build_staff_master_panel() if state.master_tab_index == 0 else build_resident_master_panel()
        tab_switcher = ft.Container(
            bgcolor=COLOR_WHITE,
            border_radius=RADIUS_MD,
            padding=ft.Padding.all(SPACE_MD),
            border=ft.Border.all(1, "#E5E7EB"),
            content=ft.Row(
                controls=[
                    ft.Container(expand=True, height=44, bgcolor=COLOR_TEAL if state.master_tab_index == 0 else COLOR_WHITE, border=ft.Border.all(1, COLOR_TEAL), border_radius=12, alignment=ft.Alignment(0, 0), ink=True, on_click=lambda e: setattr(state, "master_tab_index", 0) or render_screen(), content=ft.Text("職員管理", size=FONT_SIZE_SM, weight=ft.FontWeight.W_700, color=COLOR_WHITE if state.master_tab_index == 0 else COLOR_TEAL)),
                    ft.Container(expand=True, height=44, bgcolor=COLOR_TEAL if state.master_tab_index == 1 else COLOR_WHITE, border=ft.Border.all(1, COLOR_TEAL), border_radius=12, alignment=ft.Alignment(0, 0), ink=True, on_click=lambda e: setattr(state, "master_tab_index", 1) or render_screen(), content=ft.Text("利用者管理", size=FONT_SIZE_SM, weight=ft.FontWeight.W_700, color=COLOR_WHITE if state.master_tab_index == 1 else COLOR_TEAL)),
                ],
                spacing=SPACE_SM,
            ),
        )
        return build_screen_shell(create_shared_header(title="マスター管理", subtitle="職員マスタ・利用者マスタを管理します。", staff_text=current_staff_text(), back_label="ダッシュボードへ戻る", on_back=go_to_dashboard), [tab_switcher, current_panel])

    def go_back_by_swipe() -> None:
        if state.screen == "support_progress":
            go_to_resident_input()
        elif state.screen == "resident_input":
            go_to_dashboard()
        elif state.screen == "master_admin":
            go_to_dashboard()
        elif state.screen == "dashboard":
            go_to_staff_select()

    def with_swipe_back(content: ft.Control) -> ft.Control:
        swipe = {"dx": 0.0}

        def on_swipe_update(e: ft.DragUpdateEvent) -> None:
            swipe["dx"] += float(e.primary_delta or 0)

        def on_swipe_end(e: ft.DragEndEvent) -> None:
            should_go_back = swipe["dx"] < -90 or float(e.primary_velocity or 0) < -450
            swipe["dx"] = 0.0
            if should_go_back:
                go_back_by_swipe()

        return ft.GestureDetector(
            content=content,
            drag_interval=40,
            on_horizontal_drag_update=on_swipe_update,
            on_horizontal_drag_end=on_swipe_end,
        )

    def render_screen() -> None:
        if state.screen == "staff_select":
            screen = build_staff_select_screen()
        elif state.screen == "dashboard":
            screen = build_dashboard_screen()
        elif state.screen == "master_admin":
            screen = build_master_admin_screen()
        elif state.screen == "support_progress":
            screen = build_support_progress_screen()
        else:
            screen = build_resident_input_screen()
        root.content = with_swipe_back(screen)
        page.update()

    refresh_master_data()
    reset_input_values()
    page.add(root)
    render_screen()


if __name__ == "__main__":
    ft.run(main)
