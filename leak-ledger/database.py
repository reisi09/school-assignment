# database.py
# 서비스(services), 유출 기록(incidents), 사칭 문자 가려내기 결과(quiz_results)를 SQLite에 저장한다.
# 서비스 하나에 유출 기록이 여러 건 달릴 수 있다.

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
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
    """테이블 세 개를 생성한다."""
    conn = connect_db()

    try:
        cursor = conn.cursor()

        # name은 대소문자를 구분하지 않고(COLLATE NOCASE) 겹칠 수 없다(UNIQUE).
        # account_label(계정 별칭)은 화면에서 입력 칸을 없애서 지금은 빈 값으로 저장한다.
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

        # 사칭 문자 가려내기를 한 번 끝낼 때마다 한 줄씩 쌓인다.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                score INTEGER NOT NULL,
                total INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        conn.commit()

    finally:
        conn.close()


def check_record(name, items, notified_date):
    """
    기록에 넣을 값이 올바른지 확인한다.

    반환값: SUCCESS / EMPTY(빈 이름) / NO_ITEMS(유출된 정보 없음) / FUTURE_DATE(오늘 이후 날짜)
    """
    if name == "":
        return "EMPTY"

    if len(items) == 0:
        return "NO_ITEMS"

    if notified_date > today_kst():
        return "FUTURE_DATE"

    return "SUCCESS"


def add_record(name, category, memo, notified_date, items, leak_size):
    """
    유출 알림 한 건을 기록한다. 위험 점수와 할 일은 코드가 계산한다.
    처음 적는 서비스면 서비스도 함께 등록한다.

    반환값: SUCCESS / EMPTY / NO_ITEMS / FUTURE_DATE (check_record 참고)
    """
    name = name.strip()
    memo = memo.strip()

    status = check_record(name, items, notified_date)

    if status != "SUCCESS":
        return status

    actions = []

    for action_name in make_actions(items):
        actions.append({"name": action_name, "done": False, "done_date": None})

    conn = connect_db()

    try:
        # 이름이 같은 서비스가 이미 있으면 그 서비스에 기록을 더한다.
        row = conn.execute(
            "SELECT id FROM services WHERE name = ?",
            (name,),
        ).fetchone()

        if row is None:
            cursor = conn.execute(
                """
                INSERT INTO services (name, category, account_label, memo, created_at)
                VALUES (?, ?, '', ?, ?)
                """,
                (name, category, memo, now_kst()),
            )
            service_id = cursor.lastrowid
        else:
            service_id = row["id"]

            # 메모를 새로 적었으면 서비스의 메모를 바꾼다.
            if memo != "":
                conn.execute(
                    "UPDATE services SET memo = ? WHERE id = ?",
                    (memo, service_id),
                )

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

        # 서비스와 기록을 한 번에 확정한다. 중간에 실패하면 둘 다 저장되지 않는다.
        conn.commit()

    finally:
        conn.close()

    return "SUCCESS"


def add_case(case):
    """
    실제 유출 사례(cases.py) 하나를 기록한다.

    반환값: SUCCESS / DUPLICATE(이미 기록한 사례)
    """
    if case["name"].casefold() in get_recorded_names():
        return "DUPLICATE"

    # 날짜가 출처에 없는 사례는 오늘 날짜로 기록한다.
    if case["date"] is None:
        notified_date = today_kst()
    else:
        notified_date = date.fromisoformat(case["date"])

    return add_record(
        case["name"],
        case["category"],
        "",
        notified_date,
        case["items"],
        case["size"],
    )


