# screen_play.py
# 체험하기 화면: 해커 시점 체험과 사칭 문자 가려내기
# 문제와 공격 수법 자료는 play.py에, 문구는 texts.py에 있다.
# 사칭 문자 문제 하나를 보여 주는 show_quiz_question()은 할 일 창(screen_missions.py)도 쓴다.

import streamlit as st

from common import (
    MENU_RECORD,
    chips,
    confetti,
    count_number,
    esc,
    gauge,
    go_to,
    phone,
    pill,
    risk_pill,
    show_page_head,
    stamp,
    verdict,
)
from database import add_quiz_result, get_incidents, get_quiz_summary
from play import FAKE, QUIZ, REAL, find_attacks, order_quiz
from rules import ITEM_WEIGHTS, calc_risk_score, make_actions
from texts import TEXT as T

# 모든 정보가 유출됐을 때의 위험 점수. 해커 시점 체험의 계기판이 가득 차는 점수다.
MAX_SCORE = calc_risk_score(list(ITEM_WEIGHTS))


def start_record_from_play():
    """해커 시점 체험에서 고른 정보를 채운 채로 기록하기 화면으로 옮긴다."""
    st.session_state["record_items"] = st.session_state["hacker_items"]
    go_to(MENU_RECORD, T["record_mode_manual"])


# ---------- 사칭 문자 문제 (체험하기 화면과 할 일 창이 함께 쓴다) ----------
# 문제를 푸는 동안의 값은 session_state에 prefix로 시작하는 key로 둔다.
#   prefix_pos     지금 문제의 순서(0부터)
#   prefix_marks   지금까지 답이 맞았는지(True/False) 목록
#   prefix_choice  지금 문제에서 고른 답. 아직 안 골랐으면 None


def answer_quiz(prefix, order, choice):
    """답 버튼을 누르면 고른 답과 맞았는지를 남긴다."""
    # 이미 답한 문제는 다시 채점하지 않는다.
    if st.session_state.get(prefix + "_choice") is not None:
        return

    position = st.session_state.get(prefix + "_pos", 0)
    question = QUIZ[order[position]]
    marks = st.session_state.get(prefix + "_marks", [])

    st.session_state[prefix + "_choice"] = choice
    st.session_state[prefix + "_marks"] = marks + [choice == question["answer"]]


def next_quiz(prefix):
    """다음 문제로 넘어간다."""
    st.session_state[prefix + "_pos"] = st.session_state.get(prefix + "_pos", 0) + 1
    st.session_state[prefix + "_choice"] = None


def show_quiz_question(prefix, order, leaked_items):
    """
    사칭 문자 문제를 하나씩 보여 준다. order는 낼 문제의 순서(QUIZ에서의 위치) 목록이다.

    문제를 다 풀었으면 맞힌 문제 수를 돌려주고, 아직 푸는 중이면 None을 돌려준다.
    """
    position = st.session_state.get(prefix + "_pos", 0)
    marks = st.session_state.get(prefix + "_marks", [])
    choice = st.session_state.get(prefix + "_choice")
    total = len(order)

    if position >= total:
        return marks.count(True)

    index = order[position]
    question = QUIZ[index]

    # 진행 점: 맞힌 문제는 민트, 틀린 문제는 빨강, 지금 문제는 테두리만
    dots = ""

    for number in range(total):
        if number < len(marks) and marks[number]:
            dots += '<span class="dot is-right"></span>'
        elif number < len(marks):
            dots += '<span class="dot is-wrong"></span>'
        elif number == position:
            dots += '<span class="dot is-now"></span>'
        else:
            dots += '<span class="dot"></span>'

    head = (
        f'<div class="quiz-head"><div class="dots">{dots}</div>'
        f"<span>{esc(T['quiz_progress'].format(number=position + 1, total=total))}</span>"
    )

    # 내 기록에서 유출된 정보와 관련된 문제면 표시를 붙인다.
    if question["item"] in leaked_items:
        head += pill(T["quiz_match"].format(item=question["item"]), "mint")

    head += "</div>"

    message = T[f"quiz{index + 1}_message"]

    # 아직 답하지 않았으면 '입력 중' 표시 뒤에 문자가 도착한다.
    if choice is None:
        st.html(head + phone(message, T["otp_phone_title"], "is-arriving"))
        st.html(f'<p class="quiz-message">{esc(T["quiz_question"])}</p>')

        with st.container(horizontal=True):
            st.button(
                T["quiz_real_button"],
                key=prefix + "_answer_real",
                on_click=answer_quiz,
                args=(prefix, order, REAL),
            )
            st.button(
                T["quiz_fake_button"],
                key=prefix + "_answer_fake",
                on_click=answer_quiz,
                args=(prefix, order, FAKE),
            )

        return None

    # 답했으면 문자 위에 정답 도장을 찍는다. 틀렸으면 휴대전화가 흔들린다.
    right = choice == question["answer"]

    if question["answer"] == REAL:
        mark = stamp(T["quiz_real_button"], "mint")
        answer_text = T["quiz_answer_real"]
    else:
        mark = stamp(T["quiz_fake_button"], "red")
        answer_text = T["quiz_answer_fake"]

    if right:
        state = "is-right"
        result = T["quiz_correct"] + ". " + answer_text
    else:
        state = "is-wrong"
        result = T["quiz_wrong"] + ". " + answer_text

    st.html(
        head
        + phone(message, T["otp_phone_title"], state, mark)
        + verdict(right, result)
        + f'<p class="quiz-message">{esc(T[f"quiz{index + 1}_reason"])}</p>'
    )

    if position + 1 == total:
        next_label = T["quiz_finish"]
    else:
        next_label = T["quiz_next"]

    st.button(next_label, type="primary", key=prefix + "_next", on_click=next_quiz, args=(prefix,))

    return None


