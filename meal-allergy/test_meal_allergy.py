# test_meal_allergy.py
# 급식 알레르기의 계산·저장·검색·자료 받기를 확인한다. 나이스 포털에는 실제로 연결하지 않는다.
# 실행: python -m unittest -v

import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import requests

import database
import days
import foods
import neis
import screen_meal


class FoodsTest(unittest.TestCase):
    def test_dish_name_and_allergy_codes(self):
        # 이름 안의 괄호는 남기고, 끝의 숫자 괄호만 알레르기 번호로 읽는다.
        self.assertEqual(
            foods.parse_dish("김치함박스테이크(수제) (2.5.6.9.10)"),
            ("김치함박스테이크(수제)", [2, 5, 6, 9, 10]),
        )
        self.assertEqual(foods.parse_dish("무쌈"), ("무쌈", []))
        # 끝에 점이 하나 더 붙어 와도 읽는다.
        self.assertEqual(foods.parse_dish("배추김치 (9.13.)"), ("배추김치", [9, 13]))

    def test_whole_menu_text(self):
        text = "미니밥 <br/>물쫄면 (1.2.4.5.6.13.15.16)<br/>파김치 (9)<br/>"

        self.assertEqual(
            foods.parse_dishes(text),
            [("미니밥", []), ("물쫄면", [1, 2, 4, 5, 6, 13, 15, 16]), ("파김치", [9])],
        )
        self.assertEqual(foods.parse_dishes(None), [])

    def test_nutrition_and_calories(self):
        self.assertEqual(
            foods.parse_pairs("탄수화물(g) : 266.5<br/>쇠고기(종류) : 국내산(한우)"),
            [("탄수화물(g)", "266.5"), ("쇠고기(종류)", "국내산(한우)")],
        )
        self.assertEqual(foods.parse_kcal("2014.8 Kcal"), 2014.8)
        self.assertEqual(foods.parse_kcal(""), 0)

    def test_my_allergens_are_found_by_number(self):
        dishes = [("미니밥", []), ("돈육한방수육", [5, 6, 10, 13]), ("파김치", [9])]

        self.assertEqual(foods.find_my_allergens([5, 6, 10, 13], [10, 5]), ["대두", "돼지고기"])
        self.assertEqual(foods.count_risky_dishes(dishes, [10]), 1)
        self.assertEqual(foods.count_risky_dishes(dishes, []), 0)

    def test_watch_words_are_found_in_dish_names(self):
        words = ["아몬드", "캐슈넛", "크런치쿠키"]

        # 띄어쓰기를 빼고 비교한다. 이름에 없는 낱말은 나오지 않는다.
        self.assertEqual(foods.find_watch_words("아몬드 크런치 쿠키", words), ["아몬드", "크런치쿠키"])
        self.assertEqual(foods.find_watch_words("돈육한방수육", words), [])
        self.assertEqual(foods.find_watch_words("아몬드쿠키", []), [])


class DaysTest(unittest.TestCase):
    def test_week_math(self):
        self.assertEqual(days.monday_of(date(2026, 11, 22)), date(2026, 11, 16))
        self.assertEqual(days.school_days(date(2026, 11, 16))[-1], date(2026, 11, 20))
        self.assertEqual(days.from_ymd("20261117"), date(2026, 11, 17))


class EmptyDayTest(unittest.TestCase):
    def test_future_weekday_without_meal_is_not_yet_published(self):
        holidays = {date(2026, 11, 19): ["재량휴업일"]}

        with mock.patch.object(screen_meal, "today_kst", return_value=date(2026, 11, 17)):
            # 오늘 뒤의 평일인데 쉬는 날이 아니면 학교가 아직 올리지 않은 것이다.
            self.assertEqual(screen_meal.empty_message(date(2026, 11, 18), holidays), "급식 자료 미등록")
            # 쉬는 날이나 지난 날은 급식이 없는 것이다.
            self.assertEqual(screen_meal.empty_message(date(2026, 11, 19), holidays), "급식 없음")
            self.assertEqual(screen_meal.empty_message(date(2026, 11, 16), holidays), "급식 없음")


