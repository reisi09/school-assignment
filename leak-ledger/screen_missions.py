# screen_missions.py
# 할 일을 직접 해 보는 창. 할 일 화면의 [시작하기]를 누르면 열린다.
# 할 일의 종류(rules.py의 MISSION_TYPES)마다 아래 함수가 하나씩 있다.
#   password   연습용 새 비밀번호 점검            reuse  같은 비밀번호를 쓰던 곳 고르기
#   otp        가상 로그인으로 2단계 인증 체험     quiz   사칭 문자 3문제
#   lookup, identity, account                    사이트·앱에서 확인하고 결과 고르기
#   fss        사고예방시스템 등록                note   목록에 없는 정보 직접 확인
#
# 창 안에서 쓰는 값은 st.session_state에 "m_기록번호_할일순서_이름" 모양의 key로 둔다.
# 예: 3번 기록의 첫 번째 할 일에서 2단계 인증 체험의 단계는 "m_3_0_step"에 있다.

import random

import streamlit as st

from api import check_pwned_password
from common import esc, icon, phone, pill, verdict
from database import save_actions, today_kst
from play import find_blocked_attacks, order_quiz
from rules import (
    count_char_kinds,
    finish_action,
    get_mission_type,
    is_strong_password,
    undo_action,
)
from screen_play import show_quiz_question
from texts import TEXT as T

# 사이트를 열어 확인하는 할 일의 주소
LINKS = {
    "lookup": "https://kidc.eprivacy.go.kr",
    "identity": "https://www.msafer.or.kr",
    "fss": "https://pd.fss.or.kr",
}

# 사칭 문자 할 일에서 푸는 문제 수
QUIZ_COUNT = 3

# 2단계 인증 체험의 가상 로그인 화면에 보이는 아이디
DEMO_ID = "gasang01"


# ---------- 할 일을 끝내거나 되돌리기 ----------


def finish_mission(incident, index, result):
    """할 일을 끝낸 것으로 저장한다. 창이 닫히고 할 일 화면이 다시 그려진다."""
    actions = finish_action(incident["actions"], index, result, today_kst().isoformat())
    save_actions(incident["id"], actions)

    # 화면 구석에 잠깐 뜨는 알림. 막은 공격이 있으면 그 수도 알려 준다.
    task = incident["actions"][index]["name"]
    blocked = find_blocked_attacks(get_mission_type(task), incident["leaked_items"])
    message = T["mission_toast"].format(task=task)

    if len(blocked) > 0:
        message += " · " + T["mission_toast_blocked"].format(count=len(blocked))

    st.session_state["mission_toast"] = message

    # 방금 끝낸 줄은 할 일 화면에서 한 번 반짝인다.
    st.session_state["just_done"] = f"{incident['id']}_{index}"

    # 이 기록의 할 일을 모두 끝냈으면 축하 표시를 보여 준다.
    all_done = True

    for action in actions:
        if not action["done"]:
            all_done = False

    if all_done:
        st.session_state["cheer"] = incident["service_name"]

    # 앱 전체를 다시 실행하면 창이 닫힌다.
    st.rerun()


def undo_mission(incident, index):
    """끝낸 할 일을 다시 남은 일로 되돌린다."""
    actions = undo_action(incident["actions"], index)
    save_actions(incident["id"], actions)

    task = incident["actions"][index]["name"]
    st.session_state["mission_toast"] = T["mission_undo_toast"].format(task=task)
    st.rerun()


def clear_mission_state(prefix):
    """창을 새로 열거나 다시 풀 때, 전에 이 창에서 하던 값을 지운다."""
    for key in list(st.session_state.keys()):
        if key.startswith(prefix + "_"):
            del st.session_state[key]


def set_value(key, value):
    """버튼을 누르면 session_state의 값 하나를 바꾼다."""
    st.session_state[key] = value


def show_text(text):
    """창 안의 설명 한 단락을 보여 준다."""
    st.html(f'<p class="mission-intro">{esc(text)}</p>')


# ---------- 화면 조각 ----------


