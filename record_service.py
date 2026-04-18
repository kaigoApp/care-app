
from __future__ import annotations

import database


def save_daily_category_record(
    *,
    resident_id: int,
    staff_id: int,
    category: str,
    source_category: str,
    content: str,
    recorded_at: str,
) -> None:
    database.create_daily_record(
        resident_id=resident_id,
        staff_id=staff_id,
        category=category,
        content=content,
        recorded_at=recorded_at,
    )
    database.create_auto_support_progress_record(
        resident_id=resident_id,
        staff_id=staff_id,
        source_category=source_category,
        content=content,
        recorded_at=recorded_at,
    )
