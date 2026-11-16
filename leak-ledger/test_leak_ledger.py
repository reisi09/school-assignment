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
import play
import rules
import stats
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

    def test_finish_and_undo_change_only_one_action(self):
        actions = [
            {"name": "A", "done": True, "done_date": "2026-11-04", "result": "앞서 끝냄"},
            {"name": "B", "done": False, "done_date": None},
        ]

        finished = rules.finish_action(actions, 1, "2단계 인증을 켬", "2026-11-10")

        self.assertEqual(finished[0], actions[0])
        self.assertEqual(
            finished[1],
            {"name": "B", "done": True, "done_date": "2026-11-10", "result": "2단계 인증을 켬"},
        )

        # 원래 목록은 바뀌지 않는다.
        self.assertFalse(actions[1]["done"])

        undone = rules.undo_action(finished, 0)

        self.assertEqual(undone[0], {"name": "A", "done": False, "done_date": None, "result": None})
        self.assertEqual(undone[1], finished[1])

    def test_password_rule_follows_kisa_kinds_and_length(self):
        # 3종류 이상을 섞으면 8자, 2종류를 섞으면 10자가 기준이다.
        self.assertTrue(rules.is_strong_password("abcdef1!"))
        self.assertFalse(rules.is_strong_password("abcde1!"))
        self.assertFalse(rules.is_strong_password("abcdefgh1"))
        self.assertTrue(rules.is_strong_password("abcdefghi1"))

        # 한 종류만 쓰면 길어도 기준에 못 미친다.
        self.assertFalse(rules.is_strong_password("abcdefghijklmnop"))

        # 한글과 띄어쓰기는 네 종류 어디에도 세지 않는다.
        self.assertEqual(rules.count_char_kinds("Ab1!"), 4)
        self.assertEqual(rules.count_char_kinds("가나다 라"), 0)

    def test_every_action_opens_its_own_mission(self):
        items = list(rules.ITEM_WEIGHTS) + ["차량번호"]
        types = [rules.get_mission_type(name) for name in rules.make_actions(items)]

        # 목록에 없는 정보(차량번호)의 할 일만 직접 적는 창(note)을 연다.
        self.assertEqual(types.count("note"), 1)
        self.assertEqual(len(set(types)), len(types))

    def test_remaining_score_shrinks_as_actions_are_done(self):
        self.assertEqual(rules.calc_remaining_score(6, 4, 4), 6)
        self.assertEqual(rules.calc_remaining_score(6, 2, 4), 3)
        self.assertEqual(rules.calc_remaining_score(5, 0, 3), 0)

        # 할 일이 하나라도 남으면 0점이 되지 않는다.
        self.assertEqual(rules.calc_remaining_score(1, 1, 4), 1)

    def test_notice_items_are_found_by_other_names(self):
        text = "■ 유출 항목\n- 성명, 휴대전화번호, 이메일 주소, 주민번호, 신분증 사본 이미지"

        # "이메일 주소"의 주소는 집 주소로 읽지 않는다.
        self.assertEqual(
            rules.find_items_in_text(text),
            ["이름", "전화번호", "이메일", "주민등록번호", "신분증 사본"],
        )

    def test_notice_skips_items_said_not_leaked(self):
        text = "이름과 아이디(ID)가 유출되었으며 비밀번호는 유출되지 않았습니다."

        self.assertEqual(rules.find_items_in_text(text), ["이름", "아이디"])

    def test_notice_skips_advice_and_contact(self):
        text = (
            "고객님의 이메일, 생년월일이 유출된 사실을 확인했습니다. "
            "피해를 막기 위해 비밀번호를 변경해 주시기 바랍니다. "
            "문의: 고객센터 전화번호 1500-0000"
        )

        self.assertEqual(rules.find_items_in_text(text), ["이메일", "생년월일"])

    def test_notice_without_items_finds_nothing(self):
        self.assertEqual(rules.find_items_in_text("이벤트에 당첨되셨습니다."), [])