def check_row(ok, title, detail):
    """점검 항목 한 줄을 만든다. ok가 True면 통과, False면 실패, None이면 확인 못 함이다."""
    if ok is None:
        mark = f'<span class="check-mark is-maybe">{icon("question")}</span>'
    elif ok:
        mark = f'<span class="check-mark is-ok">{icon("check")}</span>'
    else:
        mark = f'<span class="check-mark is-no">{icon("cross")}</span>'

    return (
        f'<div class="check-row">{mark}'
        f"<div><b>{esc(title)}</b><span>{esc(detail)}</span></div></div>"
    )


def login_window(screen):
    """
    2단계 인증 체험의 가상 로그인 화면을 만든다.

    screen은 password(아이디·비밀번호 입력), code(인증번호 요구), success(로그인 성공) 중 하나다.
    """
    body = (
        f'<div class="login-field"><span>{esc(T["otp_id_label"])}</span><b>{DEMO_ID}</b></div>'
        f'<div class="login-field"><span>{esc(T["otp_pw_label"])}</span><b>●●●●●●●●</b></div>'
    )

    if screen == "code":
        body += (
            f'<div class="login-code">{icon("lock")}<p>{esc(T["otp_code_screen"])}</p>'
            '<div class="code-boxes"><i></i><i></i><i></i><i></i><i></i><i></i></div></div>'
        )
    elif screen == "success":
        body += f'<div class="login-done"><span class="done-badge">{icon("check")}</span></div>'

    return (
        f'<div class="login-window is-{screen}">'
        f'<div class="login-bar"><i></i><i></i><i></i><span>{esc(T["otp_window_title"])}</span></div>'
        f'<div class="login-body">{body}</div></div>'
    )


# ---------- 할 일 종류마다 하는 일 ----------


def mission_password(incident, index, prefix):
    """연습용 새 비밀번호를 넣고, 문자 종류·길이 기준과 유출 목록 두 가지를 점검한다."""
    show_text(T["pwm_intro"])
    st.html(f'<div class="mission-note">{esc(T["pwm_rule"])}</div>')
    st.warning(T["pw_demo_warning"])

    with st.form(prefix + "_form", clear_on_submit=True):
        password = st.text_input(T["pwm_input"], type="password")
        submitted = st.form_submit_button(T["pwm_check_button"], type="primary")

    if submitted:
        if password == "":
            st.warning(T["err_pw_empty"])
        else:
            count, status = check_pwned_password(password)

            # 비밀번호는 남기지 않고 점검 결과만 남긴다.
            st.session_state[prefix + "_check"] = {
                "kinds": count_char_kinds(password),
                "length": len(password),
                "strong": is_strong_password(password),
                "count": count,
                "status": status,
            }

    check = st.session_state.get(prefix + "_check")

    if check is None:
        return

    # 두 번째 항목: 유출 목록. 확인하지 못했으면 첫 번째 항목만으로 판단한다.
    if check["status"] != "SUCCESS":
        leak_ok = None
        leak_text = T["pwm_leak_error"]
    elif check["count"] == 0:
        leak_ok = True
        leak_text = T["pwm_leak_clean"]
    else:
        leak_ok = False
        leak_text = T["pwm_leak_found"].format(count=f"{check['count']:,}")

    rule_text = T["pwm_rule_detail"].format(kinds=check["kinds"], length=check["length"])
    rows = check_row(check["strong"], T["pwm_check_rule"], rule_text)
    rows += check_row(leak_ok, T["pwm_check_leak"], leak_text)

    if check["strong"] and leak_ok is not False:
        st.html(f'<div class="checks">{rows}</div>' + verdict(True, T["pwm_pass"]))

        if st.button(T["pwm_finish"], type="primary", key=prefix + "_finish"):
            finish_mission(incident, index, T["pwm_result"])
    else:
        st.html(f'<div class="checks">{rows}</div>' + verdict(False, T["pwm_fail"]))


