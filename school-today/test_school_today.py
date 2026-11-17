# test_school_today.py
# 학교한눈의 계산·저장·자료 받기를 확인한다. 나이스 포털에는 실제로 연결하지 않는다.
# 실행: python -m unittest -v

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


class DaysTest(unittest.TestCase):
    def test_week_and_month_math(self):
        self.assertEqual(days.monday_of(date(2026, 11, 22)), date(2026, 11, 16))
        self.assertEqual(days.school_days(date(2026, 11, 16))[-1], date(2026, 11, 20))
        self.assertEqual(days.add_months(date(2026, 12, 1), 1), date(2027, 1, 1))
        self.assertEqual(days.add_months(date(2026, 1, 1), -1), date(2025, 12, 1))
        self.assertEqual(days.last_of_month(date(2028, 2, 10)), date(2028, 2, 29))
        self.assertEqual(days.d_day(date(2026, 11, 19), date(2026, 11, 17)), 2)

    def test_crowded_weeks_count_only_the_kind(self):
        def event(day, kind):
            return {"due_date": day, "kind": kind}

        events = [
            event(date(2026, 11, 16), "수행평가"),
            event(date(2026, 11, 18), "수행평가"),
            event(date(2026, 11, 20), "수행평가"),
            event(date(2026, 11, 19), "과제"),
            event(date(2026, 11, 23), "수행평가"),
            event(date(2026, 11, 24), "수행평가"),
        ]

        # 둘째 주는 2개라 몰린 주가 아니다. 과제는 세지 않는다.
        self.assertEqual(days.find_crowded_weeks(events, "수행평가", 3), [(date(2026, 11, 16), 3)])
        self.assertEqual(days.find_crowded_weeks(events, "과제", 3), [])


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
                neis.call("hisTimetable", {})

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

    def test_profile_is_saved_and_updated_by_nickname(self):
        self.assertEqual(database.save_profile("  ", self.school, 2, 8, []), "EMPTY")
        self.assertIsNone(database.load_profile("우석"))

        database.save_profile("우석", self.school, 2, 8, [5, 10])
        database.save_profile(" 우석 ", self.school, 3, 1, [])

        profile = database.load_profile("우석")

        self.assertEqual(profile["school"], self.school)
        self.assertEqual((profile["grade"], profile["class_nm"], profile["allergies"]), (3, 1, []))

    def test_events_are_checked_found_and_deleted(self):
        add = database.add_event
        day = date(2026, 11, 20)

        self.assertEqual(add("7530878", 2, 8, "수행평가", " ", "논설문", day, ""), "NO_SUBJECT")
        self.assertEqual(add("7530878", 2, 8, "수행평가", "국어", " ", day, ""), "NO_TITLE")

        add("7530878", 2, 8, "수행평가", "독서와 작문", "논설문 쓰기", day, "원고지 준비")
        add("7530878", 2, 8, "과제", "영어Ⅱ", "단어 시험", day + timedelta(days=30), "")
        add("7530878", 2, 7, "수행평가", "독서와 작문", "다른 반 일정", day, "")

        # 다른 반 일정과 기간 밖 일정은 보이지 않는다.
        found = database.get_events("7530878", 2, 8, date(2026, 11, 1), date(2026, 11, 30))

        self.assertEqual([event["title"] for event in found], ["논설문 쓰기"])
        self.assertEqual(found[0]["due_date"], day)

        # 메모의 낱말로도 찾는다.
        everything = (date(2000, 1, 1), date(2100, 12, 31))
        by_memo = database.get_events("7530878", 2, 8, *everything, keyword="원고지")

        self.assertEqual(len(by_memo), 1)

        database.delete_event(found[0]["id"])

        self.assertEqual(len(database.get_events("7530878", 2, 8, *everything)), 1)

    def test_reviews_are_checked_and_ranked(self):
        today = date(2026, 11, 17)
        add = database.add_review

        self.assertEqual(add("7530878", today, None, 5, ""), "NO_DISH")
        self.assertEqual(add("7530878", today, "물쫄면", None, ""), "NO_STARS")
        self.assertEqual(add("7530878", today, "물쫄면", 6, ""), "NO_STARS")

        add("7530878", today, "물쫄면", 3, "")
        add("7530878", today, "돈육한방수육", 5, "부드러움")
        add("7530878", today, "돈육한방수육", 4, "양이 많음")
        add("7530878", today, "파김치", 4, "")
        add("9999999", today, "다른 학교 메뉴", 5, "")

        # 평균이 높은 순서, 평균이 같으면 평가가 많은 순서다. 다른 학교 평가는 섞이지 않는다.
        self.assertEqual(
            database.get_top_dishes("7530878"),
            [("돈육한방수육", 4.5, 2), ("파김치", 4.0, 1), ("물쫄면", 3.0, 1)],
        )

        recent = database.get_recent_reviews("7530878")

        self.assertEqual([review["comment"] for review in recent], ["양이 많음", "부드러움"])


if __name__ == "__main__":
    unittest.main()
