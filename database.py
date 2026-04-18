from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence


DB_CANDIDATE_NAMES = (
    "care_records.db",
    "care_app.db",
    "care_records.sqlite3",
    "care_app.sqlite3",
    "records.db",
    "database.db",
)


def _looks_like_sqlite_file(path: str) -> bool:
    if not path or not os.path.isfile(path):
        return False
    try:
        with open(path, "rb") as fp:
            header = fp.read(16)
        return header.startswith(b"SQLite format 3")
    except OSError:
        return False


def _inspect_existing_db(path: str) -> Optional[Dict[str, Any]]:
    if not _looks_like_sqlite_file(path):
        return None

    try:
        conn = sqlite3.connect(path)
        try:
            table_rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
            tables = {row[0] for row in table_rows}
            resident_count = 0
            staff_count = 0
            unit_count = 0
            if "residents" in tables:
                resident_count = int(conn.execute("SELECT COUNT(*) FROM residents WHERE COALESCE(is_deleted, 0) = 0").fetchone()[0] or 0)
            if "staff" in tables:
                staff_count = int(conn.execute("SELECT COUNT(*) FROM staff WHERE COALESCE(is_deleted, 0) = 0").fetchone()[0] or 0)
            if "units" in tables:
                unit_count = int(conn.execute("SELECT COUNT(*) FROM units").fetchone()[0] or 0)
            return {
                "path": path,
                "tables": tables,
                "resident_count": resident_count,
                "staff_count": staff_count,
                "unit_count": unit_count,
                "size": os.path.getsize(path),
            }
        finally:
            conn.close()
    except sqlite3.Error:
        return None


def resolve_db_path(preferred_path: Optional[str] = None) -> str:
    default_path = preferred_path or os.path.join(os.path.dirname(__file__), "care_records.db")

    app_storage_path = os.environ.get("FLET_APP_STORAGE_DATA", "").strip()
    if app_storage_path:
        try:
            os.makedirs(app_storage_path, exist_ok=True)
            return os.path.join(app_storage_path, os.path.basename(default_path))
        except OSError:
            pass

    env_path = os.environ.get("CARE_APP_DB_PATH", "").strip()
    if env_path:
        if os.path.isdir(env_path):
            env_path = os.path.join(env_path, os.path.basename(default_path))
        if _looks_like_sqlite_file(env_path):
            return env_path

    candidate_paths: List[str] = []
    seen_dirs: set[str] = set()
    for base_dir in (
        os.getcwd(),
        os.path.dirname(os.path.abspath(__file__)),
        os.path.dirname(os.path.abspath(default_path)),
    ):
        base_dir = os.path.abspath(base_dir)
        if not os.path.isdir(base_dir) or base_dir in seen_dirs:
            continue
        seen_dirs.add(base_dir)

        for name in DB_CANDIDATE_NAMES:
            candidate_paths.append(os.path.join(base_dir, name))

        try:
            for name in os.listdir(base_dir):
                lower = name.lower()
                if lower.endswith((".db", ".sqlite", ".sqlite3")) and not lower.endswith(("-wal", "-shm", "-journal")):
                    candidate_paths.append(os.path.join(base_dir, name))
        except OSError:
            continue

    best_info: Optional[Dict[str, Any]] = None
    for path in candidate_paths:
        info = _inspect_existing_db(path)
        if info is None:
            continue
        if best_info is None:
            best_info = info
            continue
        current_key = (
            info["resident_count"],
            info["staff_count"],
            info["unit_count"],
            info["size"],
        )
        best_key = (
            best_info["resident_count"],
            best_info["staff_count"],
            best_info["unit_count"],
            best_info["size"],
        )
        if current_key > best_key:
            best_info = info

    if best_info is not None:
        return best_info["path"]

    return default_path


DEFAULT_DB_PATH = resolve_db_path(os.path.join(os.path.dirname(__file__), "care_records.db"))


ALLOWED_VITAL_SCENES = {"朝", "入浴前"}
SUPPORT_PROGRESS_AUTO_CATEGORY = "支援経過"
SUPPORT_PROGRESS_CATEGORIES = ("ご様子", "通所", "受診", "訪問看護", "移動支援", "外出", "外泊")
ALLOWED_RECORD_CATEGORIES = {"食事", "服薬", "入浴", "巡視", "その他", SUPPORT_PROGRESS_AUTO_CATEGORY, *SUPPORT_PROGRESS_CATEGORIES}
ALLOWED_CARE_PLAN_STATUSES = {"draft", "pending", "approved"}
PASSWORD_HASH_ITERATIONS = 100_000


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    return dict(row) if row is not None else None


