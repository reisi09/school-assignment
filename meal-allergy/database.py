# database.py
# SQLite에 세 가지를 저장한다.
#   users        계정: 아이디, 비밀번호 해시, 복구 코드 해시, 내 학교, 내 알레르기 번호
#   watch_words  주의 낱말: 번호로 표시되지 않는 재료(예: 아몬드)를 사용자가 직접 등록한다.
#   meals        급식 기록: 나이스 포털에서 받은 급식을 메뉴 한 줄씩 저장한다. 찾기 화면이 여기서 찾는다.
#
# 비밀번호와 복구 코드는 원래 글자를 저장하지 않는다. 소금(salt)을 섞어 해시로 바꾼 값만 저장해서,
# 데이터베이스 파일을 열어 봐도 원래 글자를 알 수 없다.

import hashlib
import hmac
import secrets
import sqlite3
from datetime import date
from pathlib import Path

from days import from_ymd, now_kst
from foods import parse_dishes

# 이 파일과 같은 폴더에 데이터베이스 저장
DB_PATH = Path(__file__).resolve().parent / "meal_allergy.db"

# 아이디 글자 수와 비밀번호 최소 글자 수
USERNAME_MIN = 3
USERNAME_MAX = 20
PASSWORD_MIN = 8

# 비밀번호 해시를 만들 때 되풀이하는 횟수. 많을수록 비밀번호를 하나씩 맞혀 보는 공격이 느려진다.
HASH_ROUNDS = 200_000

# 복구 코드에 쓰는 글자. 헷갈리기 쉬운 0·O·1·I는 뺐다.
RECOVERY_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# 주의 낱말의 최대 글자 수
WORD_MAX = 20


