
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Optional


DEFAULT_VITAL_VALUES = {
    "temperature": "36.5",
    "systolic": "120",
    "diastolic": "80",
    "spo2": "98",
}


@dataclass
class MealState:
    time: str = "朝"
    intake: int = 10
    self_cooking: bool = False
    record_time: str = ""


@dataclass
class MedicationState:
    timing: str = "食後"
    completed: bool = True
    record_time: str = ""


@dataclass
class BathingState:
    status: str = "未実施"
    record_time: str = ""


@dataclass
class PatrolState:
    time: str = "22:00"
    sleep: str = "眠れている"
    safety: str = ""


@dataclass
class SupportProgressState:
    category: str = "ご様子"
    content: str = ""
    record_time: str = ""
    edit_id: Optional[int] = None
    ai_busy: bool = False
    ai_last_error: str = ""
    ai_generated: bool = False


@dataclass
class MasterStaffForm:
    name: str = ""
    password: str = ""
    role: str = "一般"


@dataclass
class MasterResidentForm:
    name: str = ""
    unit_id: Optional[int] = None
    diagnosis: str = ""
    care_level: str = ""


@dataclass
class AppState:
    screen: str = "staff_select"
    selected_date: date = field(default_factory=date.today)
    staff: Optional[Dict[str, Any]] = None
    resident: Optional[Dict[str, Any]] = None
    dashboard_residents: list[dict] = field(default_factory=list)

    vital_values: Dict[str, str] = field(default_factory=lambda: DEFAULT_VITAL_VALUES.copy())

    meal: MealState = field(default_factory=MealState)
    medication: MedicationState = field(default_factory=MedicationState)
    bathing: BathingState = field(default_factory=BathingState)
    patrol: PatrolState = field(default_factory=PatrolState)
    support_progress: SupportProgressState = field(default_factory=SupportProgressState)

    master_tab_index: int = 0
    master_staff_form: MasterStaffForm = field(default_factory=MasterStaffForm)
    master_staff_edit_id: Optional[int] = None
    master_staff_list: list[dict] = field(default_factory=list)
    master_resident_form: MasterResidentForm = field(default_factory=MasterResidentForm)
    master_resident_edit_id: Optional[int] = None
    master_resident_list: list[dict] = field(default_factory=list)
    master_units: list[dict] = field(default_factory=list)
    support_progress_records: list[dict] = field(default_factory=list)

    refs: Dict[str, Any] = field(default_factory=dict)