def update_record(incident_id, name, category, memo, notified_date, items, leak_size):
    """
    기록 한 건을 고친다. 위험 점수와 할 일을 다시 정하고, 이미 끝낸 할 일은 그대로 둔다.
    서비스의 이름·분류·메모도 함께 바꾼다.

    반환값: SUCCESS / EMPTY / NO_ITEMS / FUTURE_DATE
            DUPLICATE(다른 서비스가 쓰는 이름) / NOT_FOUND(이미 지워진 기록)
    """
    name = name.strip()
    memo = memo.strip()

    status = check_record(name, items, notified_date)

    if status != "SUCCESS":
        return status

    conn = connect_db()

    try:
        row = conn.execute(
            "SELECT service_id, actions FROM incidents WHERE id = ?",
            (incident_id,),
        ).fetchone()

        if row is None:
            return "NOT_FOUND"

        service_id = row["service_id"]

        # 다른 서비스가 같은 이름을 쓰고 있으면 바꿀 수 없다.
        other = conn.execute(
            "SELECT id FROM services WHERE name = ? AND id != ?",
            (name, service_id),
        ).fetchone()

        if other is not None:
            return "DUPLICATE"

        # 지금까지의 할 일을 이름으로 찾을 수 있게 담아 둔다.
        old_actions = {}

        for action in json.loads(row["actions"]):
            old_actions[action["name"]] = action

        # 바뀐 정보로 할 일을 다시 정한다. 이름이 같은 할 일은 끝낸 상태를 그대로 둔다.
        actions = []
        resolved = 1

        for action_name in make_actions(items):
            if action_name in old_actions:
                action = old_actions[action_name]
            else:
                action = {"name": action_name, "done": False, "done_date": None}

            if not action["done"]:
                resolved = 0

            actions.append(action)

        conn.execute(
            "UPDATE services SET name = ?, category = ?, memo = ? WHERE id = ?",
            (name, category, memo, service_id),
        )
        conn.execute(
            """
            UPDATE incidents
            SET leaked_items = ?, risk_score = ?, leak_size = ?,
                notified_date = ?, actions = ?, resolved = ?
            WHERE id = ?
            """,
            (
                ",".join(items),
                calc_risk_score(items),
                leak_size,
                notified_date.isoformat(),
                json.dumps(actions, ensure_ascii=False),
                resolved,
                incident_id,
            ),
        )

        conn.commit()

    finally:
        conn.close()

    return "SUCCESS"


def delete_record(incident_id):
    """기록 한 건을 지운다. 그 서비스에 남은 기록이 없으면 서비스도 지운다."""
    conn = connect_db()

    try:
        row = conn.execute(
            "SELECT service_id FROM incidents WHERE id = ?",
            (incident_id,),
        ).fetchone()

        # 이미 지워진 기록이면 할 일이 없다.
        if row is None:
            return

        service_id = row["service_id"]

        conn.execute("DELETE FROM incidents WHERE id = ?", (incident_id,))

        left = conn.execute(
            "SELECT COUNT(*) AS count FROM incidents WHERE service_id = ?",
            (service_id,),
        ).fetchone()

        if left["count"] == 0:
            conn.execute("DELETE FROM services WHERE id = ?", (service_id,))

        conn.commit()

    finally:
        conn.close()


def get_recorded_names():
    """기록이 있는 서비스의 이름을 모두 돌려준다. 비교하기 쉽게 소문자로 바꾼 집합이다."""
    conn = connect_db()

    try:
        names = set()

        for row in conn.execute("SELECT name FROM services").fetchall():
            names.add(row["name"].casefold())

        return names

    finally:
        conn.close()


def get_incidents(keyword="", status="전체"):
    """
    유출 기록을 서비스의 이름·분류·메모와 함께 조회한다.

    keyword는 서비스 이름의 일부, status는 전체 / 진행 중 / 완료 중 하나다.
    진행 중인 기록, 위험 점수가 높은 기록 순서로 돌려준다.
    """
    sql = """
        SELECT incidents.*,
               services.name AS service_name,
               services.category,
               services.memo
        FROM incidents
        JOIN services ON services.id = incidents.service_id
        WHERE services.name LIKE ?
    """
    params = [f"%{keyword.strip()}%"]

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
    """할 일의 상태를 저장한다. 모든 할 일이 끝나면 완료(1)로 표시한다."""
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
    """비밀번호 확인 결과를 횟수만 저장한다."""
    conn = connect_db()

    try:
        conn.execute(
            "UPDATE incidents SET pwned_count = ? WHERE id = ?",
            (count, incident_id),
        )

        conn.commit()

    finally:
        conn.close()


def add_quiz_result(score, total):
    """사칭 문자 가려내기 결과(맞힌 개수, 문제 수)를 저장한다."""
    conn = connect_db()

    try:
        conn.execute(
            "INSERT INTO quiz_results (score, total, created_at) VALUES (?, ?, ?)",
            (score, total, now_kst()),
        )

        conn.commit()

    finally:
        conn.close()


def get_quiz_summary():
    """
    사칭 문자 가려내기 결과를 요약한다.

    반환값: (최고 점수, 푼 횟수). 아직 푼 적이 없으면 최고 점수는 None이다.
    """
    conn = connect_db()

    try:
        row = conn.execute(
            "SELECT MAX(score) AS best, COUNT(*) AS count FROM quiz_results"
        ).fetchone()

        return row["best"], row["count"]

    finally:
        conn.close()
