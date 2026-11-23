"""
Enterprise Role-Based Access Control (RBAC) and Audit Logging for SmartMIS.
Supports Admin, Manager, and Department-scoped Operators with salted SHA-256 passwords.
"""
import hashlib
import json
import logging
import os
import secrets
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

try:
    import config
except ImportError:
    from . import config

log = logging.getLogger("smartmis.auth")


def _hash_pw(password: str, salt: Optional[str] = None) -> str:
    """Generate salted SHA-256 hash in format salt$hexdigest."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    return f"{salt}${digest}"


def _verify_pw(password: str, stored_hash: str) -> bool:
    """Verify password against stored salt$digest."""
    try:
        salt, _ = stored_hash.split("$", 1)
        expected = _hash_pw(password, salt)
        return secrets.compare_digest(expected, stored_hash)
    except Exception:
        return False


# Default enterprise users matrix
DEFAULT_USERS: Dict[str, Dict[str, Any]] = {
    "admin": {
        "username": "admin",
        "full_name": "System Administrator",
        "role": "Admin",
        "department": "All",
        "password_hash": _hash_pw("admin123", salt="smartmis_admin_salt"),
    },
    "manager": {
        "username": "manager",
        "full_name": "Plant Operations Manager",
        "role": "Manager",
        "department": "All",
        "password_hash": _hash_pw("manager123", salt="smartmis_manager_salt"),
    },
    "foundry_op": {
        "username": "foundry_op",
        "full_name": "Foundry Shift Supervisor",
        "role": "Operator",
        "department": "Foundry",
        "password_hash": _hash_pw("foundry123", salt="smartmis_foundry_salt"),
    },
    "machining_op": {
        "username": "machining_op",
        "full_name": "Machine Shop Line Operator",
        "role": "Operator",
        "department": "Machine Shop",
        "password_hash": _hash_pw("machining123", salt="smartmis_machining_salt"),
    },
}


def load_users(filepath: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Load users from storage or return defaults."""
    path = filepath or config.USERS_FILE
    users = dict(DEFAULT_USERS)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_dict = json.load(f)
                users.update(user_dict)
        except Exception as e:
            log.warning("Could not read users file %s: %s", path, e)
    return users


def save_users(users: Dict[str, Dict[str, Any]], filepath: Optional[str] = None) -> None:
    """Persist user registry to storage."""
    path = filepath or config.USERS_FILE
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def authenticate_user(username: str, password: str, filepath: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Verify credentials and return authenticated user dictionary or None."""
    users = load_users(filepath)
    user = users.get(username.strip().lower())
    if not user:
        return None
    if _verify_pw(password, user.get("password_hash", "")):
        # Return sanitized user record
        return {
            "username": user["username"],
            "full_name": user.get("full_name", username),
            "role": user.get("role", "Operator"),
            "department": user.get("department", "All"),
        }
    return None


def filter_data_by_role(df: pd.DataFrame, user: Optional[Dict[str, Any]]) -> pd.DataFrame:
    """Enforce departmental scope: Operators only view records for their department."""
    if not user or df.empty:
        return df

    dept_scope = user.get("department", "All")
    if dept_scope != "All" and "department" in df.columns:
        return df[df["department"] == dept_scope].reset_index(drop=True)
    return df


# ==============================================================================
# AUDIT LOGGING ENGINE
# ==============================================================================

def init_audit_db(db_path: Optional[str] = None) -> None:
    """Ensure audit log table exists in central database."""
    path = db_path or config.DB_PATH
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS action_audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        username TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT,
        action TEXT NOT NULL,
        details TEXT
    )
    """)
    con.commit()
    con.close()


def log_audit_action(
    username: str,
    role: str,
    action: str,
    details: str = "",
    department: str = "All",
    db_path: Optional[str] = None,
) -> None:
    """Record an administrative or operational event into the central audit log."""
    path = db_path or config.DB_PATH
    init_audit_db(path)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        con = sqlite3.connect(path)
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO action_audit_log (timestamp, username, role, department, action, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (now_str, username, role, department, action, details),
        )
        con.commit()
        con.close()
    except Exception as e:
        log.warning("Could not write audit log: %s", e)


def get_audit_logs(limit: int = 50, db_path: Optional[str] = None) -> pd.DataFrame:
    """Retrieve recent enterprise audit log entries."""
    path = db_path or config.DB_PATH
    init_audit_db(path)
    con = sqlite3.connect(path)
    try:
        df = pd.read_sql(
            f"SELECT timestamp, username, role, department, action, details FROM action_audit_log ORDER BY id DESC LIMIT {limit}",
            con,
        )
    except Exception:
        con.close()
        return pd.DataFrame()
    con.close()
    return df