class NeisTest(unittest.TestCase):
    def fake_server(self, rows_by_day):
        """
        인증키 없는 나이스 포털처럼 한 번에 5건까지만 주는 가짜 call()을 만든다.

        rows_by_day는 {날짜: 그날 줄 수}이다. 기간 요청은 (전체 건수, 앞 5건)을 준다.
        """
        def call(service, params):
            if "AA_YMD" in params:
                day = days.from_ymd(params["AA_YMD"])
                rows = [{"AA_YMD": params["AA_YMD"], "n": n} for n in range(rows_by_day.get(day, 0))]
                return len(rows), rows[:5]

            start = days.from_ymd(params["AA_FROM_YMD"])
            end = days.from_ymd(params["AA_TO_YMD"])
            rows = []

            for day in sorted(rows_by_day):
                if start <= day <= end:
                    rows += [{"AA_YMD": days.ymd(day), "n": n} for n in range(rows_by_day[day])]

            return len(rows), rows[:5]

        return call

    def test_range_is_split_until_every_row_arrives(self):
        # 첫 주는 하루에 3건씩(주 15건)이라 하루씩 받아야 하고, 둘째 주는 2건이라 한 번에 받는다.
        rows_by_day = {}

        for offset in range(5):
            rows_by_day[date(2026, 12, 7) + timedelta(days=offset)] = 3

        rows_by_day[date(2026, 12, 15)] = 2

        with mock.patch.object(neis, "call", self.fake_server(rows_by_day)):
            rows = neis.fetch_range(
                "SchoolSchedule",
                {},
                ("AA_FROM_YMD", "AA_TO_YMD", "AA_YMD"),
                date(2026, 12, 1),
                date(2026, 12, 31),
            )

        self.assertEqual(len(rows), 17)
        self.assertEqual(
            sorted((row["AA_YMD"], row["n"]) for row in rows),
            sorted(set((row["AA_YMD"], row["n"]) for row in rows)),
        )

    def fake_response(self, data):
        response = mock.Mock()
        response.json.return_value = data
        return response

    def test_call_reads_rows_and_no_data(self):
        data = {
            "mealServiceDietInfo": [
                {"head": [{"list_total_count": 2}, {"RESULT": {"CODE": "INFO-000"}}]},
                {"row": [{"a": 1}, {"a": 2}]},
            ]
        }

        with mock.patch.object(neis, "get_key", return_value=""):
            with mock.patch.object(neis.requests, "get", return_value=self.fake_response(data)) as get:
                self.assertEqual(neis.call("mealServiceDietInfo", {}), (2, [{"a": 1}, {"a": 2}]))

            # 인증키가 없으면 KEY를 보내지 않고 5건만 달라고 한다.
            sent = get.call_args.kwargs["params"]
            self.assertNotIn("KEY", sent)
            self.assertEqual(sent["pSize"], 5)

            no_data = {"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}}

            with mock.patch.object(neis.requests, "get", return_value=self.fake_response(no_data)):
                self.assertEqual(neis.call("mealServiceDietInfo", {}), (0, []))

    def test_call_raises_on_errors(self):
        with mock.patch.object(neis, "get_key", return_value=""):
            with mock.patch.object(neis.requests, "get", side_effect=requests.Timeout):
                with self.assertRaises(neis.NeisError):
                    neis.call("SchoolSchedule", {})

            bad_key = {"RESULT": {"CODE": "ERROR-290", "MESSAGE": "인증키가 유효하지 않습니다."}}

            with mock.patch.object(neis.requests, "get", return_value=self.fake_response(bad_key)):
                with self.assertRaises(neis.NeisError):
                    neis.call("SchoolSchedule", {})

    def test_key_is_sent_when_present(self):
        data = {"RESULT": {"CODE": "INFO-200"}}

        with mock.patch.object(neis, "get_key", return_value="test-key"):
            with mock.patch.object(neis.requests, "get", return_value=self.fake_response(data)) as get:
                neis.call("mealServiceDietInfo", {})

        sent = get.call_args.kwargs["params"]
        self.assertEqual(sent["KEY"], "test-key")
        self.assertEqual(sent["pSize"], 1000)


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        # 테스트마다 빈 임시 데이터베이스를 쓴다.
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

        patcher = mock.patch.object(database, "DB_PATH", Path(self.folder.name) / "test.db")
        patcher.start()
        self.addCleanup(patcher.stop)

        database.create_tables()
        self.school = {
            "name": "고색고등학교",
            "kind": "고등학교",
            "atpt_code": "J10",
            "school_code": "7530878",
        }

    def meal(self, day, dishes):
        """neis.fetch_meals()가 돌려주는 모양의 급식 하나"""
        return {"date": day, "meal": "중식", "dishes": dishes}

    def test_signup_checks_rules_and_stores_only_hashes(self):
        create = database.create_user
        code = "K7QM-3XRP-9DTA"

        self.assertEqual(create("ab", "password1", "password1", self.school, code), "BAD_USERNAME")
        self.assertEqual(create("a" * 21, "password1", "password1", self.school, code), "BAD_USERNAME")
        self.assertEqual(create("급식지킴이", "short", "short", self.school, code), "SHORT_PASSWORD")
        self.assertEqual(create("급식지킴이", "password1", "password2", self.school, code), "MISMATCH")
        self.assertEqual(create(" 급식지킴이 ", "password1", "password1", self.school, code), "SUCCESS")
        self.assertEqual(create("급식지킴이", "password9", "password9", self.school, code), "TAKEN")

        # 비밀번호와 복구 코드의 원래 글자는 DB에 남지 않는다.
        conn = database.connect_db()
        row = conn.execute("SELECT password_hash, recovery_hash FROM users").fetchone()
        conn.close()

        self.assertNotIn("password1", row["password_hash"])
        self.assertNotIn("K7QM3XRP9DTA", row["recovery_hash"])

    def test_login_needs_the_right_password(self):
        database.create_user("급식지킴이", "password1", "password1", self.school, "K7QM-3XRP-9DTA")

        user = database.login("급식지킴이", "password1")

        self.assertEqual(user["username"], "급식지킴이")
        self.assertEqual(user["school"], self.school)
        self.assertEqual(user["allergies"], [])
        self.assertNotIn("password_hash", user)
        self.assertIsNone(database.login("급식지킴이", "password2"))
        self.assertIsNone(database.login("없는아이디", "password1"))

    def test_same_password_gets_a_different_salt(self):
        first = database.hash_password("password1")
        second = database.hash_password("password1")

        self.assertNotEqual(first, second)
        self.assertTrue(database.check_password("password1", first))
        self.assertTrue(database.check_password("password1", second))
        self.assertFalse(database.check_password("password2", first))

    def test_settings_are_saved_to_the_account(self):
        database.create_user("급식지킴이", "password1", "password1", self.school, "K7QM-3XRP-9DTA")
        user = database.login("급식지킴이", "password1")
        other = dict(self.school, name="고색중학교", kind="중학교", school_code="7531000")

        saved = database.save_settings(user["id"], other, [5, 10])

        # 다시 로그인해도 저장한 학교와 알레르기가 나온다.
        again = database.login("급식지킴이", "password1")

        self.assertEqual(saved["allergies"], [5, 10])
        self.assertEqual(again["school"], other)
        self.assertEqual(again["allergies"], [5, 10])

    def test_recovery_code_resets_the_password_only_once(self):
        database.create_user("급식지킴이", "password1", "password1", self.school, "K7QM-3XRP-9DTA")
        reset = database.reset_password

        self.assertEqual(reset("급식지킴이", "AAAA-BBBB-CCCC", "newpass99", "newpass99", "BBBB-CCCC-DDDD"), "WRONG_CODE")
        self.assertEqual(reset("없는아이디", "K7QM-3XRP-9DTA", "newpass99", "newpass99", "BBBB-CCCC-DDDD"), "WRONG_CODE")
        self.assertEqual(reset("급식지킴이", "K7QM-3XRP-9DTA", "short", "short", "BBBB-CCCC-DDDD"), "SHORT_PASSWORD")

        # 소문자로, 하이픈 없이 넣어도 맞는 코드로 본다.
        self.assertEqual(reset("급식지킴이", "k7qm3xrp9dta", "newpass99", "newpass99", "BBBB-CCCC-DDDD"), "SUCCESS")
        self.assertIsNone(database.login("급식지킴이", "password1"))
        self.assertIsNotNone(database.login("급식지킴이", "newpass99"))

        # 쓴 코드는 더는 쓸 수 없고, 새로 받은 코드로만 다시 바꿀 수 있다.
        self.assertEqual(reset("급식지킴이", "K7QM-3XRP-9DTA", "another99", "another99", "EEEE-FFFF-GGGG"), "WRONG_CODE")
        self.assertEqual(reset("급식지킴이", "BBBB-CCCC-DDDD", "another99", "another99", "EEEE-FFFF-GGGG"), "SUCCESS")

    def test_recovery_codes_are_random_and_easy_to_read(self):
        first = database.make_recovery_code()
        second = database.make_recovery_code()

        # 헷갈리는 0·O·1·I 없이 4글자씩 세 묶음이다.
        self.assertRegex(first, r"^[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$")
        self.assertNotEqual(first, second)

    def test_meals_are_saved_once_and_found_by_name_and_allergen(self):
        meals = [
            self.meal("20261116", "쌀밥<br/>돈까스 (1.2.5.6.10)<br/>닭갈비 (15)"),
            self.meal("20261117", "치즈 돈까스 (2.5.6.10)<br/>배추김치 (9.13)"),
        ]

        database.save_meals("7530878", meals)
        database.save_meals("7530878", meals)
        database.save_meals("9999999", [self.meal("20261117", "돈까스 (5)")])

        # 같은 학교·날짜·끼니·메뉴는 두 번 저장해도 한 줄이다.
        self.assertEqual(database.count_meals("7530878"), 5)

        # 띄어쓰기를 빼고 비교한다. 새 날짜부터 놓고, 다른 학교 기록은 섞이지 않는다.
        by_name = database.search_meals("7530878", "돈 까스")

        self.assertEqual([item["dish"] for item in by_name], ["치즈 돈까스", "돈까스"])
        self.assertEqual(by_name[0]["meal_date"], date(2026, 11, 17))
        self.assertEqual(by_name[0]["codes"], [2, 5, 6, 10])

        # 5번(대두)을 찾을 때 15번(닭고기)만 든 메뉴와 번호가 없는 메뉴는 나오지 않는다.
        by_soy = database.search_meals("7530878", "", 5)
        by_chicken = database.search_meals("7530878", "", 15)

        self.assertEqual([item["dish"] for item in by_soy], ["치즈 돈까스", "돈까스"])
        self.assertEqual([item["dish"] for item in by_chicken], ["닭갈비"])

        # 이름과 식품을 함께 주면 둘 다 맞는 메뉴만 찾는다.
        self.assertEqual(database.search_meals("7530878", "김치", 5), [])

    def test_old_database_is_upgraded_without_losing_accounts(self):
        old_path = Path(self.folder.name) / "old.db"

        # 예전 버전이 만든 모양: users에 recovery_hash가 없고, meals에 saved_at이 있다.
        conn = sqlite3.connect(str(old_path))
        conn.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,"
            " password_hash TEXT NOT NULL, school_name TEXT NOT NULL, school_kind TEXT NOT NULL,"
            " atpt_code TEXT NOT NULL, school_code TEXT NOT NULL, allergies TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO users (username, password_hash, school_name, school_kind, atpt_code, school_code,"
            " allergies, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("예전계정", database.hash_password("password1"), "고색고등학교", "고등학교", "J10", "7530878", "5", "2026-11-17"),
        )
        conn.execute(
            "CREATE TABLE meals (id INTEGER PRIMARY KEY AUTOINCREMENT, school_code TEXT NOT NULL,"
            " meal_date TEXT NOT NULL, meal_name TEXT NOT NULL, dish TEXT NOT NULL,"
            " allergy_codes TEXT NOT NULL, saved_at TEXT NOT NULL)"
        )
        conn.commit()
        conn.close()

        with mock.patch.object(database, "DB_PATH", old_path):
            database.create_tables()

            # 예전 계정은 그대로 로그인되고, 복구 코드가 없으니 비밀번호 찾기는 거절된다.
            self.assertEqual(database.login("예전계정", "password1")["allergies"], [5])
            self.assertEqual(
                database.reset_password("예전계정", "", "newpass99", "newpass99", "BBBB-CCCC-DDDD"),
                "WRONG_CODE",
            )

            # 새 모양의 meals에 저장하고 찾을 수 있다.
            database.save_meals("7530878", [self.meal("20261117", "돈까스 (5)")])
            self.assertEqual(len(database.search_meals("7530878", "돈까스")), 1)

    def test_watch_words_are_added_listed_searched_and_deleted(self):
        add = database.add_watch_word

        self.assertEqual(add(1, "  ", "메모"), "EMPTY")
        self.assertEqual(add(1, "가" * 21, ""), "TOO_LONG")
        self.assertEqual(add(1, " 아몬드 ", "번호 표시 없는 견과류"), "SUCCESS")
        self.assertEqual(add(1, "아몬드", ""), "DUPLICATE")
        self.assertEqual(add(1, "캐슈넛", "견과류"), "SUCCESS")
        self.assertEqual(add(2, "아몬드", ""), "SUCCESS")

        # 내 낱말만 등록한 순서대로 나온다. 다른 사람이 같은 낱말을 등록해도 섞이지 않는다.
        mine = database.get_watch_words(1)

        self.assertEqual([row["word"] for row in mine], ["아몬드", "캐슈넛"])

        # 낱말이나 메모에 든 글자로 찾는다.
        self.assertEqual([row["word"] for row in database.get_watch_words(1, "견과")], ["아몬드", "캐슈넛"])
        self.assertEqual([row["word"] for row in database.get_watch_words(1, "캐슈")], ["캐슈넛"])

        # 다른 사람의 번호로는 지워지지 않고, 내 번호로만 지워진다.
        database.delete_watch_word(2, mine[0]["id"])
        self.assertEqual(len(database.get_watch_words(1)), 2)

        database.delete_watch_word(1, mine[0]["id"])
        self.assertEqual([row["word"] for row in database.get_watch_words(1)], ["캐슈넛"])


if __name__ == "__main__":
    unittest.main()