def connect_db():
    """데이터베이스에 연결한다. 결과를 이름으로 꺼낼 수 있게 row_factory를 정한다."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def column_names(conn, table):
    """테이블의 칸 이름 목록을 돌려준다. 테이블이 없으면 빈 목록이다."""
    names = []

    for row in conn.execute(f"PRAGMA table_info({table})").fetchall():
        names.append(row["name"])

    return names


def create_tables():
    """테이블 세 개를 만든다. 이미 있으면 그대로 두고, 예전 모양이면 새 모양으로 고친다."""
    conn = connect_db()

    try:
        # 예전 버전이 만든 users에는 recovery_hash 칸이 없다. 칸을 붙이고 값은 빈 글자로 둔다.
        # 그런 계정은 로그인은 그대로 되지만 복구 코드가 없어서 비밀번호 찾기는 쓸 수 없다.
        users_columns = column_names(conn, "users")

        if len(users_columns) > 0 and "recovery_hash" not in users_columns:
            conn.execute("ALTER TABLE users ADD COLUMN recovery_hash TEXT NOT NULL DEFAULT ''")

        # 예전 meals에는 지금 쓰지 않는 saved_at 칸이 있다. 급식 기록은 나이스에서 다시 받으면 되므로
        # 테이블을 지우고 아래에서 새로 만든다.
        if "saved_at" in column_names(conn, "meals"):
            conn.execute("DROP TABLE meals")

        # username에 UNIQUE를 걸어 같은 아이디가 두 번 저장되지 않게 한다.
        # allergies는 알레르기 번호를 쉼표로 이은 글자다. 예: "5,10"
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                recovery_hash TEXT NOT NULL,
                school_name TEXT NOT NULL,
                school_kind TEXT NOT NULL,
                atpt_code TEXT NOT NULL,
                school_code TEXT NOT NULL,
                allergies TEXT NOT NULL,
                created_at TEXT NOT NULL
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
                UNIQUE (school_code, meal_date, meal_name, dish)
            )
            """
        )

        # 주의 낱말: 한 사람이 같은 낱말을 두 번 등록하지 못하도록 (user_id, word)에 UNIQUE를 건다.
        # user_id는 users.id를 가리킨다.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watch_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                memo TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (user_id, word)
            )
            """
        )

        conn.commit()

    finally:
        conn.close()


# ---------- 비밀번호와 복구 코드 ----------


def hash_password(password, salt=None):
    """
    비밀번호를 해시로 바꾼다. 결과는 "소금$해시" 모양의 글자다. 복구 코드도 이 함수로 바꾼다.

    소금(salt)은 계정마다 다른 무작위 글자다. 그래서 같은 비밀번호라도 저장되는 글자가 달라진다.
    """
    if salt is None:
        salt = secrets.token_hex(16)

    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), HASH_ROUNDS).hex()

    return salt + "$" + digest


def check_password(password, stored):
    """입력한 비밀번호가 저장된 해시와 맞는지 확인한다."""
    salt = stored.split("$")[0]

    # compare_digest는 비교에 걸리는 시간이 늘 같아서, 걸린 시간으로 답을 짐작할 수 없다.
    return hmac.compare_digest(hash_password(password, salt), stored)


def make_recovery_code():
    """비밀번호를 잊었을 때 쓸 복구 코드를 만든다. 예: K7QM-3XRP-9DTA"""
    letters = ""

    # secrets.choice는 맞히기 어려운 무작위 글자를 고른다. 12글자를 뽑는다.
    for number in range(12):
        letters += secrets.choice(RECOVERY_LETTERS)

    return letters[0:4] + "-" + letters[4:8] + "-" + letters[8:12]


def normalize_code(code):
    """복구 코드를 비교하기 좋게 바꾼다. 소문자는 대문자로, 하이픈과 띄어쓰기는 뺀다."""
    return code.upper().replace("-", "").replace(" ", "")


def check_new_password(password, password_confirm):
    """새 비밀번호를 확인한다. 반환값: OK / SHORT_PASSWORD(8자보다 짧음) / MISMATCH(확인이 다름)"""
    if len(password) < PASSWORD_MIN:
        return "SHORT_PASSWORD"

    if password != password_confirm:
        return "MISMATCH"

    return "OK"


# ---------- 계정 ----------


def user_from_row(row):
    """users 테이블의 한 줄을 화면이 쓰는 계정 정보로 바꾼다. 해시는 넣지 않는다."""
    allergies = []

    for part in row["allergies"].split(","):
        if part != "":
            allergies.append(int(part))

    return {
        "id": row["id"],
        "username": row["username"],
        "school": {
            "name": row["school_name"],
            "kind": row["school_kind"],
            "atpt_code": row["atpt_code"],
            "school_code": row["school_code"],
        },
        "allergies": allergies,
    }


def create_user(username, password, password_confirm, school, recovery_code):
    """
    회원가입: 아이디와 비밀번호를 확인하고 계정을 만든다. 처음 학교는 school이고 알레르기는 없다.

    recovery_code는 make_recovery_code()로 만든 복구 코드다. 해시로 바꿔 저장한다.
    반환값: SUCCESS / BAD_USERNAME(3~20자가 아님) / SHORT_PASSWORD(8자보다 짧음)
            MISMATCH(비밀번호 확인이 다름) / TAKEN(이미 있는 아이디)
    """
    username = username.strip()

    if not USERNAME_MIN <= len(username) <= USERNAME_MAX:
        return "BAD_USERNAME"

    status = check_new_password(password, password_confirm)

    if status != "OK":
        return status

    conn = connect_db()

    try:
        conn.execute(
            """
            INSERT INTO users (
                username, password_hash, recovery_hash, school_name, school_kind,
                atpt_code, school_code, allergies, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                hash_password(password),
                hash_password(normalize_code(recovery_code)),
                school["name"],
                school["kind"],
                school["atpt_code"],
                school["school_code"],
                "",
                now_kst(),
            ),
        )
        conn.commit()

    except sqlite3.IntegrityError:
        # username에 UNIQUE가 걸려 있어서 같은 아이디가 이미 있으면 이 오류가 난다.
        return "TAKEN"

    finally:
        conn.close()

    return "SUCCESS"


def login(username, password):
    """아이디와 비밀번호가 맞으면 계정 정보를, 틀리면 None을 돌려준다."""
    conn = connect_db()

    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()

    finally:
        conn.close()

    if row is None:
        return None

    if not check_password(password, row["password_hash"]):
        return None

    return user_from_row(row)