def _rows_to_dicts(rows: Sequence[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(row) for row in rows]


def _validate_choice(value: str, allowed: set[str], field_name: str) -> None:
    if value not in allowed:
        raise ValueError(f"{field_name} は次のいずれかで指定してください: {', '.join(sorted(allowed))}")


def _require_staff_id(staff_id: Optional[int]) -> int:
    if staff_id is None:
        raise ValueError("staff_id が未設定のため保存できません。職員を選択し直してください。")
    return int(staff_id)


def _hash_password(password: str) -> str:
    if not password:
        raise ValueError("パスワードは必須です。")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    )
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, digest_hex = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
    except (AttributeError, ValueError):
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(candidate, digest_hex)


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def _ensure_column_exists(conn: sqlite3.Connection, table_name: str, column_name: str, column_sql: str) -> None:
    if not _column_exists(conn, table_name, column_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")


def _ensure_daily_records_category_compatibility(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'daily_records'"
    ).fetchone()
    table_sql = str(row[0]) if row and row[0] else ""
    required_tokens = [SUPPORT_PROGRESS_AUTO_CATEGORY, *SUPPORT_PROGRESS_CATEGORIES]
    if table_sql and all(token in table_sql for token in required_tokens):
        return

    existing_rows = conn.execute(
        """
        SELECT id, resident_id, staff_id, category, content, recorded_at, updated_at
          FROM daily_records
         ORDER BY id ASC
        """
    ).fetchall()

    conn.execute("DROP INDEX IF EXISTS idx_daily_records_resident_category_recorded")
    conn.execute("ALTER TABLE daily_records RENAME TO daily_records_old")
    conn.execute(
        """
        CREATE TABLE daily_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resident_id INTEGER NOT NULL,
            staff_id INTEGER,
            category TEXT NOT NULL CHECK (category IN ('食事', '服薬', '入浴', '巡視', 'その他', '支援経過', 'ご様子', '通所', '受診', '訪問看護', '移動支援', '外出', '外泊')),
            content TEXT NOT NULL,
            recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (resident_id) REFERENCES residents(id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,
            FOREIGN KEY (staff_id) REFERENCES staff(id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
        )
        """
    )

    if existing_rows:
        conn.executemany(
            """
            INSERT INTO daily_records (id, resident_id, staff_id, category, content, recorded_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    int(row["id"]),
                    int(row["resident_id"]),
                    row["staff_id"],
                    row["category"],
                    row["content"],
                    row["recorded_at"],
                    row["updated_at"],
                )
                for row in existing_rows
            ],
        )

    conn.execute("DROP TABLE daily_records_old")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_daily_records_resident_category_recorded ON daily_records(resident_id, category, recorded_at DESC, id DESC)"
    )


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    schema_sql = """
    CREATE TABLE IF NOT EXISTS units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_name TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS residents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        unit_id INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (unit_id) REFERENCES units(id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT
    );

    CREATE TABLE IF NOT EXISTS vitals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resident_id INTEGER NOT NULL,
        staff_id INTEGER,
        temperature REAL,
        systolic_bp INTEGER,
        diastolic_bp INTEGER,
        pulse INTEGER,
        spo2 INTEGER,
        scene TEXT NOT NULL CHECK (scene IN ('朝', '入浴前')),
        note TEXT DEFAULT '',
        recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (resident_id) REFERENCES residents(id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT,
        FOREIGN KEY (staff_id) REFERENCES staff(id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT
    );

    CREATE TABLE IF NOT EXISTS daily_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resident_id INTEGER NOT NULL,
        staff_id INTEGER,
        category TEXT NOT NULL CHECK (category IN ('食事', '服薬', '入浴', '巡視', 'その他', '支援経過', 'ご様子', '通所', '受診', '訪問看護', '移動支援', '外出', '外泊')),
        content TEXT NOT NULL,
        recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (resident_id) REFERENCES residents(id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT,
        FOREIGN KEY (staff_id) REFERENCES staff(id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT
    );

    CREATE TABLE IF NOT EXISTS care_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resident_id INTEGER NOT NULL,
        staff_id INTEGER,
        content TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'pending', 'approved')),
        is_ai_generated INTEGER NOT NULL DEFAULT 0 CHECK (is_ai_generated IN (0, 1)),
        recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (resident_id) REFERENCES residents(id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT,
        FOREIGN KEY (staff_id) REFERENCES staff(id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT
    );

    CREATE INDEX IF NOT EXISTS idx_residents_unit_id ON residents(unit_id);
    CREATE INDEX IF NOT EXISTS idx_vitals_resident_recorded ON vitals(resident_id, recorded_at DESC, id DESC);
    CREATE INDEX IF NOT EXISTS idx_daily_records_resident_category_recorded ON daily_records(resident_id, category, recorded_at DESC, id DESC);
    CREATE INDEX IF NOT EXISTS idx_care_plans_resident_recorded ON care_plans(resident_id, recorded_at DESC, id DESC);
    """

    with get_connection(db_path) as conn:
        conn.executescript(schema_sql)
        _ensure_column_exists(conn, "vitals", "staff_id", "INTEGER")
        _ensure_column_exists(conn, "daily_records", "staff_id", "INTEGER")
        _ensure_column_exists(conn, "care_plans", "staff_id", "INTEGER")
        _ensure_column_exists(conn, "residents", "diagnosis", "TEXT DEFAULT ''")
        _ensure_column_exists(conn, "residents", "care_level", "TEXT DEFAULT ''")
        _ensure_column_exists(conn, "staff", "is_deleted", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column_exists(conn, "residents", "is_deleted", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column_exists(conn, "daily_records", "is_deleted", "INTEGER NOT NULL DEFAULT 0")
        _ensure_daily_records_category_compatibility(conn)
        conn.commit()


def _fetch_one(query: str, params: Sequence[Any] = (), db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        return _row_to_dict(conn.execute(query, params).fetchone())


def _fetch_all(query: str, params: Sequence[Any] = (), db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        return _rows_to_dicts(conn.execute(query, params).fetchall())


# Unit CRUD

def create_unit(unit_name: str, db_path: str = DEFAULT_DB_PATH) -> int:
    if not unit_name or not unit_name.strip():
        raise ValueError("ユニット名は必須です。")
    ts = _now_str()
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO units (unit_name, created_at, updated_at) VALUES (?, ?, ?)",
            (unit_name.strip(), ts, ts),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_unit(unit_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    return _fetch_one("SELECT * FROM units WHERE id = ?", (unit_id,), db_path)


def list_units(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    return _fetch_all("SELECT * FROM units ORDER BY unit_name ASC", db_path=db_path)


def update_unit(unit_id: int, unit_name: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    if not unit_name or not unit_name.strip():
        raise ValueError("ユニット名は必須です。")
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "UPDATE units SET unit_name = ?, updated_at = ? WHERE id = ?",
            (unit_name.strip(), _now_str(), unit_id),
        )
        conn.commit()
        return cur.rowcount > 0


def delete_unit(unit_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    with get_connection(db_path) as conn:
        cur = conn.execute("DELETE FROM units WHERE id = ?", (unit_id,))
        conn.commit()
        return cur.rowcount > 0


# Staff CRUD

def create_staff(name: str, password: str, role: str, db_path: str = DEFAULT_DB_PATH) -> int:
    if not name or not name.strip():
        raise ValueError("職員名は必須です。")
    if not role or not role.strip():
        raise ValueError("権限は必須です。")
    ts = _now_str()
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO staff (name, password, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (name.strip(), _hash_password(password), role.strip(), ts, ts),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_staff(staff_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    return _fetch_one(
        "SELECT id, name, role, created_at, updated_at FROM staff WHERE id = ? AND COALESCE(is_deleted, 0) = 0",
        (staff_id,),
        db_path,
    )


def list_staff(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    return _fetch_all(
        "SELECT id, name, role, created_at, updated_at FROM staff WHERE COALESCE(is_deleted, 0) = 0 ORDER BY name ASC",
        db_path=db_path,
    )


def update_staff(
    staff_id: int,
    name: Optional[str] = None,
    password: Optional[str] = None,
    role: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> bool:
    updates: List[str] = []
    params: List[Any] = []

    if name is not None:
        if not name.strip():
            raise ValueError("職員名は空にできません。")
        updates.append("name = ?")
        params.append(name.strip())
    if password is not None:
        updates.append("password = ?")
        params.append(_hash_password(password))
    if role is not None:
        if not role.strip():
            raise ValueError("権限は空にできません。")
        updates.append("role = ?")
        params.append(role.strip())
    if not updates:
        return False

    updates.append("updated_at = ?")
    params.append(_now_str())
    params.append(staff_id)

    with get_connection(db_path) as conn:
        cur = conn.execute(f"UPDATE staff SET {', '.join(updates)} WHERE id = ?", tuple(params))
        conn.commit()
        return cur.rowcount > 0


def _get_staff_reference_map(conn: sqlite3.Connection) -> List[tuple[str, List[str]]]:
    reference_map: List[tuple[str, List[str]]] = []
    for table_name in _get_user_tables(conn):
        if table_name in {"staff", "units"}:
            continue

        columns = _get_table_columns(conn, table_name)
        staff_ref_columns: List[str] = []

        try:
            fk_rows = conn.execute(f"PRAGMA foreign_key_list({_quote_ident(table_name)})").fetchall()
        except sqlite3.Error:
            fk_rows = []

        for row in fk_rows:
            if len(row) >= 4 and str(row[2]).lower() == "staff":
                from_col = str(row[3])
                if from_col and from_col not in staff_ref_columns:
                    staff_ref_columns.append(from_col)

        if "staff_id" in columns and "staff_id" not in staff_ref_columns:
            staff_ref_columns.append("staff_id")

        if staff_ref_columns:
            reference_map.append((table_name, staff_ref_columns))

    return reference_map


def _ensure_archived_staff(conn: sqlite3.Connection, exclude_staff_id: Optional[int] = None) -> int:
    params: List[Any] = ["退職済み職員"]
    query = "SELECT id FROM staff WHERE name = ? AND COALESCE(is_deleted, 0) = 0"
    if exclude_staff_id is not None:
        query += " AND id <> ?"
        params.append(exclude_staff_id)
    row = conn.execute(query, tuple(params)).fetchone()
    if row:
        return int(row[0])

    ts = _now_str()
    cur = conn.execute(
        "INSERT INTO staff (name, password, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("退職済み職員", _hash_password("archived-staff"), "退職", ts, ts),
    )
    return int(cur.lastrowid)


def delete_staff(staff_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    with get_connection(db_path) as conn:
        existing = conn.execute("SELECT id, name FROM staff WHERE id = ? AND COALESCE(is_deleted, 0) = 0", (staff_id,)).fetchone()
        if not existing:
            return False
        if str(existing[1]) == "退職済み職員":
            return False

        cur = conn.execute(
            "UPDATE staff SET is_deleted = 1, role = ?, updated_at = ? WHERE id = ? AND COALESCE(is_deleted, 0) = 0",
            ("退職", _now_str(), staff_id),
        )
        conn.commit()
        return cur.rowcount > 0


def verify_staff_credentials(name: str, password: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    row = _fetch_one("SELECT * FROM staff WHERE name = ? AND COALESCE(is_deleted, 0) = 0", (name.strip(),), db_path)
    if not row:
        return None
    if not _verify_password(password, row["password"]):
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "role": row["role"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# Resident CRUD

def create_resident(
    name: str,
    unit_id: int,
    diagnosis: str = "",
    care_level: str = "",
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    if not name or not name.strip():
        raise ValueError("利用者名は必須です。")
    ts = _now_str()
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO residents (name, unit_id, diagnosis, care_level, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (name.strip(), unit_id, (diagnosis or "").strip(), (care_level or "").strip(), ts, ts),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_resident(resident_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    return _fetch_one(
        """
        SELECT r.*, u.unit_name
          FROM residents r
          JOIN units u ON u.id = r.unit_id
         WHERE r.id = ?
           AND COALESCE(r.is_deleted, 0) = 0
        """,
        (resident_id,),
        db_path,
    )


def list_residents(unit_id: Optional[int] = None, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    query = """
        SELECT r.*, u.unit_name
          FROM residents r
          JOIN units u ON u.id = r.unit_id
    """
    params: List[Any] = []
    query += " WHERE COALESCE(r.is_deleted, 0) = 0"
    if unit_id is not None:
        query += " AND r.unit_id = ?"
        params.append(unit_id)
    query += " ORDER BY u.unit_name ASC, r.name ASC"
    return _fetch_all(query, tuple(params), db_path)


def update_resident(
    resident_id: int,
    name: Optional[str] = None,
    unit_id: Optional[int] = None,
    diagnosis: Optional[str] = None,
    care_level: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> bool:
    updates: List[str] = []
    params: List[Any] = []
    if name is not None:
        if not name.strip():
            raise ValueError("利用者名は空にできません。")
        updates.append("name = ?")
        params.append(name.strip())
    if unit_id is not None:
        updates.append("unit_id = ?")
        params.append(unit_id)
    if diagnosis is not None:
        updates.append("diagnosis = ?")
        params.append((diagnosis or "").strip())
    if care_level is not None:
        updates.append("care_level = ?")
        params.append((care_level or "").strip())
    if not updates:
        return False
    updates.append("updated_at = ?")
    params.append(_now_str())
    params.append(resident_id)
    with get_connection(db_path) as conn:
        cur = conn.execute(f"UPDATE residents SET {', '.join(updates)} WHERE id = ?", tuple(params))
        conn.commit()
        return cur.rowcount > 0



def _quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _get_user_tables(conn: sqlite3.Connection) -> List[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return [str(row[0]) for row in rows if row[0]]


def _get_table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    rows = conn.execute(f"PRAGMA table_info({_quote_ident(table_name)})").fetchall()
    return [str(row[1]) for row in rows if len(row) > 1]


def _get_resident_reference_map(conn: sqlite3.Connection) -> List[tuple[str, List[str]]]:
    reference_map: List[tuple[str, List[str]]] = []
    for table_name in _get_user_tables(conn):
        if table_name in {"residents", "units", "staff"}:
            continue

        columns = _get_table_columns(conn, table_name)
        resident_ref_columns: List[str] = []

        try:
            fk_rows = conn.execute(f"PRAGMA foreign_key_list({_quote_ident(table_name)})").fetchall()
        except sqlite3.Error:
            fk_rows = []

        for row in fk_rows:
            # PRAGMA foreign_key_list columns: id, seq, table, from, to, on_update, on_delete, match
            if len(row) >= 4 and str(row[2]).lower() == "residents":
                from_col = str(row[3])
                if from_col and from_col not in resident_ref_columns:
                    resident_ref_columns.append(from_col)

        if "resident_id" in columns and "resident_id" not in resident_ref_columns:
            resident_ref_columns.append("resident_id")

        if resident_ref_columns:
            reference_map.append((table_name, resident_ref_columns))

    return reference_map

def delete_resident(resident_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    with get_connection(db_path) as conn:
        reference_map = _get_resident_reference_map(conn)

        for table_name, ref_columns in reference_map:
            quoted_table = _quote_ident(table_name)
            for column_name in ref_columns:
                quoted_column = _quote_ident(column_name)
                conn.execute(f"DELETE FROM {quoted_table} WHERE {quoted_column} = ?", (resident_id,))

        cur = conn.execute(
            "UPDATE residents SET is_deleted = 1, updated_at = ? WHERE id = ? AND COALESCE(is_deleted, 0) = 0",
            (_now_str(), resident_id),
        )
        conn.commit()
        return cur.rowcount > 0


def ensure_default_master_data(db_path: str = DEFAULT_DB_PATH) -> None:
    default_unit_name = "デフォルトユニット"
    default_staff = [
        {"name": "管理者", "password": "0000", "role": "管理者"},
    ]
    default_residents = [f"利用者{index:02d}" for index in range(1, 11)]

    with get_connection(db_path) as conn:
        unit_rows = conn.execute("SELECT id, unit_name FROM units ORDER BY id ASC").fetchall()
        if unit_rows:
            unit_id = int(unit_rows[0]["id"])
        else:
            ts = _now_str()
            cur = conn.execute(
                "INSERT INTO units (unit_name, created_at, updated_at) VALUES (?, ?, ?)",
                (default_unit_name, ts, ts),
            )
            unit_id = int(cur.lastrowid)

        staff_count = int(conn.execute("SELECT COUNT(*) FROM staff WHERE COALESCE(is_deleted, 0) = 0").fetchone()[0] or 0)
        if staff_count == 0:
            ts = _now_str()
            for item in default_staff:
                conn.execute(
                    "INSERT INTO staff (name, password, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (item["name"], _hash_password(item["password"]), item["role"], ts, ts),
                )

        resident_count = int(conn.execute("SELECT COUNT(*) FROM residents WHERE COALESCE(is_deleted, 0) = 0").fetchone()[0] or 0)
        if resident_count == 0:
            ts = _now_str()
            for name in default_residents:
                conn.execute(
                    "INSERT INTO residents (name, unit_id, diagnosis, care_level, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, unit_id, "", "", ts, ts),
                )
        conn.commit()


# Dashboard queries

def list_residents_with_latest_vitals(
    unit_id: Optional[int] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    query = """
    WITH latest_vitals AS (
        SELECT
            v.*,
            ROW_NUMBER() OVER (
                PARTITION BY v.resident_id
                ORDER BY v.recorded_at DESC, v.id DESC
            ) AS rn
        FROM vitals v
    )
    SELECT
        r.id,
        r.name,
        r.unit_id,
        r.diagnosis,
        r.care_level,
        u.unit_name,
        lv.id AS latest_vital_id,
        lv.temperature AS latest_temperature,
        lv.systolic_bp AS latest_systolic_bp,
        lv.diastolic_bp AS latest_diastolic_bp,
        lv.pulse AS latest_pulse,
        lv.spo2 AS latest_spo2,
        lv.scene AS latest_scene,
        lv.note AS latest_note,
        lv.recorded_at AS latest_recorded_at,
        lv.staff_id AS latest_vital_staff_id
    FROM residents r
    JOIN units u ON u.id = r.unit_id
    LEFT JOIN latest_vitals lv ON lv.resident_id = r.id AND lv.rn = 1
    WHERE COALESCE(r.is_deleted, 0) = 0
    """
    params: List[Any] = []
    if unit_id is not None:
        query += " AND r.unit_id = ?"
        params.append(unit_id)
    query += " ORDER BY u.unit_name ASC, r.name ASC"
    return _fetch_all(query, tuple(params), db_path)


def list_residents_with_latest_status(
    unit_id: Optional[int] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    query = """
    WITH latest_vitals AS (
        SELECT
            v.*,
            ROW_NUMBER() OVER (
                PARTITION BY v.resident_id
                ORDER BY v.recorded_at DESC, v.id DESC
            ) AS rn
        FROM vitals v
    ),
    latest_meals AS (
        SELECT
            d.*,
            ROW_NUMBER() OVER (
                PARTITION BY d.resident_id
                ORDER BY d.recorded_at DESC, d.id DESC
            ) AS rn
        FROM daily_records d
        WHERE d.category = '食事'
          AND COALESCE(d.is_deleted, 0) = 0
    ),
    latest_meds AS (
        SELECT
            d.*,
            ROW_NUMBER() OVER (
                PARTITION BY d.resident_id
                ORDER BY d.recorded_at DESC, d.id DESC
            ) AS rn
        FROM daily_records d
        WHERE d.category = '服薬'
          AND COALESCE(d.is_deleted, 0) = 0
    ),
    latest_baths AS (
        SELECT
            d.*,
            ROW_NUMBER() OVER (
                PARTITION BY d.resident_id
                ORDER BY d.recorded_at DESC, d.id DESC
            ) AS rn
        FROM daily_records d
        WHERE d.category = '入浴'
          AND COALESCE(d.is_deleted, 0) = 0
    ),
    latest_patrols AS (
        SELECT
            d.*,
            ROW_NUMBER() OVER (
                PARTITION BY d.resident_id
                ORDER BY d.recorded_at DESC, d.id DESC
            ) AS rn
        FROM daily_records d
        WHERE d.category = '巡視'
          AND COALESCE(d.is_deleted, 0) = 0
    )
    SELECT
        r.id,
        r.name,
        r.unit_id,
        r.diagnosis,
        r.care_level,
        u.unit_name,
        lv.id AS latest_vital_id,
        lv.temperature AS latest_temperature,
        lv.systolic_bp AS latest_systolic_bp,
        lv.diastolic_bp AS latest_diastolic_bp,
        lv.pulse AS latest_pulse,
        lv.spo2 AS latest_spo2,
        lv.scene AS latest_scene,
        lv.note AS latest_note,
        lv.recorded_at AS latest_recorded_at,
        lv.staff_id AS latest_vital_staff_id,
        lm.id AS latest_meal_record_id,
        COALESCE(lm.content, 'なし') AS latest_meal_content,
        lm.recorded_at AS latest_meal_recorded_at,
        lm.staff_id AS latest_meal_staff_id,
        md.id AS latest_medication_record_id,
        COALESCE(md.content, 'なし') AS latest_medication_content,
        md.recorded_at AS latest_medication_recorded_at,
        md.staff_id AS latest_medication_staff_id,
        lb.id AS latest_bath_record_id,
        COALESCE(lb.content, 'なし') AS latest_bath_content,
        lb.recorded_at AS latest_bath_recorded_at,
        lb.staff_id AS latest_bath_staff_id,
        lp.id AS latest_patrol_record_id,
        COALESCE(lp.content, 'なし') AS latest_patrol_content,
        lp.recorded_at AS latest_patrol_recorded_at,
        lp.staff_id AS latest_patrol_staff_id
    FROM residents r
    JOIN units u ON u.id = r.unit_id
    LEFT JOIN latest_vitals lv ON lv.resident_id = r.id AND lv.rn = 1
    LEFT JOIN latest_meals lm ON lm.resident_id = r.id AND lm.rn = 1
    LEFT JOIN latest_meds md ON md.resident_id = r.id AND md.rn = 1
    LEFT JOIN latest_baths lb ON lb.resident_id = r.id AND lb.rn = 1
    LEFT JOIN latest_patrols lp ON lp.resident_id = r.id AND lp.rn = 1
    WHERE COALESCE(r.is_deleted, 0) = 0
    """
    params: List[Any] = []
    if unit_id is not None:
        query += " AND r.unit_id = ?"
        params.append(unit_id)
    query += " ORDER BY u.unit_name ASC, r.name ASC"
    rows = _fetch_all(query, tuple(params), db_path)
    for row in rows:
        parsed_bath = _parse_bath_record(row.get("latest_bath_content") or "", row.get("latest_bath_recorded_at"))
        row["latest_bath_status"] = parsed_bath["status"]
        row["latest_bath_label"] = parsed_bath["label"]
        parsed_patrol = _parse_patrol_record(row.get("latest_patrol_content") or "", row.get("latest_patrol_recorded_at"))
        row["latest_patrol_status"] = parsed_patrol["status"]
        row["latest_patrol_label"] = parsed_patrol["label"]
    return rows


_DAILY_STATUS_TIMINGS = ("朝", "昼", "夕")


def _normalize_daily_timing(value: Optional[str]) -> Optional[str]:
    text = (value or "").strip()
    mapping = {
        "朝": "朝",
        "朝食": "朝",
        "昼": "昼",
        "昼食": "昼",
        "夕": "夕",
        "夜": "夕",
        "夕食": "夕",
        "夕飯": "夕",
    }
    return mapping.get(text)


def _default_daily_status_block() -> Dict[str, Dict[str, Dict[str, Any]]]:
    return {
        "meal": {
            timing: {
                "timing": timing,
                "label": "未記録",
                "amount": None,
                "content": "未記録",
                "recorded_at": None,
            }
            for timing in _DAILY_STATUS_TIMINGS
        },
        "medication": {
            timing: {
                "timing": timing,
                "label": "未記録",
                "status": "未記録",
                "content": "未記録",
                "recorded_at": None,
            }
            for timing in _DAILY_STATUS_TIMINGS
        },
        "bath": {
            "timing": None,
            "label": "未記録",
            "status": "未記録",
            "content": "未記録",
            "recorded_at": None,
        },
        "patrol": {
            "time": None,
            "sleep": None,
            "safety": None,
            "label": "未記録",
            "status": "未記録",
            "content": "未記録",
            "recorded_at": None,
        },
    }


def _extract_daily_timing_from_text(content: str) -> Optional[str]:
    text = (content or "").strip()
    for token in ("朝食", "昼食", "夕食", "夕飯", "朝", "昼", "夕", "夜"):
        if token in text:
            return _normalize_daily_timing(token)
    return None


def _extract_daily_timing_from_recorded_at(recorded_at: Optional[str]) -> Optional[str]:
    if not recorded_at:
        return None
    text = str(recorded_at).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            hour = datetime.strptime(text, fmt).hour
            if hour < 11:
                return "朝"
            if hour < 16:
                return "昼"
            return "夕"
        except ValueError:
            continue
    return None


def _parse_meal_record(content: str, recorded_at: Optional[str]) -> Dict[str, Any]:
    text = (content or "").strip()
    timing = _extract_daily_timing_from_text(text) or _extract_daily_timing_from_recorded_at(recorded_at)

    amount = None
    match = re.search(r"(\d{1,2})\s*/\s*10", text)
    if match:
        amount = int(match.group(1))
    else:
        match = re.search(r"\b(10|[1-9])\b", text)
        if match:
            amount = int(match.group(1))

    label = f"{amount}/10" if amount is not None else (text or "未記録")
    return {
        "timing": timing,
        "label": label,
        "amount": amount,
        "content": text or "未記録",
        "recorded_at": recorded_at,
    }


def _parse_medication_record(content: str, recorded_at: Optional[str]) -> Dict[str, Any]:
    text = (content or "").strip()
    timing = _extract_daily_timing_from_text(text) or _extract_daily_timing_from_recorded_at(recorded_at)

    if "未完了" in text or re.search(r"(^|\s)未($|\s)", text):
        status = "未"
    elif "完了" in text or "済" in text:
        status = "完了"
    else:
        status = "未記録" if not text else text

    return {
        "timing": timing,
        "label": status,
        "status": status,
        "content": text or "未記録",
        "recorded_at": recorded_at,
    }


def _parse_bath_record(content: str, recorded_at: Optional[str]) -> Dict[str, Any]:
    text = (content or "").strip()
    normalized = text.replace("　", " ")

    if not normalized:
        status = "未記録"
    elif any(token in normalized for token in ("未実施", "見送り", "見送", "中止", "拒否", "入らず", "なし")):
        status = "未実施"
    elif "清拭" in normalized:
        status = "清拭"
    elif "シャワ" in normalized:
        status = "シャワー"
    elif "浴槽" in normalized or "湯船" in normalized:
        status = "浴槽"
    elif "見守り" in normalized:
        status = "見守り"
    elif "介助" in normalized and "入浴" in normalized:
        status = "介助"
    elif "入浴" in normalized:
        status = "実施"
    else:
        status = normalized

    label = status if status else "未記録"
    return {
        "timing": None,
        "label": label,
        "status": status or "未記録",
        "content": normalized or "未記録",
        "recorded_at": recorded_at,
    }



def _parse_patrol_record(content: str, recorded_at: Optional[str]) -> Dict[str, Any]:
    text = (content or "").strip()
    normalized = text.replace("　", " ")

    time_match = re.search(r"\b([0-2]?\d:\d{2})\b", normalized)
    patrol_time = time_match.group(1) if time_match else None

    if "覚醒" in normalized:
        sleep = "覚醒"
    elif "眠れている" in normalized or "入眠" in normalized or "就寝" in normalized or "睡眠" in normalized:
        sleep = "眠れている"
    else:
        sleep = None

    safety = None
    safety_match = re.search(r"安全確認[:：]\s*(.+)$", normalized)
    if safety_match:
        safety = safety_match.group(1).strip()
    elif "|" in normalized:
        parts = [part.strip() for part in normalized.split("|") if part.strip()]
        if len(parts) >= 3:
            last_part = parts[-1]
            safety = re.sub(r"^(安全確認|安全)[:：]\s*", "", last_part).strip() or None

    label_parts = [part for part in (patrol_time, sleep) if part]
    label = " ".join(label_parts) if label_parts else (normalized or "未記録")

    return {
        "time": patrol_time,
        "sleep": sleep,
        "safety": safety or "記載なし",
        "label": label,
        "status": sleep or ("未記録" if not normalized else normalized),
        "content": normalized or "未記録",
        "recorded_at": recorded_at,
    }


def get_resident_daily_status(
    resident_id: int,
    target_date: Optional[Any] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """指定した利用者の対象日分の食事・服薬・入浴・巡視の最新状態を返す。"""
    if isinstance(target_date, str) and os.path.sep in target_date and db_path == DEFAULT_DB_PATH:
        db_path = target_date
        target_date = None

    target_date_str = date.today().isoformat() if target_date is None else str(target_date)
    status = _default_daily_status_block()

    with get_connection(db_path) as conn:
        meal_rows = conn.execute(
            """
            SELECT content, recorded_at
              FROM daily_records
             WHERE resident_id = ?
               AND category = '食事'
               AND date(recorded_at) = ?
             ORDER BY recorded_at DESC, id DESC
            """,
            (resident_id, target_date_str),
        ).fetchall()

        seen_meal: set[str] = set()
        for row in meal_rows:
            parsed = _parse_meal_record(row["content"], row["recorded_at"])
            timing = parsed.get("timing")
            if timing is None or timing in seen_meal:
                continue
            status["meal"][timing] = parsed
            seen_meal.add(timing)
            if len(seen_meal) == len(_DAILY_STATUS_TIMINGS):
                break

        med_rows = conn.execute(
            """
            SELECT content, recorded_at
              FROM daily_records
             WHERE resident_id = ?
               AND category = '服薬'
               AND date(recorded_at) = ?
             ORDER BY recorded_at DESC, id DESC
            """,
            (resident_id, target_date_str),
        ).fetchall()

        seen_med: set[str] = set()
        for row in med_rows:
            parsed = _parse_medication_record(row["content"], row["recorded_at"])
            timing = parsed.get("timing")
            if timing is None or timing in seen_med:
                continue
            status["medication"][timing] = parsed
            seen_med.add(timing)
            if len(seen_med) == len(_DAILY_STATUS_TIMINGS):
                break

        bath_row = conn.execute(
            """
            SELECT content, recorded_at
              FROM daily_records
             WHERE resident_id = ?
               AND category = '入浴'
               AND date(recorded_at) = ?
             ORDER BY recorded_at DESC, id DESC
             LIMIT 1
            """,
            (resident_id, target_date_str),
        ).fetchone()
        if bath_row:
            status["bath"] = _parse_bath_record(bath_row["content"], bath_row["recorded_at"])

        patrol_row = conn.execute(
            """
            SELECT content, recorded_at
              FROM daily_records
             WHERE resident_id = ?
               AND category = '巡視'
               AND date(recorded_at) = ?
             ORDER BY recorded_at DESC, id DESC
             LIMIT 1
            """,
            (resident_id, target_date_str),
        ).fetchone()
        if patrol_row:
            status["patrol"] = _parse_patrol_record(patrol_row["content"], patrol_row["recorded_at"])

    return status


# Vitals CRUD

def _build_vital_summary(
    temperature: Optional[float],
    systolic_bp: Optional[int],
    diastolic_bp: Optional[int],
    pulse: Optional[int],
    spo2: Optional[int],
    scene: str,
    note: str,
    recorded_at: Optional[str] = None,
) -> str:
    parts = [f"{scene} バイタル"]
    if recorded_at:
        try:
            parts.append(f"時刻:{datetime.strptime(str(recorded_at), '%Y-%m-%d %H:%M:%S').strftime('%H:%M')}")
        except ValueError:
            parts.append(f"時刻:{recorded_at}")
    if temperature is not None:
        parts.append(f"体温:{temperature:.1f}℃")
    if systolic_bp is not None or diastolic_bp is not None:
        sys_text = "-" if systolic_bp is None else str(systolic_bp)
        dia_text = "-" if diastolic_bp is None else str(diastolic_bp)
        parts.append(f"血圧:{sys_text}/{dia_text}")
    if pulse is not None:
        parts.append(f"脈拍:{pulse}")
    if spo2 is not None:
        parts.append(f"SpO2:{spo2}%")
    if note and note.strip():
        parts.append(f"備考:{note.strip()}")
    return ", ".join(parts)


def _create_daily_record_with_conn(
    conn: sqlite3.Connection,
    resident_id: int,
    staff_id: int,
    category: str,
    content: str,
    recorded_at: str,
) -> int:
    _require_staff_id(staff_id)
    if not content or not content.strip():
        raise ValueError("経過記録の内容は必須です。")
    _validate_choice(category, ALLOWED_RECORD_CATEGORIES, "カテゴリ")
    cur = conn.execute(
        """
        INSERT INTO daily_records (resident_id, staff_id, category, content, recorded_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (resident_id, staff_id, category, content.strip(), recorded_at, recorded_at),
    )
    return int(cur.lastrowid)


def _format_auto_support_progress_content(source_category: str, content: str) -> str:
    summary = (content or "").strip()
    if not summary:
        raise ValueError("自動連携する支援経過の内容がありません。")
    return f"【自動連携:{source_category}】 {summary}"


def create_auto_support_progress_record_with_conn(
    conn: sqlite3.Connection,
    resident_id: int,
    staff_id: int,
    source_category: str,
    content: str,
    recorded_at: str,
) -> int:
    return _create_daily_record_with_conn(
        conn,
        resident_id,
        staff_id,
        SUPPORT_PROGRESS_AUTO_CATEGORY,
        _format_auto_support_progress_content(source_category, content),
        recorded_at,
    )


def create_support_progress_record(
    resident_id: int,
    staff_id: Optional[int],
    category: str,
    content: str,
    recorded_at: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    staff_id = _require_staff_id(staff_id)
    ts = recorded_at or _now_str()
    return create_daily_record(
        resident_id=resident_id,
        staff_id=staff_id,
        category=category,
        content=content,
        recorded_at=ts,
        db_path=db_path,
    )


def create_auto_support_progress_record(
    resident_id: int,
    staff_id: Optional[int],
    source_category: str,
    content: str,
    recorded_at: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    staff_id = _require_staff_id(staff_id)
    ts = recorded_at or _now_str()
    with get_connection(db_path) as conn:
        record_id = create_auto_support_progress_record_with_conn(
            conn,
            resident_id,
            staff_id,
            source_category,
            content,
            ts,
        )
        conn.commit()
        return record_id


def create_vital(
    resident_id: int,
    staff_id: Optional[int],
    temperature: Optional[float] = None,
    systolic_bp: Optional[int] = None,
    diastolic_bp: Optional[int] = None,
    pulse: Optional[int] = None,
    spo2: Optional[int] = None,
    scene: str = "朝",
    note: str = "",
    recorded_at: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    staff_id = _require_staff_id(staff_id)
    _validate_choice(scene, ALLOWED_VITAL_SCENES, "シーン")
    ts = recorded_at or _now_str()
    summary = _build_vital_summary(temperature, systolic_bp, diastolic_bp, pulse, spo2, scene, note, ts)

    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO vitals (
                resident_id, staff_id, temperature, systolic_bp, diastolic_bp,
                pulse, spo2, scene, note, recorded_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resident_id,
                staff_id,
                temperature,
                systolic_bp,
                diastolic_bp,
                pulse,
                spo2,
                scene,
                note.strip(),
                ts,
                ts,
            ),
        )
        vital_id = int(cur.lastrowid)
        create_auto_support_progress_record_with_conn(conn, resident_id, staff_id, "バイタル", summary, ts)
        conn.commit()
        return vital_id


def get_vital(vital_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    return _fetch_one(
        """
        SELECT v.*, r.name AS resident_name, s.name AS staff_name, u.unit_name
          FROM vitals v
          JOIN residents r ON r.id = v.resident_id
          JOIN units u ON u.id = r.unit_id
          JOIN staff s ON s.id = v.staff_id
         WHERE v.id = ?
           AND COALESCE(r.is_deleted, 0) = 0
        """,
        (vital_id,),
        db_path,
    )


def list_vitals(
    resident_id: Optional[int] = None,
    staff_id: Optional[int] = None,
    unit_id: Optional[int] = None,
    scene: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    if scene is not None:
        _validate_choice(scene, ALLOWED_VITAL_SCENES, "シーン")
    query = """
        SELECT v.*, r.name AS resident_name, s.name AS staff_name, u.unit_name
          FROM vitals v
          JOIN residents r ON r.id = v.resident_id
          JOIN units u ON u.id = r.unit_id
          JOIN staff s ON s.id = v.staff_id
         WHERE 1 = 1
           AND COALESCE(r.is_deleted, 0) = 0
    """
    params: List[Any] = []
    if resident_id is not None:
        query += " AND v.resident_id = ?"
        params.append(resident_id)
    if staff_id is not None:
        query += " AND v.staff_id = ?"
        params.append(staff_id)
    if unit_id is not None:
        query += " AND r.unit_id = ?"
        params.append(unit_id)
    if scene is not None:
        query += " AND v.scene = ?"
        params.append(scene)
    if date_from is not None:
        query += " AND v.recorded_at >= ?"
        params.append(date_from)
    if date_to is not None:
        query += " AND v.recorded_at <= ?"
        params.append(date_to)
    query += " ORDER BY v.recorded_at DESC, v.id DESC LIMIT ?"
    params.append(limit)
    return _fetch_all(query, tuple(params), db_path)


def update_vital(
    vital_id: int,
    temperature: Optional[float] = None,
    systolic_bp: Optional[int] = None,
    diastolic_bp: Optional[int] = None,
    pulse: Optional[int] = None,
    spo2: Optional[int] = None,
    scene: Optional[str] = None,
    note: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> bool:
    updates: List[str] = []
    params: List[Any] = []
    if temperature is not None:
        updates.append("temperature = ?")
        params.append(temperature)
    if systolic_bp is not None:
        updates.append("systolic_bp = ?")
        params.append(systolic_bp)
    if diastolic_bp is not None:
        updates.append("diastolic_bp = ?")
        params.append(diastolic_bp)
    if pulse is not None:
        updates.append("pulse = ?")
        params.append(pulse)
    if spo2 is not None:
        updates.append("spo2 = ?")
        params.append(spo2)
    if scene is not None:
        _validate_choice(scene, ALLOWED_VITAL_SCENES, "シーン")
        updates.append("scene = ?")
        params.append(scene)
    if note is not None:
        updates.append("note = ?")
        params.append(note.strip())
    if not updates:
        return False
    updates.append("updated_at = ?")
    params.append(_now_str())
    params.append(vital_id)
    with get_connection(db_path) as conn:
        cur = conn.execute(f"UPDATE vitals SET {', '.join(updates)} WHERE id = ?", tuple(params))
        conn.commit()
        return cur.rowcount > 0


def delete_vital(vital_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    with get_connection(db_path) as conn:
        cur = conn.execute("DELETE FROM vitals WHERE id = ?", (vital_id,))
        conn.commit()
        return cur.rowcount > 0


# DailyRecords CRUD

def create_daily_record(
    resident_id: int,
    staff_id: Optional[int],
    category: str,
    content: str,
    recorded_at: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    staff_id = _require_staff_id(staff_id)
    ts = recorded_at or _now_str()
    with get_connection(db_path) as conn:
        record_id = _create_daily_record_with_conn(conn, resident_id, staff_id, category, content, ts)
        conn.commit()
        return record_id


def get_daily_record(record_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    return _fetch_one(
        """
        SELECT d.*, r.name AS resident_name, s.name AS staff_name, u.unit_name
          FROM daily_records d
          JOIN residents r ON r.id = d.resident_id
          JOIN units u ON u.id = r.unit_id
          JOIN staff s ON s.id = d.staff_id
         WHERE d.id = ?
           AND COALESCE(d.is_deleted, 0) = 0
           AND COALESCE(r.is_deleted, 0) = 0
        """,
        (record_id,),
        db_path,
    )


def list_daily_records(
    resident_id: Optional[int] = None,
    staff_id: Optional[int] = None,
    unit_id: Optional[int] = None,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    if category is not None:
        _validate_choice(category, ALLOWED_RECORD_CATEGORIES, "カテゴリ")
    query = """
        SELECT d.*, r.name AS resident_name, s.name AS staff_name, u.unit_name
          FROM daily_records d
          JOIN residents r ON r.id = d.resident_id
          JOIN units u ON u.id = r.unit_id
          JOIN staff s ON s.id = d.staff_id
         WHERE 1 = 1
           AND COALESCE(d.is_deleted, 0) = 0
           AND COALESCE(r.is_deleted, 0) = 0
    """
    params: List[Any] = []
    if resident_id is not None:
        query += " AND d.resident_id = ?"
        params.append(resident_id)
    if staff_id is not None:
        query += " AND d.staff_id = ?"
        params.append(staff_id)
    if unit_id is not None:
        query += " AND r.unit_id = ?"
        params.append(unit_id)
    if category is not None:
        query += " AND d.category = ?"
        params.append(category)
    if date_from is not None:
        query += " AND d.recorded_at >= ?"
        params.append(date_from)
    if date_to is not None:
        query += " AND d.recorded_at <= ?"
        params.append(date_to)
    query += " ORDER BY d.recorded_at DESC, d.id DESC LIMIT ?"
    params.append(limit)
    return _fetch_all(query, tuple(params), db_path)


def list_support_progress_records(
    resident_id: Optional[int] = None,
    staff_id: Optional[int] = None,
    unit_id: Optional[int] = None,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    allowed_support_categories = {SUPPORT_PROGRESS_AUTO_CATEGORY, *SUPPORT_PROGRESS_CATEGORIES}
    if category is not None:
        _validate_choice(category, allowed_support_categories, "支援経過区分")

    query = """
        SELECT d.*, r.name AS resident_name, s.name AS staff_name, u.unit_name
          FROM daily_records d
          JOIN residents r ON r.id = d.resident_id
          JOIN units u ON u.id = r.unit_id
          LEFT JOIN staff s ON s.id = d.staff_id
         WHERE 1 = 1
           AND COALESCE(d.is_deleted, 0) = 0
           AND COALESCE(r.is_deleted, 0) = 0
    """
    params: List[Any] = []
    if resident_id is not None:
        query += " AND d.resident_id = ?"
        params.append(resident_id)
    if staff_id is not None:
        query += " AND d.staff_id = ?"
        params.append(staff_id)
    if unit_id is not None:
        query += " AND r.unit_id = ?"
        params.append(unit_id)
    if category is not None:
        query += " AND d.category = ?"
        params.append(category)
    else:
        placeholders = ", ".join(["?"] * len(allowed_support_categories))
        query += f" AND d.category IN ({placeholders})"
        params.extend([SUPPORT_PROGRESS_AUTO_CATEGORY, *SUPPORT_PROGRESS_CATEGORIES])
    if date_from is not None:
        query += " AND d.recorded_at >= ?"
        params.append(date_from)
    if date_to is not None:
        query += " AND d.recorded_at <= ?"
        params.append(date_to)
    query += " ORDER BY d.recorded_at DESC, d.id DESC LIMIT ?"
    params.append(limit)
    return _fetch_all(query, tuple(params), db_path)


def list_support_progress_export_rows(
    resident_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    rows = list_support_progress_records(
        resident_id=resident_id,
        date_from=date_from,
        date_to=date_to,
        limit=1000,
        db_path=db_path,
    )
    return [
        {
            "recorded_at": row.get("recorded_at"),
            "category": row.get("category"),
            "content": row.get("content"),
            "resident_name": row.get("resident_name"),
            "unit_name": row.get("unit_name"),
            "staff_name": row.get("staff_name") or "-",
        }
        for row in rows
    ]


def update_daily_record(
    record_id: int,
    category: Optional[str] = None,
    content: Optional[str] = None,
    recorded_at: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> bool:
    updates: List[str] = []
    params: List[Any] = []
    if category is not None:
        _validate_choice(category, ALLOWED_RECORD_CATEGORIES, "カテゴリ")
        updates.append("category = ?")
        params.append(category)
    if content is not None:
        if not content.strip():
            raise ValueError("経過記録の内容は空にできません。")
        updates.append("content = ?")
        params.append(content.strip())
    if recorded_at is not None:
        if not str(recorded_at).strip():
            raise ValueError("記録時刻は空にできません。")
        updates.append("recorded_at = ?")
        params.append(str(recorded_at).strip())
    if not updates:
        return False
    updates.append("updated_at = ?")
    params.append(_now_str())
    params.append(record_id)
    with get_connection(db_path) as conn:
        cur = conn.execute(
            f"UPDATE daily_records SET {', '.join(updates)} WHERE id = ? AND COALESCE(is_deleted, 0) = 0",
            tuple(params),
        )
        conn.commit()
        return cur.rowcount > 0


def delete_daily_record(record_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "UPDATE daily_records SET is_deleted = 1, updated_at = ? WHERE id = ? AND COALESCE(is_deleted, 0) = 0",
            (_now_str(), record_id),
        )
        conn.commit()
        return cur.rowcount > 0


# CarePlans CRUD

def create_care_plan(
    resident_id: int,
    staff_id: Optional[int],
    content: str,
    status: str = "draft",
    is_ai_generated: bool = False,
    recorded_at: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    staff_id = _require_staff_id(staff_id)
    if not content or not content.strip():
        raise ValueError("個別支援計画の内容は必須です。")
    _validate_choice(status, ALLOWED_CARE_PLAN_STATUSES, "ステータス")
    ts = recorded_at or _now_str()
    with get_connection(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO care_plans (
                resident_id, staff_id, content, status, is_ai_generated, recorded_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (resident_id, staff_id, content.strip(), status, int(bool(is_ai_generated)), ts, ts),
        )
        care_plan_id = int(cur.lastrowid)
        _create_daily_record_with_conn(
            conn,
            resident_id,
            staff_id,
            "その他",
            f"個別支援計画を保存: ステータス={status}, AI生成={'あり' if is_ai_generated else 'なし'}",
            ts,
        )
        conn.commit()
        return care_plan_id


def get_care_plan(care_plan_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    return _fetch_one(
        """
        SELECT c.*, r.name AS resident_name, u.unit_name, s.name AS staff_name
          FROM care_plans c
          JOIN residents r ON r.id = c.resident_id
          JOIN units u ON u.id = r.unit_id
          LEFT JOIN staff s ON s.id = c.staff_id
         WHERE c.id = ?
           AND COALESCE(r.is_deleted, 0) = 0
        """,
        (care_plan_id,),
        db_path,
    )


def list_care_plans(
    resident_id: Optional[int] = None,
    status: Optional[str] = None,
    is_ai_generated: Optional[bool] = None,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    if status is not None:
        _validate_choice(status, ALLOWED_CARE_PLAN_STATUSES, "ステータス")
    query = """
        SELECT c.*, r.name AS resident_name, u.unit_name, s.name AS staff_name
          FROM care_plans c
          JOIN residents r ON r.id = c.resident_id
          JOIN units u ON u.id = r.unit_id
          LEFT JOIN staff s ON s.id = c.staff_id
         WHERE 1 = 1
           AND COALESCE(r.is_deleted, 0) = 0
    """
    params: List[Any] = []
    if resident_id is not None:
        query += " AND c.resident_id = ?"
        params.append(resident_id)
    if status is not None:
        query += " AND c.status = ?"
        params.append(status)
    if is_ai_generated is not None:
        query += " AND c.is_ai_generated = ?"
        params.append(int(bool(is_ai_generated)))
    query += " ORDER BY c.recorded_at DESC, c.id DESC LIMIT ?"
    params.append(limit)
    return _fetch_all(query, tuple(params), db_path)


def update_care_plan(
    care_plan_id: int,
    content: Optional[str] = None,
    status: Optional[str] = None,
    is_ai_generated: Optional[bool] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> bool:
    updates: List[str] = []
    params: List[Any] = []
    if content is not None:
        if not content.strip():
            raise ValueError("個別支援計画の内容は空にできません。")
        updates.append("content = ?")
        params.append(content.strip())
    if status is not None:
        _validate_choice(status, ALLOWED_CARE_PLAN_STATUSES, "ステータス")
        updates.append("status = ?")
        params.append(status)
    if is_ai_generated is not None:
        updates.append("is_ai_generated = ?")
        params.append(int(bool(is_ai_generated)))
    if not updates:
        return False
    updates.append("updated_at = ?")
    params.append(_now_str())
    params.append(care_plan_id)
    with get_connection(db_path) as conn:
        cur = conn.execute(f"UPDATE care_plans SET {', '.join(updates)} WHERE id = ?", tuple(params))
        conn.commit()
        return cur.rowcount > 0


def delete_care_plan(care_plan_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    with get_connection(db_path) as conn:
        cur = conn.execute("DELETE FROM care_plans WHERE id = ?", (care_plan_id,))
        conn.commit()
        return cur.rowcount > 0



def get_support_progress_ai_context(
    resident_id: int,
    target_date: Optional[Any] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    resident = get_resident(resident_id, db_path=db_path)
    if resident is None:
        raise ValueError("対象利用者が存在しません。")

    target_date_str = date.today().isoformat() if target_date is None else str(target_date)
    date_from = f"{target_date_str} 00:00:00"
    date_to = f"{target_date_str} 23:59:59"

    with get_connection(db_path) as conn:
        vital_rows = conn.execute(
            """
            SELECT v.*, s.name AS staff_name
              FROM vitals v
              LEFT JOIN staff s ON s.id = v.staff_id
             WHERE v.resident_id = ?
               AND v.recorded_at >= ?
               AND v.recorded_at <= ?
             ORDER BY v.recorded_at ASC, v.id ASC
            """,
            (resident_id, date_from, date_to),
        ).fetchall()

        daily_rows = conn.execute(
            """
            SELECT d.*, s.name AS staff_name
              FROM daily_records d
              LEFT JOIN staff s ON s.id = d.staff_id
             WHERE d.resident_id = ?
               AND COALESCE(d.is_deleted, 0) = 0
               AND d.recorded_at >= ?
               AND d.recorded_at <= ?
             ORDER BY d.recorded_at ASC, d.id ASC
            """,
            (resident_id, date_from, date_to),
        ).fetchall()

    support_categories = {SUPPORT_PROGRESS_AUTO_CATEGORY, *SUPPORT_PROGRESS_CATEGORIES}
    support_progress_rows: List[Dict[str, Any]] = []
    other_daily_rows: List[Dict[str, Any]] = []
    for row in _rows_to_dicts(daily_rows):
        if row.get("category") in support_categories:
            support_progress_rows.append(row)
        else:
            other_daily_rows.append(row)

    return {
        "resident": resident,
        "target_date": target_date_str,
        "vitals": _rows_to_dicts(vital_rows),
        "daily_records": other_daily_rows,
        "support_progress_records": support_progress_rows,
    }


# Reusable context for future AI/PDF features

def get_resident_context(resident_id: int, db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    resident = get_resident(resident_id, db_path=db_path)
    if resident is None:
        raise ValueError("対象利用者が存在しません。")
    return {
        "resident": resident,
        "latest_status": next(
            (item for item in list_residents_with_latest_status(db_path=db_path) if item["id"] == resident_id),
            None,
        ),
        "recent_vitals": list_vitals(resident_id=resident_id, limit=20, db_path=db_path),
        "recent_daily_records": list_daily_records(resident_id=resident_id, limit=50, db_path=db_path),
        "recent_care_plans": list_care_plans(resident_id=resident_id, limit=20, db_path=db_path),
    }