def mission_reuse(incident, index, prefix):
    """같은 비밀번호를 쓰던 곳을 고르면, 공격자가 그곳에도 로그인할 수 있음을 보여 준다."""
    show_text(T["reuse_intro"])

    places = st.pills(
        T["reuse_pick_label"],
        T["reuse_places"],
        selection_mode="multi",
        key=prefix + "_places",
    )

    if len(places) == 0:
        if st.button(T["reuse_none_button"], key=prefix + "_none"):
            finish_mission(incident, index, T["reuse_result_none"])

        return

    # 새로 고른 곳만 움직이며 나타나게 지난번에 고른 곳을 기억한다.
    before = st.session_state.get(prefix + "_before", [])
    st.session_state[prefix + "_before"] = places

    cards = ""

    for place in places:
        new = ""

        if place not in before:
            new = " is-new"

        cards += f'<div class="place{new}"><b>{esc(place)}</b>{pill(T["reuse_open"], "red")}</div>'

    st.html(
        f'<p class="mission-risk">{esc(T["reuse_risk_line"].format(count=len(places)))}</p>'
        f'<div class="places">{cards}</div>'
    )

    if st.button(T["reuse_finish"], type="primary", key=prefix + "_finish"):
        finish_mission(incident, index, T["reuse_result"].format(count=len(places)))


def start_my_login(prefix):
    """'나로 로그인'을 누르면 인증번호 6자리를 새로 만들어 가상 휴대전화로 보낸다."""
    st.session_state[prefix + "_code"] = str(random.randint(100000, 999999))
    st.session_state[prefix + "_step"] = "code"


def mission_otp(incident, index, prefix):
    """가상 로그인 화면에서 공격자와 나로 한 번씩 로그인해 2단계 인증을 겪어 본다."""
    show_text(T["otp_intro"])
    step = st.session_state.get(prefix + "_step", "attacker")

    # 1단계: 공격자가 유출된 아이디와 비밀번호로 로그인한다.
    if step == "attacker":
        st.html(login_window("password"))
        st.button(
            T["otp_attacker_button"],
            type="primary",
            key=prefix + "_attack",
            on_click=set_value,
            args=(prefix + "_step", "blocked"),
        )

    # 2단계: 인증번호를 요구받은 공격자는 내 휴대전화가 없어서 막힌다.
    elif step == "blocked":
        st.html(login_window("code") + verdict(False, T["otp_attacker_blocked"]))
        st.button(
            T["otp_me_button"],
            type="primary",
            key=prefix + "_me",
            on_click=start_my_login,
            args=(prefix,),
        )

    # 3단계: 나는 내 휴대전화에 온 인증번호를 넣는다.
    elif step == "code":
        code = st.session_state[prefix + "_code"]
        message = T["otp_phone_message"].format(code=code)
        st.html(login_window("code") + phone(message, T["otp_phone_title"], "is-arriving"))

        with st.form(prefix + "_code_form"):
            typed = st.text_input(T["otp_code_label"], max_chars=6)
            submitted = st.form_submit_button(T["otp_code_button"], type="primary")

        if submitted:
            if typed.strip() == code:
                st.session_state[prefix + "_step"] = "success"
                # 창만 다시 그려서 다음 단계를 보여 준다.
                st.rerun(scope="fragment")
            else:
                st.html(verdict(False, T["otp_code_wrong"]))

    # 4단계: 로그인 성공. 실제 서비스에서도 켠 뒤 끝낸다.
    else:
        st.html(
            login_window("success")
            + verdict(True, T["otp_success"])
            + f'<p class="mission-intro">{esc(T["otp_real_guide"])}</p>'
        )

        if st.button(T["otp_finish"], type="primary", key=prefix + "_finish"):
            finish_mission(incident, index, T["otp_result"])


def mission_quiz(incident, index, prefix):
    """내 유출 정보와 관련된 사칭 문자 3문제를 푼다. 모두 맞혀야 끝낼 수 있다."""
    show_text(T["qm_intro"])

    order = order_quiz(incident["leaked_items"])[:QUIZ_COUNT]
    score = show_quiz_question(prefix, order, incident["leaked_items"])

    # 아직 푸는 중이다.
    if score is None:
        return

    if score == len(order):
        st.html(verdict(True, T["qm_pass"]))

        if st.button(T["qm_finish"], type="primary", key=prefix + "_finish"):
            finish_mission(incident, index, T["qm_result"].format(total=len(order)))
    else:
        st.html(verdict(False, T["qm_fail"].format(score=score, total=len(order))))
        st.button(
            T["quiz_retry"],
            key=prefix + "_retry",
            on_click=clear_mission_state,
            args=(prefix,),
        )


