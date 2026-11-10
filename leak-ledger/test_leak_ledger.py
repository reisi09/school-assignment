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
        self.assertIn("명의도용 여부 확인", rules.make_actions(items))

    def test_grade_boundaries(self):
        self.assertEqual(rules.get_risk_grade(3), "낮음")
        self.assertEqual(rules.get_risk_grade(4), "보통")
        self.assertEqual(rules.get_risk_grade(7), "보통")
        self.assertEqual(rules.get_risk_grade(8), "높음")

    def test_unknown_item_gets_no_score(self):
        items = ["이름", "차량번호"]

        self.assertEqual(rules.calc_risk_score(items), 1)
        self.assertIn("직접 확인 필요: 차량번호", rules.make_actions(items))

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

    def add_sample_incident(self):
        database.add_service("가상커피 멤버십", "쇼핑", "학교 메일 계정", "")
        service = database.get_services()[0]

        return database.add_incident(
            service["id"],
            database.today_kst(),
            ["비밀번호", "전화번호", "이메일"],
            18000,
        )

    def test_tc01_first_run_is_empty(self):
        self.assertEqual(database.get_services(), [])
        self.assertEqual(database.get_incidents(), [])

    def test_tc02_service_is_saved_and_searched(self):
        self.assertEqual(database.add_service("가상커피 멤버십", "쇼핑", "", ""), "SUCCESS")
        self.assertEqual(database.add_service("가상은행", "금융", "", ""), "SUCCESS")

        found = database.get_services("커피")

        self.assertEqual([service["name"] for service in found], ["가상커피 멤버십"])
        self.assertEqual(len(database.get_services(category="금융")), 1)

    def test_tc04_invalid_input_is_rejected(self):
        self.assertEqual(database.add_service("   ", "쇼핑", "", ""), "EMPTY")

        database.add_service("가상은행", "금융", "", "")
        self.assertEqual(database.add_service("가상은행", "금융", "", ""), "DUPLICATE")

        service = database.get_services()[0]
        today = database.today_kst()
        tomorrow = today + timedelta(days=1)

        self.assertEqual(database.add_incident(service["id"], today, [], 0), "NO_ITEMS")
        self.assertEqual(
            database.add_incident(service["id"], tomorrow, ["이름"], 0),
            "FUTURE_DATE",
        )
        self.assertEqual(database.get_incidents(), [])

    def test_tc03_incident_is_saved_with_score_and_actions(self):
        self.assertEqual(self.add_sample_incident(), "SUCCESS")

        incident = database.get_incidents()[0]

        self.assertEqual(incident["risk_score"], 5)
        self.assertEqual(incident["leaked_items"], ["비밀번호", "전화번호", "이메일"])
        self.assertEqual(len(incident["actions"]), 5)
        self.assertEqual(incident["resolved"], 0)
        self.assertIsNone(incident["pwned_count"])

    def test_tc08_resolved_only_when_all_actions_done(self):
        self.add_sample_incident()
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
