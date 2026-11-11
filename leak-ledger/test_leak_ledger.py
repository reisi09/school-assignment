# test_leak_ledger.py
# 기획서의 검증 계획(TC) 중 코드로 확인할 수 있는 항목
# 실행: python -m unittest -v

import hashlib
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

import requests

import api
import database
import rules
from texts import TEXT


class RulesTest(unittest.TestCase):
    def test_tc03_password_phone_email(self):
        items = ["비밀번호", "전화번호", "이메일"]

        self.assertEqual(rules.calc_risk_score(items), 5)
        self.assertEqual(rules.get_risk_grade(5), "보통")
        self.assertEqual(len(rules.make_actions(items)), 5)

    def test_tc05_resident_number_and_id_copy(self):
        items = ["주민등록번호", "신분증 사본"]
        score = rules.calc_risk_score(items)

        self.assertEqual(score, 10)
        self.assertEqual(rules.get_risk_grade(score), "높음")
        self.assertIn(TEXT["act_identity"], rules.make_actions(items))

    def test_grade_boundaries(self):
        self.assertEqual(rules.get_risk_grade(3), "낮음")
        self.assertEqual(rules.get_risk_grade(4), "보통")
        self.assertEqual(rules.get_risk_grade(7), "보통")
        self.assertEqual(rules.get_risk_grade(8), "높음")

    def test_unknown_item_gets_no_score(self):
        items = ["이름", "차량번호"]

        self.assertEqual(rules.calc_risk_score(items), 1)
        self.assertIn(
            TEXT["act_unknown"].format(item="차량번호"),
            rules.make_actions(items),
        )

    def test_tc08_done_date_is_kept_and_cleared(self):
        actions = [
            {"name": "A", "done": True, "done_date": "2026-11-04"},
            {"name": "B", "done": False, "done_date": None},
            {"name": "C", "done": True, "done_date": "2026-11-05"},
        ]

        updated = rules.update_action_states(
            actions, [True, True, False], "2026-11-10"
        )

        self.assertEqual(updated[0]["done_date"], "2026-11-04")
        self.assertEqual(updated[1]["done_date"], "2026-11-10")
        self.assertEqual(updated[2], {"name": "C", "done": False, "done_date": None})


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        # 테스트마다 빈 임시 데이터베이스를 쓴다.
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

        patcher = mock.patch.object(
            database, "DB_PATH", Path(self.folder.name) / "test.db"
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        database.create_tables()
        self.today = database.today_kst()

    def add_sample_record(self):
        return database.add_record(
            "가상커피 멤버십",
            "쇼핑",
            "",
            self.today,
            ["비밀번호", "전화번호", "이메일"],
            18000,
        )

    def test_tc01_first_run_is_empty(self):
        self.assertEqual(database.get_recorded_names(), set())
        self.assertEqual(database.get_incidents(), [])

    def test_tc02_record_is_saved_and_searched(self):
        database.add_record("가상커피 멤버십", "쇼핑", "학교 메일로 가입", self.today, ["이름"], 0)
        database.add_record("가상은행", "금융", "", self.today, ["계좌번호"], 0)

        found = database.get_incidents("커피")

        self.assertEqual([incident["service_name"] for incident in found], ["가상커피 멤버십"])
        self.assertEqual(found[0]["category"], "쇼핑")
        self.assertEqual(found[0]["memo"], "학교 메일로 가입")
        self.assertEqual(len(database.get_incidents()), 2)

    def test_tc03_record_is_saved_with_score_and_actions(self):
        self.assertEqual(self.add_sample_record(), "SUCCESS")

        incident = database.get_incidents()[0]

        self.assertEqual(incident["risk_score"], 5)
        self.assertEqual(incident["leaked_items"], ["비밀번호", "전화번호", "이메일"])
        self.assertEqual(incident["leak_size"], 18000)
        self.assertEqual(len(incident["actions"]), 5)
        self.assertEqual(incident["resolved"], 0)
        self.assertIsNone(incident["pwned_count"])

    def test_tc04_invalid_input_saves_nothing(self):
        tomorrow = self.today + timedelta(days=1)

        self.assertEqual(
            database.add_record("  ", "기타", "", self.today, ["이름"], 0), "EMPTY"
        )
        self.assertEqual(
            database.add_record("가상몰", "쇼핑", "", self.today, [], 0), "NO_ITEMS"
        )
        self.assertEqual(
            database.add_record("가상몰", "쇼핑", "", tomorrow, ["이름"], 0),
            "FUTURE_DATE",
        )

        # 서비스만 남고 기록은 없는 상태가 생기지 않는다.
        self.assertEqual(database.get_recorded_names(), set())
        self.assertEqual(database.get_incidents(), [])

    def test_same_service_gets_second_record(self):
        database.add_record("Gasang Mall", "쇼핑", "첫 메모", self.today, ["이름"], 0)

        # 이름의 앞뒤 공백과 대소문자가 달라도 같은 서비스로 본다.
        database.add_record(" gasang mall ", "기타", "", self.today, ["비밀번호"], 0)

        incidents = database.get_incidents("gasang")

        self.assertEqual(database.get_recorded_names(), {"gasang mall"})
        self.assertEqual(len(incidents), 2)

        # 서비스의 분류는 처음 값 그대로이고, 메모는 비워서 적으면 바뀌지 않는다.
        self.assertEqual(incidents[0]["category"], "쇼핑")
        self.assertEqual(incidents[0]["memo"], "첫 메모")

        database.add_record("Gasang Mall", "쇼핑", "바꾼 메모", self.today, ["이름"], 0)

        self.assertEqual(database.get_incidents("gasang")[0]["memo"], "바꾼 메모")

    def test_tc08_resolved_only_when_all_actions_done(self):
        self.add_sample_record()
        incident = database.get_incidents()[0]
        count = len(incident["actions"])

        partly = rules.update_action_states(
            incident["actions"], [True] + [False] * (count - 1), "2026-11-10"
        )
        database.save_actions(incident["id"], partly)

        self.assertEqual(len(database.get_incidents(status="진행 중")), 1)

        all_done = rules.update_action_states(partly, [True] * count, "2026-11-11")
        database.save_actions(incident["id"], all_done)

        self.assertEqual(database.get_incidents(status="진행 중"), [])

        saved = database.get_incidents(status="완료")[0]

        self.assertEqual(saved["actions"][0]["done_date"], "2026-11-10")
        self.assertEqual(saved["actions"][1]["done_date"], "2026-11-11")

    def test_pwned_count_is_saved(self):
        self.add_sample_record()
        incident = database.get_incidents()[0]

        database.save_pwned_count(incident["id"], 52372427)

        self.assertEqual(database.get_incidents()[0]["pwned_count"], 52372427)

    def test_real_case_is_recorded_once(self):
        # 기사에 적힌 사례 하나를 서비스와 유출 기록으로 등록한다.
        case = {
            "name": "대신증권",
            "category": "금융",
            "date": "2026-10-28",
            "size": 38490,
            "items": ["이름", "이메일", "주소", "계좌번호"],
        }

        self.assertEqual(database.add_case(case), "SUCCESS")

        incident = database.get_incidents()[0]

        self.assertEqual(incident["service_name"], "대신증권")
        self.assertEqual(incident["notified_date"], "2026-10-28")
        self.assertEqual(incident["risk_score"], 6)
        self.assertEqual(incident["leak_size"], 38490)

        # 같은 사례를 다시 누르면 서비스도 기록도 늘지 않는다.
        self.assertEqual(database.add_case(case), "DUPLICATE")
        self.assertEqual(database.get_recorded_names(), {"대신증권"})
        self.assertEqual(len(database.get_incidents()), 1)

    def test_real_case_without_date_uses_today(self):
        case = {
            "name": "빗썸",
            "category": "금융",
            "date": None,
            "size": 6444,
            "items": ["주민등록번호", "신분증 사본"],
        }

        database.add_case(case)

        self.assertEqual(
            database.get_incidents()[0]["notified_date"],
            self.today.isoformat(),
        )


class ApiTest(unittest.TestCase):
    def fake_response(self, text, status_code=200):
        response = mock.Mock()
        response.status_code = status_code
        response.text = text
        return response

    def test_tc06_finds_own_suffix_and_sends_only_prefix(self):
        sha1 = hashlib.sha1(b"password").hexdigest().upper()
        body = f"0000000000000000000000000000000000A:3\r\n{sha1[5:]}:52372427\r\n"

        with mock.patch.object(
            api.requests, "get", return_value=self.fake_response(body)
        ) as get:
            self.assertEqual(api.check_pwned_password("password"), (52372427, "SUCCESS"))

        # TC-12: 전송 주소에는 해시 앞 5자리만 들어간다.
        self.assertEqual(get.call_args.args[0], api.API_URL + sha1[:5])

    def test_tc07_not_in_list_is_zero(self):
        body = "0000000000000000000000000000000000A:3\r\n"

        with mock.patch.object(
            api.requests, "get", return_value=self.fake_response(body)
        ):
            self.assertEqual(api.check_pwned_password("password"), (0, "SUCCESS"))

    def test_tc09_failures_return_no_count(self):
        with mock.patch.object(
            api.requests, "get", side_effect=requests.Timeout
        ):
            self.assertEqual(api.check_pwned_password("a"), (None, "NETWORK_ERROR"))

        with mock.patch.object(
            api.requests, "get", return_value=self.fake_response("", 503)
        ):
            self.assertEqual(api.check_pwned_password("a"), (None, "NETWORK_ERROR"))

        with mock.patch.object(
            api.requests, "get", return_value=self.fake_response("<html>")
        ):
            self.assertEqual(api.check_pwned_password("a"), (None, "DATA_ERROR"))

    def test_tc10_empty_password_does_not_call_api(self):
        with mock.patch.object(api.requests, "get") as get:
            self.assertEqual(api.check_pwned_password(""), (None, "EMPTY"))

        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
