# database.py
# SQLite에 두 가지를 저장한다.
#   profiles  내 설정: 이름표(별명), 학교, 알레르기 번호
#   meals     급식 기록: 나이스 포털에서 받은 급식을 메뉴 한 줄씩 저장한다. 찾기 화면이 여기서 찾는다.

import sqlite3
from datetime import date
from pathlib import Path

from days import from_ymd, now_kst
from foods import parse_dishes

# 이 파일과 같은 폴더에 데이터베이스 저장
DB_PATH = Path(__file__).resolve().parent / "meal_allergy.db"


def connect_db():
    """데이터베이스에 연결한다. 결과를 이름으로 꺼낼 수 있게 row_factory를 정한다."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    """테이블 두 개를 만든다. 이미 있으면 그대로 둔다."""
    conn = connect_db()

    try:
        # allergies는 알레르기 번호를 쉼표로 이은 글자다. 예: "5,10"
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT NOT NULL UNIQUE,
                school_name TEXT NOT NULL,
                school_kind TEXT NOT NULL,
                atpt_code TEXT NOT NULL,
                school_code TEXT NOT NULL,
                allergies TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # allergy_codes는 번호 앞뒤를 쉼표로 감싼 글자다. 예: ",5,6,10,13,"
        # 5번을 ",5,"로 찾으면 15번(",15,")은 걸리지 않는다.
        # 같은 학교·날짜·끼니·메뉴는 한 줄만 남도록 UNIQUE를 건다.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_code TEXT NOT NULL,
                meal_date TEXT NOT NULL,
                meal_name TEXT NOT NULL,
                dish TEXT NOT NULL,
                allergy_codes TEXT NOT NULL,
                saved_at TEXT NOT NULL,
                UNIQUE (school_code, meal_date, meal_name, dish)
            )
            """
        )

        conn.commit()

    finally:
        conn.close()


# ---------- 내 설정 ----------


def save_profile(nickname, school, allergies):
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

    now = now_kst()
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
                    nickname, school_name, school_kind, atpt_code, school_code,
                    allergies, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    nickname,
                    school["name"],
                    school["kind"],
                    school["atpt_code"],
                    school["school_code"],
                    ",".join(codes),
                    now,
                    now,
                ),
            )
        else:
            # 처음 저장한 시각(created_at)은 그대로 두고 나머지만 바꾼다.
            conn.execute(
                """
                UPDATE profiles
                SET school_name = ?, school_kind = ?, atpt_code = ?, school_code = ?,
                    allergies = ?, updated_at = ?
                WHERE nickname = ?
                """,
                (
                    school["name"],
                    school["kind"],
                    school["atpt_code"],
                    school["school_code"],
                    ",".join(codes),
                    now,
                    nickname,
                ),
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
        "allergies": allergies,
        "created_at": row["created_at"],
    }


# ---------- 급식 기록 ----------


def save_meals(school_code, meals):
    """
    나이스 포털에서 받은 급식을 메뉴 한 줄씩 meals 테이블에 저장한다.

    meals는 neis.fetch_meals()가 돌려준 급식 목록이다.
    같은 학교·날짜·끼니·메뉴가 이미 있으면 새 내용으로 바꿔 쓴다(INSERT OR REPLACE).
    """
    now = now_kst()
    conn = connect_db()

    try:
        for meal in meals:
            meal_date = from_ymd(meal["date"]).isoformat()

            for dish, codes in parse_dishes(meal["dishes"]):
                numbers = []

                for code in codes:
                    numbers.append(str(code))

                # 번호가 없는 메뉴(예: 쌀밥)는 빈 글자로 둔다.
                allergy_codes = ""

                if len(numbers) > 0:
                    allergy_codes = "," + ",".join(numbers) + ","

                conn.execute(
                    """
                    INSERT OR REPLACE INTO meals (
                        school_code, meal_date, meal_name, dish, allergy_codes, saved_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (school_code, meal_date, meal["meal"], dish, allergy_codes, now),
                )

        conn.commit()

    finally:
        conn.close()


def search_meals(school_code, keyword="", allergen=None):
    """
    저장된 급식 기록에서 메뉴를 찾는다. 새 날짜부터 놓는다.

    keyword: 메뉴 이름에 들어간 낱말. 띄어쓰기는 빼고 비교한다. 빈 글자면 이름은 따지지 않는다.
    allergen: 알레르기 번호. None이면 번호는 따지지 않는다.
    반환값: 메뉴 목록. 메뉴마다 meal_date(날짜), meal_name(끼니), dish(이름), codes(번호 목록)가 있다.
    """
    word = keyword.replace(" ", "")
    sql = "SELECT * FROM meals WHERE school_code = ? AND REPLACE(dish, ' ', '') LIKE ?"
    values = [school_code, f"%{word}%"]

    if allergen is not None:
        sql += " AND allergy_codes LIKE ?"
        values.append(f"%,{allergen},%")

    sql += " ORDER BY meal_date DESC, id"

    conn = connect_db()

    try:
        rows = conn.execute(sql, values).fetchall()

    finally:
        conn.close()

    found = []

    for row in rows:
        codes = []

        for part in row["allergy_codes"].split(","):
            if part != "":
                codes.append(int(part))

        found.append(
            {
                "meal_date": date.fromisoformat(row["meal_date"]),
                "meal_name": row["meal_name"],
                "dish": row["dish"],
                "codes": codes,
            }
        )

    return found


def count_meals(school_code):
    """그 학교의 저장된 메뉴 기록 수를 센다."""
    conn = connect_db()

    try:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM meals WHERE school_code = ?",
            (school_code,),
        ).fetchone()

    finally:
        conn.close()

    return row["count"]