class StatsTest(unittest.TestCase):
    def setUp(self):
        # database.get_incidents()가 돌려주는 모양을 흉내 낸 기록 세 건
        done = {"name": "A", "done": True, "done_date": "2026-11-10"}
        open_ = {"name": "B", "done": False, "done_date": None}

        self.incidents = [
            {
                "service_name": "가상은행",
                "risk_score": 9,
                "leaked_items": ["이름", "이메일", "주민등록번호"],
                "actions": [open_, open_, open_],
            },
            {
                "service_name": "가상쇼핑",
                "risk_score": 4,
                "leaked_items": ["이메일", "비밀번호"],
                "actions": [done, open_],
            },
            {
                "service_name": "가상쇼핑",
                "risk_score": 1,
                "leaked_items": ["이메일"],
                "actions": [done],
            },
        ]

    def test_repeated_items_count_services_not_records(self):
        # 이메일은 기록 세 건에 있지만 서비스는 두 곳이다.
        self.assertEqual(
            stats.find_repeated_items(self.incidents),
            [("이메일", ["가상은행", "가상쇼핑"])],
        )

    def test_items_are_counted_most_leaked_first(self):
        self.assertEqual(stats.count_items(self.incidents)[0], ("이메일", 3))

    def test_grades_remaining_score_and_done_percent(self):
        self.assertEqual(
            stats.count_grades(self.incidents),
            {"높음": 1, "보통": 1, "낮음": 1},
        )

        # 9점(모두 남음) + 4점의 절반 + 0점(모두 끝냄)
        self.assertEqual(stats.sum_remaining_scores(self.incidents), 11)

        # 할 일 6개 중 2개를 끝냈다.
        self.assertEqual(stats.get_done_percent(self.incidents), 33)
        self.assertEqual(stats.get_done_percent([]), 0)