def mission_check(incident, index, prefix, kind):
    """
    사이트나 앱에서 직접 확인하고 결과를 고른다. kind는 lookup, identity, account 중 하나다.

    문구는 texts.py에서 "kind_intro", "kind_clean"처럼 kind로 시작하는 key로 찾는다.
    """
    show_text(T[kind + "_intro"])

    if kind in LINKS:
        st.link_button(T[kind + "_link"], LINKS[kind])

    result = st.radio(
        T["mission_result_label"],
        [T[kind + "_clean"], T[kind + "_found"]],
        index=None,
        key=prefix + "_result",
    )

    # 문제가 있다고 고르면 바로 할 일을 알려 준다.
    if result == T[kind + "_found"]:
        st.html(verdict(False, T[kind + "_found_advice"]))

    if st.button(
        T[kind + "_finish"],
        type="primary",
        disabled=result is None,
        key=prefix + "_finish",
    ):
        finish_mission(incident, index, result)


def mission_fss(incident, index, prefix):
    """개인정보노출자 사고예방시스템을 열어 등록하고 끝낸다."""
    show_text(T["fss_intro"])
    st.link_button(T["fss_link"], LINKS["fss"])

    if st.button(T["fss_finish"], type="primary", key=prefix + "_finish"):
        finish_mission(incident, index, T["fss_result"])


def mission_note(incident, index, prefix):
    """목록에 없는 정보는 무엇을 확인했는지 직접 적고 끝낸다."""
    show_text(T["note_intro"])
    note = st.text_area(T["note_label"], key=prefix + "_note")

    if st.button(T["note_finish"], type="primary", key=prefix + "_finish"):
        if note.strip() == "":
            st.warning(T["note_empty"])
        else:
            finish_mission(incident, index, note.strip())


# ---------- 창 ----------


@st.dialog(T["mission_dialog_title"], width="medium")
def show_mission(incident, index):
    """할 일 하나를 직접 해 보는 창. 할 일의 종류에 맞는 함수를 부른다."""
    action = incident["actions"][index]
    mission_type = get_mission_type(action["name"])
    prefix = f"m_{incident['id']}_{index}"

    # 창 맨 위: 서비스 이름, 할 일 이름, 이 할 일을 끝내면 막는 공격
    tags = ""

    for attack in find_blocked_attacks(mission_type, incident["leaked_items"]):
        tags += pill(T["attack_" + attack["name"] + "_title"], "red")

    head = (
        f'<p class="mission-service">{esc(incident["service_name"])}</p>'
        f'<h2 class="mission-title">{esc(action["name"])}</h2>'
    )

    if tags != "":
        head += f'<div class="mission-tags"><span>{esc(T["mission_blocks_label"])}</span>{tags}</div>'

    st.html(head)

    # 이미 끝낸 할 일이면 결과를 보여 주고, 되돌릴 수 있게 한다.
    if action["done"]:
        result = action.get("result") or T["pill_done"]
        line = T["mission_review_line"].format(date=action["done_date"], result=result)
        st.html(verdict(True, line))

        if st.button(T["mission_undo"], key=prefix + "_undo"):
            undo_mission(incident, index)

        return

    if mission_type == "password":
        mission_password(incident, index, prefix)
    elif mission_type == "reuse":
        mission_reuse(incident, index, prefix)
    elif mission_type == "otp":
        mission_otp(incident, index, prefix)
    elif mission_type == "quiz":
        mission_quiz(incident, index, prefix)
    elif mission_type == "fss":
        mission_fss(incident, index, prefix)
    elif mission_type == "note":
        mission_note(incident, index, prefix)
    else:
        # lookup, identity, account는 확인하고 결과를 고르는 같은 방식이다.
        mission_check(incident, index, prefix, mission_type)
