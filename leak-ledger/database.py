# database.py
# 가입 서비스(services)와 유출 기록(incidents)을 SQLite에 저장한다.

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rules import calc_risk_score, make_actions

# 이 파일과 같은 폴더에 데이터베이스 저장
DB_PATH = Path(__file__).resolve().parent / "leak_ledger.db"

# 한국 시간(KST)
KST = timezone(timedelta(hours=9))


def now_kst():
    """현재 시각을 KST ISO 형식 문자열로 돌려준다."""
    return datetime.now(KST).isoformat(timespec="seconds")


def today_kst():
    """KST 기준 오늘 날짜를 돌려준다."""
    return datetime.now(KST).date()


def connect_db():
    """데이터베이스에 연결한다."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():
    """서비스와 유출 기록 테이블을 생성한다."""
    conn = connect_db()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                category TEXT NOT NULL,
                account_label TEXT NOT NULL,
                memo TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                leaked_items TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                leak_size INTEGER NOT NULL,
                resolved INTEGER NOT NULL,
                notified_date TEXT NOT NULL,
                actions TEXT NOT NULL,
                pwned_count INTEGER,
                service_id INTEGER NOT NULL REFERENCES services (id),
                created_at TEXT NOT NULL
            )
            """
        )

        conn.commit()

    finally:
        conn.close()


def add_service(name, category, account_label, memo):
    """
    가입한 서비스를 저장한다.

    반환값: SUCCESS / EMPTY(빈 이름) / DUPLICATE(이미 있는 이름)
    """
    name = name.strip()

    if name == "":
        return "EMPTY"

    conn = connect_db()

    try:
        conn.execute(
            """
            INSERT INTO services (name, category, account_label, memo, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, category, account_label.strip(), memo.strip(), now_kst()),
        )

        conn.commit()

    except sqlite3.IntegrityError:
        # name 열의 UNIQUE 조건에 걸린 경우
        return "DUPLICATE"

    finally:
        conn.close()

    return "SUCCESS"


def get_services(keyword="", category="전체"):
    """이름에 검색어가 포함된 서비스를 ID 순서로 조회한다."""
    sql = "SELECT * FROM services WHERE name LIKE ?"
    params = [f"%{keyword.strip()}%"]

    if category != "전체":
        sql += " AND category = ?"
        params.append(category)

    conn = connect_db()

    try:
        rows = conn.execute(sql + " ORDER BY id", params).fetchall()
        return [dict(row) for row in rows]

    finally:
        conn.close()


def add_incident(service_id, notified_date, items, leak_size):
    """
    유출 기록을 저장한다. 위험 점수와 권장 조치는 코드가 계산한다.

    반환값: SUCCESS / NO_ITEMS(유출 항목 없음) / FUTURE_DATE(오늘 이후 통지일)
    """
    if len(items) == 0:
        return "NO_ITEMS"

    if notified_date > today_kst():
        return "FUTURE_DATE"

    actions = []

    for name in make_actions(items):
        actions.append({"name": name, "done": False, "done_date": None})

    conn = connect_db()

    try:
        conn.execute(
            """
            INSERT INTO incidents (
                leaked_items, risk_score, leak_size, resolved,
                notified_date, actions, pwned_count, service_id, created_at
            )
            VALUES (?, ?, ?, 0, ?, ?, NULL, ?, ?)
            """,
            (
                ",".join(items),
                calc_risk_score(items),
                leak_size,
                notified_date.isoformat(),
                json.dumps(actions, ensure_ascii=False),
                service_id,
                now_kst(),
            ),
        )

        conn.commit()

    finally:
        conn.close()

    return "SUCCESS"


def get_incidents(keyword="", category="전체", status="전체"):
    """
    유출 기록을 서비스 정보와 함께 조회한다.

    진행 중인 기록, 위험 점수가 높은 기록 순서로 돌려준다.
    """
    sql = """
        SELECT incidents.*, services.name AS service_name, services.category
        FROM incidents
        JOIN services ON services.id = incidents.service_id
        WHERE services.name LIKE ?
    """
    params = [f"%{keyword.strip()}%"]

    if category != "전체":
        sql += " AND services.category = ?"
        params.append(category)

    if status == "진행 중":
        sql += " AND incidents.resolved = 0"
    elif status == "완료":
        sql += " AND incidents.resolved = 1"

    sql += " ORDER BY incidents.resolved, incidents.risk_score DESC, incidents.id DESC"

    conn = connect_db()

    try:
        incidents = []

        for row in conn.execute(sql, params).fetchall():
            incident = dict(row)
            incident["leaked_items"] = incident["leaked_items"].split(",")
            incident["actions"] = json.loads(incident["actions"])
            incidents.append(incident)

        return incidents

    finally:
        conn.close()


def save_actions(incident_id, actions):
    """조치 상태를 저장한다. 모든 조치가 끝나면 대응 완료(1)로 표시한다."""
    resolved = 1

    for action in actions:
        if not action["done"]:
            resolved = 0

    conn = connect_db()

    try:
        conn.execute(
            "UPDATE incidents SET actions = ?, resolved = ? WHERE id = ?",
            (json.dumps(actions, ensure_ascii=False), resolved, incident_id),
        )

        conn.commit()

    finally:
        conn.close()


def save_pwned_count(incident_id, count):
    """비밀번호 유출 목록 조회 결과를 횟수만 저장한다."""
    conn = connect_db()

    try:
        conn.execute(
            "UPDATE incidents SET pwned_count = ? WHERE id = ?",
            (count, incident_id),
        )

        conn.commit()

    finally:
        conn.close()