class PlayTest(unittest.TestCase):
    def attack_names(self, items):
        return [attack["name"] for attack in play.find_attacks(items)]

    def test_attack_needs_every_item(self):
        self.assertEqual(self.attack_names(["이름"]), [])
        self.assertEqual(self.attack_names(["이름", "전화번호"]), ["sms", "call"])
        self.assertEqual(self.attack_names(["주민등록번호"]), ["rrn"])
        self.assertEqual(len(play.find_attacks(list(rules.ITEM_WEIGHTS))), len(play.ATTACKS))

    def test_quiz_puts_my_leaked_items_first(self):
        order = play.order_quiz(["비밀번호"])

        self.assertEqual(order[:2], [3, 4])
        self.assertEqual(sorted(order), list(range(len(play.QUIZ))))
        self.assertEqual(play.order_quiz([]), list(range(len(play.QUIZ))))

    def test_mission_blocks_only_attacks_possible_with_leaked_items(self):
        def names(mission_type, items):
            return [attack["name"] for attack in play.find_blocked_attacks(mission_type, items)]

        # 이름과 생년월일이 함께 유출되지 않았으면 생일 추측 공격은 막을 것이 없다.
        self.assertEqual(names("password", ["비밀번호", "이메일"]), ["pw"])
        self.assertEqual(names("password", ["비밀번호", "이름", "생년월일"]), ["pw", "birth"])

        # 확인만 하는 할 일은 막는 공격이 없다.
        self.assertEqual(names("lookup", list(rules.ITEM_WEIGHTS)), [])

        attack_names = [attack["name"] for attack in play.ATTACKS]

        for blocked in play.MISSION_BLOCKS.values():
            for name in blocked:
                self.assertIn(name, attack_names)

    def test_every_attack_and_question_has_text(self):
        # 문구가 하나라도 빠지면 체험하기 화면이 멈춘다.
        for attack in play.ATTACKS:
            self.assertIn(f"attack_{attack['name']}_title", TEXT)
            self.assertIn(f"attack_{attack['name']}_body", TEXT)

            for item in attack["needs"]:
                self.assertIn(item, rules.ITEM_WEIGHTS)

        for number, question in enumerate(play.QUIZ, start=1):
            self.assertIn(f"quiz{number}_message", TEXT)
            self.assertIn(f"quiz{number}_reason", TEXT)
            self.assertIn(question["item"], rules.ITEM_WEIGHTS)


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

        partly = rules.finish_action(incident["actions"], 0, "결과", "2026-11-10")
        database.save_actions(incident["id"], partly)

        self.assertEqual(len(database.get_incidents(status="진행 중")), 1)

        all_done = partly

        for index in range(1, count):
            all_done = rules.finish_action(all_done, index, "결과", "2026-11-11")

        database.save_actions(incident["id"], all_done)

        self.assertEqual(database.get_incidents(status="진행 중"), [])

        saved = database.get_incidents(status="완료")[0]

        self.assertEqual(saved["actions"][0]["done_date"], "2026-11-10")
        self.assertEqual(saved["actions"][1]["done_date"], "2026-11-11")
        self.assertEqual(saved["actions"][1]["result"], "결과")

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

    def test_update_recalculates_and_keeps_done_actions(self):
        self.add_sample_record()
        incident = database.get_incidents()[0]

        # 첫 번째 할 일(이 서비스의 비밀번호 바꾸기)을 끝낸다.
        done_one = rules.finish_action(
            incident["actions"], 0, "기준에 맞게 비밀번호 바꿈", "2026-11-10"
        )
        database.save_actions(incident["id"], done_one)

        status = database.update_record(
            incident["id"],
            "가상커피",
            "기타",
            "고친 메모",
            self.today,
            ["비밀번호", "주민등록번호"],
            500,
        )

        self.assertEqual(status, "SUCCESS")

        saved = database.get_incidents()[0]

        self.assertEqual(saved["service_name"], "가상커피")
        self.assertEqual(saved["category"], "기타")
        self.assertEqual(saved["memo"], "고친 메모")
        self.assertEqual(saved["leak_size"], 500)
        self.assertEqual(saved["risk_score"], 8)
        self.assertEqual(
            [action["name"] for action in saved["actions"]],
            rules.make_actions(["비밀번호", "주민등록번호"]),
        )

        # 이미 끝낸 일은 그대로이고, 새로 생긴 일은 남아 있다.
        self.assertEqual(saved["actions"][0]["done_date"], "2026-11-10")
        self.assertEqual(saved["actions"][0]["result"], "기준에 맞게 비밀번호 바꿈")
        self.assertIn(TEXT["act_identity"], [a["name"] for a in saved["actions"] if not a["done"]])
        self.assertEqual(saved["resolved"], 0)

    def test_update_rejects_bad_input_and_taken_name(self):
        self.add_sample_record()
        database.add_record("가상은행", "금융", "", self.today, ["계좌번호"], 0)
        incident = database.get_incidents("커피")[0]

        self.assertEqual(
            database.update_record(incident["id"], "가상은행", "쇼핑", "", self.today, ["이름"], 0),
            "DUPLICATE",
        )
        self.assertEqual(
            database.update_record(incident["id"], "가상커피 멤버십", "쇼핑", "", self.today, [], 0),
            "NO_ITEMS",
        )
        self.assertEqual(
            database.update_record(9999, "없는 기록", "쇼핑", "", self.today, ["이름"], 0),
            "NOT_FOUND",
        )

        # 고치지 못했으면 기록은 그대로다.
        unchanged = database.get_incidents("커피")[0]

        self.assertEqual(unchanged["service_name"], "가상커피 멤버십")
        self.assertEqual(unchanged["leaked_items"], ["비밀번호", "전화번호", "이메일"])

    def test_delete_removes_service_only_with_its_last_record(self):
        self.add_sample_record()
        self.add_sample_record()
        first, second = database.get_incidents()

        database.delete_record(first["id"])

        self.assertEqual(len(database.get_incidents()), 1)
        self.assertEqual(database.get_recorded_names(), {"가상커피 멤버십"})

        database.delete_record(second["id"])

        self.assertEqual(database.get_incidents(), [])
        self.assertEqual(database.get_recorded_names(), set())

        # 이미 지운 기록을 다시 지워도 오류가 나지 않는다.
        database.delete_record(second["id"])

    def test_quiz_summary_keeps_best_score_and_count(self):
        self.assertEqual(database.get_quiz_summary(), (None, 0))

        database.add_quiz_result(5, 8)
        database.add_quiz_result(7, 8)
        database.add_quiz_result(6, 8)

        self.assertEqual(database.get_quiz_summary(), (7, 3))


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