def reset_password(username, recovery_code, new_password, new_password_confirm, new_recovery_code):
    """
    비밀번호 찾기: 복구 코드가 맞으면 비밀번호를 바꾸고, 복구 코드도 새것으로 바꾼다.

    쓴 복구 코드는 다시 쓸 수 없다. new_recovery_code는 make_recovery_code()로 만든 새 코드다.
    반환값: SUCCESS / SHORT_PASSWORD / MISMATCH / WRONG_CODE(아이디나 복구 코드가 틀림)
    """
    status = check_new_password(new_password, new_password_confirm)

    if status != "OK":
        return status

    conn = connect_db()

    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()

        # 아이디가 없을 때와 코드가 틀렸을 때를 구분해 알려 주지 않는다.
        if row is None or not check_password(normalize_code(recovery_code), row["recovery_hash"]):
            return "WRONG_CODE"

        conn.execute(
            "UPDATE users SET password_hash = ?, recovery_hash = ? WHERE id = ?",
            (
                hash_password(new_password),
                hash_password(normalize_code(new_recovery_code)),
                row["id"],
            ),
        )
        conn.commit()

    finally:
        conn.close()

    return "SUCCESS"


def save_settings(user_id, school, allergies):
    """로그인한 계정의 학교와 알레르기를 저장하고, 바뀐 계정 정보를 돌려준다."""
    codes = []

    for code in allergies:
        codes.append(str(code))

    conn = connect_db()

    try:
        conn.execute(
            """
            UPDATE users
            SET school_name = ?, school_kind = ?, atpt_code = ?, school_code = ?, allergies = ?
            WHERE id = ?
            """,
            (
                school["name"],
                school["kind"],
                school["atpt_code"],
                school["school_code"],
                ",".join(codes),
                user_id,
            ),
        )
        conn.commit()

        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    finally:
        conn.close()

    return user_from_row(row)


# ---------- 주의 낱말 ----------


def add_watch_word(user_id, word, memo):
    """
    주의 낱말을 등록한다. 메뉴 이름에 이 낱말이 들어가면 화면에 표시한다.

    반환값: SUCCESS / EMPTY(빈 낱말) / TOO_LONG(20자를 넘음) / DUPLICATE(이미 등록한 낱말)
    """
    word = word.strip()

    if word == "":
        return "EMPTY"

    if len(word) > WORD_MAX:
        return "TOO_LONG"

    conn = connect_db()

    try:
        conn.execute(
            "INSERT INTO watch_words (user_id, word, memo, created_at) VALUES (?, ?, ?, ?)",
            (user_id, word, memo.strip(), now_kst()),
        )
        conn.commit()

    except sqlite3.IntegrityError:
        # (user_id, word)에 UNIQUE가 걸려 있어서 같은 낱말을 또 등록하면 이 오류가 난다.
        return "DUPLICATE"

    finally:
        conn.close()

    return "SUCCESS"


def get_watch_words(user_id, keyword=""):
    """
    내 주의 낱말을 등록한 순서대로 돌려준다.

    keyword를 주면 낱말이나 메모에 그 글자가 든 것만 돌려준다.
    """
    pattern = f"%{keyword.strip()}%"
    conn = connect_db()

    try:
        rows = conn.execute(
            """
            SELECT * FROM watch_words
            WHERE user_id = ? AND (word LIKE ? OR memo LIKE ?)
            ORDER BY id
            """,
            (user_id, pattern, pattern),
        ).fetchall()

    finally:
        conn.close()

    words = []

    for row in rows:
        words.append(dict(row))

    return words


def delete_watch_word(user_id, word_id):
    """내 주의 낱말 하나를 지운다. user_id도 함께 확인해서 다른 사람의 낱말은 지우지 않는다."""
    conn = connect_db()

    try:
        conn.execute(
            "DELETE FROM watch_words WHERE id = ? AND user_id = ?",
            (word_id, user_id),
        )
        conn.commit()

    finally:
        conn.close()


# ---------- 급식 기록 ----------


def save_meals(school_code, meals):
    """
    나이스 포털에서 받은 급식을 메뉴 한 줄씩 meals 테이블에 저장한다.

    meals는 neis.fetch_meals()가 돌려준 급식 목록이다.
    같은 학교·날짜·끼니·메뉴가 이미 있으면 새 내용으로 바꿔 쓴다(INSERT OR REPLACE).
    """
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
                    INSERT OR REPLACE INTO meals (school_code, meal_date, meal_name, dish, allergy_codes)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (school_code, meal_date, meal["meal"], dish, allergy_codes),
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