# ---------- 체험하기 화면 ----------


def show_hacker():
    """해커 시점 체험: 정보를 고르면 계기판과 공격자가 할 수 있는 일이 바로 바뀐다."""
    left, right = st.columns([7, 5], gap="large")

    with left:
        # 정보를 누를 때마다 화면이 다시 그려진다.
        selected = st.pills(
            T["hacker_pick_label"],
            list(ITEM_WEIGHTS),
            selection_mode="multi",
            key="hacker_items",
        )
        attacks = find_attacks(selected)

        # 지난번에 보인 공격을 기억해 두고, 새로 생긴 공격만 움직이며 나타나게 한다.
        shown_before = st.session_state.get("hacker_shown_attacks", [])
        shown_now = []

        for attack in attacks:
            shown_now.append(attack["name"])

        st.session_state["hacker_shown_attacks"] = shown_now

        if len(selected) == 0:
            st.html(f'<div class="empty">{esc(T["hacker_empty"])}</div>')
        elif len(attacks) == 0:
            st.html(f'<div class="empty">{esc(T["hacker_none"])}</div>')
        else:
            rows = ""

            for number, attack in enumerate(attacks, start=1):
                new = ""

                if attack["name"] not in shown_before:
                    new = " is-new"

                rows += (
                    f'<div class="attack{new}"><span class="step-number">{number}</span><div>'
                    f"<h3>{esc(T['attack_' + attack['name'] + '_title'])}</h3>"
                    f"<p>{esc(T['attack_' + attack['name'] + '_body'])}</p>"
                    f'<div class="attack-needs"><span>{esc(T["hacker_needs_label"])}</span>'
                    f"{chips(attack['needs'])}</div></div></div>"
                )

            st.html(
                f'<h2 class="group-title">{esc(T["hacker_list_title"])}</h2>'
                f'<div class="attacks">{rows}</div>'
            )

    with right:
        # 남색 카드: 계기판, 위험 등급, 해야 할 일
        score = calc_risk_score(selected)

        # 지난번 점수에서 지금 점수까지 바늘이 움직이게 지난번 점수를 기억한다.
        previous = st.session_state.get("hacker_shown_score", 0)
        st.session_state["hacker_shown_score"] = score

        actions = ""

        if len(selected) > 0:
            for action_name in make_actions(selected):
                actions += f"<li>{esc(action_name)}</li>"

            actions = f"<h3>{esc(T['hacker_actions_title'])}</h3><ul>{actions}</ul>"

        st.html(
            '<div class="score-card">'
            f'<div class="score-head"><span class="score-label">{esc(T["hacker_score_label"])}</span>'
            f"{risk_pill(score)}</div>"
            f"{gauge(score, previous, MAX_SCORE)}"
            f"{actions}</div>"
        )

        if len(selected) > 0:
            st.button(
                T["hacker_record_button"],
                type="primary",
                on_click=start_record_from_play,
                width="stretch",
            )

    st.caption(T["hacker_notice"])


def restart_quiz():
    """사칭 문자 가려내기를 처음부터 다시 시작한다."""
    for key in ["quiz_order", "quiz_pos", "quiz_marks", "quiz_choice", "quiz_saved"]:
        st.session_state.pop(key, None)


def show_quiz():
    """사칭 문자 가려내기: 문자를 하나씩 보고 진짜 안내인지 사칭인지 고른다."""
    # 내 기록에서 유출된 정보를 모은다.
    leaked_items = []

    for incident in get_incidents():
        leaked_items += incident["leaked_items"]

    # 문제 순서는 시작할 때 한 번만 정한다. 유출된 정보와 관련된 문제가 앞에 온다.
    if "quiz_order" not in st.session_state:
        st.session_state["quiz_order"] = order_quiz(leaked_items)

    order = st.session_state["quiz_order"]
    total = len(order)

    with st.container(key="card_quiz"):
        score = show_quiz_question("quiz", order, leaked_items)

        # 다 풀었으면 결과를 한 번만 저장하고 결과를 보여 준다.
        if score is not None:
            celebrate = False

            if not st.session_state.get("quiz_saved", False):
                add_quiz_result(score, total)
                st.session_state["quiz_saved"] = True
                celebrate = score == total

            best, count = get_quiz_summary()

            if score == total:
                message = T["quiz_result_all"]
            else:
                message = T["quiz_result_some"]

            st.html(
                f'<div class="quiz-score"><b>{count_number(score, 0)}</b><span>/ {total}</span></div>'
                f'<p class="card-meta">{esc(T["quiz_result_label"].format(total=total))}</p>'
                f'<p class="quiz-message">{esc(message)}</p>'
                f'<p class="card-note">'
                f"{esc(T['quiz_best'].format(best=best, total=total, count=count))}</p>"
            )

            # 모두 맞힌 순간에만 색종이를 뿌린다.
            if celebrate:
                st.html(confetti())

            st.button(T["quiz_retry"], type="primary", on_click=restart_quiz)

    st.caption(T["quiz_notice"])


def show_play():
    """체험하기 화면: 해커 시점 체험과 사칭 문자 가려내기 중 하나를 골라서 해 본다."""
    with st.container(key="sec_page"):
        show_page_head(T["play_title"], T["play_intro"])

        if "play_mode" not in st.session_state:
            st.session_state["play_mode"] = T["play_mode_hacker"]

        mode = st.segmented_control(
            T["play_mode_label"],
            [T["play_mode_hacker"], T["play_mode_quiz"]],
            key="play_mode",
            label_visibility="collapsed",
        )

        if mode == T["play_mode_quiz"]:
            show_quiz()
        else:
            show_hacker()
