# database.py
# 학생이 직접 등록하는 자료를 SQLite에 저장한다.
#   profiles      내 설정: 이름표(별명), 학교, 학년, 반, 알레르기
#   class_events  우리 반 일정: 수행평가·과제·시험 (같은 학교·학년·반 친구들이 함께 본다)
#   meal_reviews  급식 평가: 메뉴별 별점과 한줄평
# 급식·시간표·학사일정은 나이스 포털에서 받아 오므로 여기에 저장하지 않는다.

import sqlite3
from datetime import date
from pathlib import Path

from days import now_kst

# 이 파일과 같은 폴더에 데이터베이스 저장
DB_PATH = Path(__file__).resolve().parent / "school_today.db"


def connect_db():
    """데이터베이스에 연결한다. 결과를 이름으로 꺼낼 수 있게 row_factory를 정한다."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    """테이블 세 개를 만든다. 이미 있으면 그대로 둔다."""
    conn = connect_db()

    try:
        # allergies는 알레르기 번호를 쉼표로 이은 글자다. 예: "5,10"
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT NOT NULL UNIQUE,
                atpt_code TEXT NOT NULL,
                school_code TEXT NOT NULL,
                school_name TEXT NOT NULL,
                school_kind TEXT NOT NULL,
                grade INTEGER NOT NULL,
                class_nm INTEGER NOT NULL,
                allergies TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # due_date는 2026-11-20 모양의 글자다. 글자끼리 비교해도 날짜 순서가 맞다.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS class_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_code TEXT NOT NULL,
                grade INTEGER NOT NULL,
                class_nm INTEGER NOT NULL,
                kind TEXT NOT NULL,
                subject TEXT NOT NULL,
                title TEXT NOT NULL,
                due_date TEXT NOT NULL,
                memo TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meal_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_code TEXT NOT NULL,
                meal_date TEXT NOT NULL,
                dish TEXT NOT NULL,
                stars INTEGER NOT NULL,
                comment TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        conn.commit()

    finally:
        conn.close()


# ---------- 내 설정 ----------


def save_profile(nickname, school, grade, class_nm, allergies):
    """
    내 설정을 이름표로 저장한다. 같은 이름표가 있으면 내용을 바꾼다.

    school은 neis.py가 돌려준 학교(이름, 종류, 교육청 코드, 학교 코드)다.
    allergies는 알레르기 번호 목록이다.
    반환값: SUCCESS / EMPTY(빈 이름표)
    """
    nickname = nickname.strip()

    if nickname == "":
        return "EMPTY"

    codes = []

    for code in allergies:
        codes.append(str(code))

    values = (
        school["atpt_code"],
        school["school_code"],
        school["name"],
        school["kind"],
        grade,
        class_nm,
        ",".join(codes),
        now_kst(),
        nickname,
    )

    conn = connect_db()

    try:
        found = conn.execute(
            "SELECT id FROM profiles WHERE nickname = ?",
            (nickname,),
        ).fetchone()

        if found is None:
            conn.execute(
                """
                INSERT INTO profiles (
                    atpt_code, school_code, school_name, school_kind,
                    grade, class_nm, allergies, updated_at, nickname
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
        else:
            conn.execute(
                """
                UPDATE profiles
                SET atpt_code = ?, school_code = ?, school_name = ?, school_kind = ?,
                    grade = ?, class_nm = ?, allergies = ?, updated_at = ?
                WHERE nickname = ?
                """,
                values,
            )

        conn.commit()

    finally:
        conn.close()

    return "SUCCESS"


def load_profile(nickname):
    """이름표로 내 설정을 불러온다. 없으면 None이다."""
    conn = connect_db()

    try:
        row = conn.execute(
            "SELECT * FROM profiles WHERE nickname = ?",
            (nickname.strip(),),
        ).fetchone()

    finally:
        conn.close()

    if row is None:
        return None

    allergies = []

    for part in row["allergies"].split(","):
        if part != "":
            allergies.append(int(part))

    return {
        "nickname": row["nickname"],
        "school": {
            "name": row["school_name"],
            "kind": row["school_kind"],
            "atpt_code": row["atpt_code"],
            "school_code": row["school_code"],
        },
        "grade": row["grade"],
        "class_nm": row["class_nm"],
        "allergies": allergies,
    }


# ---------- 우리 반 일정 ----------


def add_event(school_code, grade, class_nm, kind, subject, title, due_date, memo):
    """
    우리 반 일정 하나를 등록한다.

    반환값: SUCCESS / NO_SUBJECT(빈 과목) / NO_TITLE(빈 내용)
    """
    subject = subject.strip()
    title = title.strip()

    if subject == "":
        return "NO_SUBJECT"

    if title == "":
        return "NO_TITLE"

    conn = connect_db()

    try:
        conn.execute(
            """
            INSERT INTO class_events (
                school_code, grade, class_nm, kind, subject, title, due_date, memo, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                school_code,
                grade,
                class_nm,
                kind,
                subject,
                title,
                due_date.isoformat(),
                memo.strip(),
                now_kst(),
            ),
        )

        conn.commit()

    finally:
        conn.close()

    return "SUCCESS"


def get_events(school_code, grade, class_nm, start, end, keyword=""):
    """
    한 반의 start~end 일정을 날짜 순서로 돌려준다.

    keyword를 주면 과목, 내용, 메모에 그 낱말이 들어간 일정만 돌려준다.
    일정마다 due_date는 날짜로 바꿔 돌려준다.
    """
    pattern = f"%{keyword.strip()}%"

    conn = connect_db()

    try:
        rows = conn.execute(
            """
            SELECT * FROM class_events
            WHERE school_code = ? AND grade = ? AND class_nm = ?
              AND due_date BETWEEN ? AND ?
              AND (subject LIKE ? OR title LIKE ? OR memo LIKE ?)
            ORDER BY due_date, id
            """,
            (
                school_code,
                grade,
                class_nm,
                start.isoformat(),
                end.isoformat(),
                pattern,
                pattern,
                pattern,
            ),
        ).fetchall()

    finally:
        conn.close()

    events = []

    for row in rows:
        event = dict(row)
        event["due_date"] = date.fromisoformat(event["due_date"])
        events.append(event)

    return events


def delete_event(event_id):
    """우리 반 일정 하나를 지운다."""
    conn = connect_db()

    try:
        conn.execute("DELETE FROM class_events WHERE id = ?", (event_id,))
        conn.commit()

    finally:
        conn.close()


# ---------- 급식 평가 ----------


def add_review(school_code, meal_date, dish, stars, comment):
    """
    급식 메뉴 하나에 별점(1~5)과 한줄평을 남긴다.

    반환값: SUCCESS / NO_DISH(메뉴를 안 고름) / NO_STARS(별점을 안 고름)
    """
    if dish is None or dish == "":
        return "NO_DISH"

    if stars is None or not 1 <= stars <= 5:
        return "NO_STARS"

    conn = connect_db()

    try:
        conn.execute(
            """
            INSERT INTO meal_reviews (school_code, meal_date, dish, stars, comment, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (school_code, meal_date.isoformat(), dish, stars, comment.strip(), now_kst()),
        )

        conn.commit()

    finally:
        conn.close()

    return "SUCCESS"


def get_top_dishes(school_code, limit=5):
    """
    평균 별점이 높은 메뉴 순서로 (메뉴, 평균 별점, 평가 수) 목록을 돌려준다.

    평균이 같으면 평가가 많은 메뉴가 앞에 온다.
    """
    conn = connect_db()

    try:
        rows = conn.execute(
            """
            SELECT dish, AVG(stars) AS average, COUNT(*) AS count
            FROM meal_reviews
            WHERE school_code = ?
            GROUP BY dish
            ORDER BY average DESC, count DESC, dish
            LIMIT ?
            """,
            (school_code, limit),
        ).fetchall()

    finally:
        conn.close()

    top = []

    for row in rows:
        top.append((row["dish"], round(row["average"], 1), row["count"]))

    return top


def get_recent_reviews(school_code, limit=5):
    """최근에 남긴 한줄평을 새것부터 돌려준다. 한줄평이 빈 평가는 뺀다."""
    conn = connect_db()

    try:
        rows = conn.execute(
            """
            SELECT * FROM meal_reviews
            WHERE school_code = ? AND comment != ''
            ORDER BY id DESC
            LIMIT ?
            """,
            (school_code, limit),
        ).fetchall()

    finally:
        conn.close()

    reviews = []

    for row in rows:
        review = dict(row)
        review["meal_date"] = date.fromisoformat(review["meal_date"])
        reviews.append(review)

    return reviews
