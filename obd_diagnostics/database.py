"""
Модуль работы с базой данных SQLite для хранения истории диагностики
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import config

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    """Создаёт и возвращает соединение с базой данных."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализирует схему базы данных."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT    NOT NULL,
                vin         TEXT,
                car_brand   TEXT,
                port        TEXT,
                scan_type   TEXT    NOT NULL DEFAULT 'live',
                duration_s  INTEGER,
                notes       TEXT
            );

            CREATE TABLE IF NOT EXISTS readings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL REFERENCES sessions(id),
                timestamp   TEXT    NOT NULL,
                pid_name    TEXT    NOT NULL,
                pid_code    TEXT,
                value       REAL,
                unit        TEXT,
                raw_value   TEXT,
                status      TEXT    DEFAULT 'ok'
            );

            CREATE TABLE IF NOT EXISTS dtc_codes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL REFERENCES sessions(id),
                code        TEXT    NOT NULL,
                description TEXT,
                type        TEXT    DEFAULT 'confirmed',
                severity    TEXT    DEFAULT 'unknown'
            );

            CREATE TABLE IF NOT EXISTS ai_reports (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL REFERENCES sessions(id),
                timestamp   TEXT    NOT NULL,
                report_text TEXT    NOT NULL,
                model       TEXT
            );

            CREATE TABLE IF NOT EXISTS anomalies (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL REFERENCES sessions(id),
                pid_name    TEXT    NOT NULL,
                value       REAL,
                unit        TEXT,
                expected_min REAL,
                expected_max REAL,
                severity    TEXT    DEFAULT 'warning'
            );

            CREATE INDEX IF NOT EXISTS idx_readings_session ON readings(session_id);
            CREATE INDEX IF NOT EXISTS idx_dtc_session ON dtc_codes(session_id);
        """)
    logger.info("База данных инициализирована: %s", config.DB_PATH)


def create_session(vin: Optional[str] = None, car_brand: str = "generic",
                   port: str = "", scan_type: str = "live") -> int:
    """Создаёт новую сессию диагностики и возвращает её ID."""
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (timestamp, vin, car_brand, port, scan_type) VALUES (?,?,?,?,?)",
            (datetime.now().isoformat(), vin, car_brand, port, scan_type)
        )
        return cur.lastrowid


def close_session(session_id: int, duration_s: Optional[int] = None, notes: str = ""):
    """Закрывает сессию — записывает продолжительность и заметки."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE sessions SET duration_s=?, notes=? WHERE id=?",
            (duration_s, notes, session_id)
        )


def save_reading(session_id: int, pid_name: str, value: Optional[float],
                 unit: str = "", raw_value: str = "", pid_code: str = "",
                 status: str = "ok"):
    """Сохраняет одно показание датчика."""
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO readings
               (session_id, timestamp, pid_name, pid_code, value, unit, raw_value, status)
               VALUES (?,?,?,?,?,?,?,?)""",
            (session_id, datetime.now().isoformat(), pid_name, pid_code,
             value, unit, raw_value, status)
        )


def save_readings_bulk(session_id: int, readings: List[Dict[str, Any]]):
    """Массовое сохранение показаний."""
    with get_connection() as conn:
        conn.executemany(
            """INSERT INTO readings
               (session_id, timestamp, pid_name, pid_code, value, unit, raw_value, status)
               VALUES (:session_id, :timestamp, :pid_name, :pid_code,
                       :value, :unit, :raw_value, :status)""",
            [{
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "pid_name": r.get("name", ""),
                "pid_code": r.get("code", ""),
                "value": r.get("value"),
                "unit": r.get("unit", ""),
                "raw_value": str(r.get("raw", "")),
                "status": r.get("status", "ok"),
            } for r in readings]
        )


def save_dtc_codes(session_id: int, codes: List[Dict[str, Any]]):
    """Сохраняет коды неисправностей."""
    if not codes:
        return
    with get_connection() as conn:
        conn.executemany(
            """INSERT INTO dtc_codes (session_id, code, description, type, severity)
               VALUES (:session_id, :code, :description, :type, :severity)""",
            [{
                "session_id": session_id,
                "code": c.get("code", ""),
                "description": c.get("description", ""),
                "type": c.get("type", "confirmed"),
                "severity": c.get("severity", "unknown"),
            } for c in codes]
        )


def save_anomalies(session_id: int, anomalies: List[Dict[str, Any]]):
    """Сохраняет обнаруженные аномалии."""
    if not anomalies:
        return
    with get_connection() as conn:
        conn.executemany(
            """INSERT INTO anomalies
               (session_id, pid_name, value, unit, expected_min, expected_max, severity)
               VALUES (:session_id, :pid_name, :value, :unit,
                       :expected_min, :expected_max, :severity)""",
            [{
                "session_id": session_id,
                "pid_name": a.get("pid_name", ""),
                "value": a.get("value"),
                "unit": a.get("unit", ""),
                "expected_min": a.get("expected_min"),
                "expected_max": a.get("expected_max"),
                "severity": a.get("severity", "warning"),
            } for a in anomalies]
        )


def save_ai_report(session_id: int, report_text: str, model: str = "gpt-4o-mini"):
    """Сохраняет AI-отчёт."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO ai_reports (session_id, timestamp, report_text, model) VALUES (?,?,?,?)",
            (session_id, datetime.now().isoformat(), report_text, model)
        )


def get_sessions(limit: int = 100) -> List[Dict]:
    """Возвращает список последних сессий."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT s.*, 
               (SELECT COUNT(*) FROM dtc_codes WHERE session_id=s.id) as dtc_count,
               (SELECT COUNT(*) FROM anomalies WHERE session_id=s.id) as anomaly_count
               FROM sessions s ORDER BY s.timestamp DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_session_detail(session_id: int) -> Dict:
    """Возвращает полные данные сессии."""
    with get_connection() as conn:
        session = dict(conn.execute(
            "SELECT * FROM sessions WHERE id=?", (session_id,)
        ).fetchone() or {})

        readings = [dict(r) for r in conn.execute(
            "SELECT * FROM readings WHERE session_id=? ORDER BY timestamp",
            (session_id,)
        ).fetchall()]

        dtcs = [dict(r) for r in conn.execute(
            "SELECT * FROM dtc_codes WHERE session_id=?", (session_id,)
        ).fetchall()]

        anomalies = [dict(r) for r in conn.execute(
            "SELECT * FROM anomalies WHERE session_id=?", (session_id,)
        ).fetchall()]

        report_row = conn.execute(
            "SELECT report_text FROM ai_reports WHERE session_id=? ORDER BY timestamp DESC LIMIT 1",
            (session_id,)
        ).fetchone()
        report = report_row["report_text"] if report_row else ""

        return {
            "session": session,
            "readings": readings,
            "dtcs": dtcs,
            "anomalies": anomalies,
            "ai_report": report,
        }


def get_recent_readings_for_pid(pid_name: str, limit: int = 50) -> List[Dict]:
    """Возвращает последние показания конкретного датчика (для графиков)."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT r.timestamp, r.value, r.unit FROM readings r
               JOIN sessions s ON s.id=r.session_id
               WHERE r.pid_name=? ORDER BY r.timestamp DESC LIMIT ?""",
            (pid_name, limit)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]
