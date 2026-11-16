# screen_play.py
# 체험하기 화면: 해커 시점 체험과 사칭 문자 가려내기
# 문제와 공격 수법 자료는 play.py에, 문구는 texts.py에 있다.

import streamlit as st

from common import (
    MENU_RECORD,
    chips,
    esc,
    go_to,
    pill,
    progress_bar,
    risk_pill,
    show_page_head,
)
from database import add_quiz_result, get_incidents, get_quiz_summary
from play import FAKE, QUIZ, REAL, find_attacks, order_quiz
from rules import ITEM_WEIGHTS, calc_risk_score, make_actions
from texts import TEXT as T

# 모든 정보가 유출됐을 때의 위험 점수. 해커 시점 체험의 막대 길이를 정할 때 쓴다.
MAX_SCORE = calc_risk_score(list(ITEM_WEIGHTS))


def start_record_from_play():
    """해커 시점 체험에서 고른 정보를 채운 채로 기록하기 화면으로 옮긴다."""
    st.session_state["record_items"] = st.session_state["hacker_items"]
    go_to(MENU_RECORD, T["record_mode_manual"])


def answer_quiz(choice):
    """사칭 문자 가려내기에서 답을 고르면 맞았는지 확인해 점수에 더한다."""
    # 이미 답한 문제는 다시 채점하지 않는다.
    if st.session_state["quiz_choice"] is not None:
        return

    index = st.session_state["quiz_order"][st.session_state["quiz_pos"]]
    st.session_state["quiz_choice"] = choice

    if choice == QUIZ[index]["answer"]:
        st.session_state["quiz_score"] += 1


def next_quiz():
    """다음 문제로 넘어간다. 마지막 문제였으면 결과를 저장한다."""
    st.session_state["quiz_pos"] += 1
    st.session_state["quiz_choice"] = None

    if st.session_state["quiz_pos"] == len(QUIZ):
        add_quiz_result(st.session_state["quiz_score"], len(QUIZ))


def restart_quiz():
    """사칭 문자 가려내기를 처음부터 다시 시작한다."""
    for key in ["quiz_order", "quiz_pos", "quiz_score", "quiz_choice"]:
        del st.session_state[key]


def show_hacker():
    """해커 시점 체험: 정보를 고르면 위험 점수와 공격자가 할 수 있는 일이 바로 바뀐다."""
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

        if len(selected) == 0:
            st.html(f'<div class="empty">{esc(T["hacker_empty"])}</div>')
        elif len(attacks) == 0:
            st.html(f'<div class="empty">{esc(T["hacker_none"])}</div>')
        else:
            rows = ""

            for number, attack in enumerate(attacks, start=1):
                rows += (
                    f'<div class="attack"><span class="step-number">{number}</span><div>'
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
        # 남색 카드: 위험 점수, 막대, 해야 할 일
        score = calc_risk_score(selected)
        percent = round(score / MAX_SCORE * 100)
        actions = ""

        if len(selected) > 0:
            for action_name in make_actions(selected):
                actions += f"<li>{esc(action_name)}</li>"

            actions = f"<h3>{esc(T['hacker_actions_title'])}</h3><ul>{actions}</ul>"

        st.html(
            '<div class="score-card">'
            f'<span class="score-label">{esc(T["hacker_score_label"])}</span>'
            f'<div class="score-number"><b>{score}</b><span>{esc(T["score_unit"])}</span>'
            f"{risk_pill(score)}</div>"
            f'<div class="meter"><div style="width: {percent}%"></div></div>'
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


def show_quiz():
    """사칭 문자 가려내기: 문자 예시를 하나씩 보고 진짜 안내인지 사칭인지 고른다."""
    # 내 기록에서 유출된 정보를 모은다.
    leaked_items = []

    for incident in get_incidents():
        leaked_items += incident["leaked_items"]

    # 문제 순서는 시작할 때 한 번만 정한다. 유출된 정보와 관련된 문제가 앞에 온다.
    if "quiz_order" not in st.session_state:
        st.session_state["quiz_order"] = order_quiz(leaked_items)
        st.session_state["quiz_pos"] = 0
        st.session_state["quiz_score"] = 0
        st.session_state["quiz_choice"] = None

    position = st.session_state["quiz_pos"]
    score = st.session_state["quiz_score"]
    total = len(QUIZ)

    with st.container(key="card_quiz"):
        # 문제를 다 풀었으면 결과를 보여 준다.
        if position >= total:
            best, count = get_quiz_summary()

            if score == total:
                message = T["quiz_result_all"]
            else:
                message = T["quiz_result_some"]

            st.html(
                f'<div class="quiz-score"><b>{score}</b><span>/ {total}</span></div>'
                f'<p class="card-meta">{esc(T["quiz_result_label"].format(total=total))}</p>'
                f'<p class="quiz-message">{esc(message)}</p>'
                f'<p class="card-note">'
                f"{esc(T['quiz_best'].format(best=best, total=total, count=count))}</p>"
            )
            st.button(T["quiz_retry"], type="primary", on_click=restart_quiz)

        else:
            index = st.session_state["quiz_order"][position]
            question = QUIZ[index]
            choice = st.session_state["quiz_choice"]

            # 내 기록에서 유출된 정보와 관련된 문제면 표시를 붙인다.
            match = ""

            if question["item"] in leaked_items:
                match = pill(T["quiz_match"].format(item=question["item"]), "mint")

            progress_text = T["quiz_progress"].format(number=position + 1, total=total)

            st.html(
                progress_bar(progress_text, position + 1, total)
                + f'<div class="sms-head">{match}</div>'
                + f'<div class="sms">{esc(T[f"quiz{index + 1}_message"])}</div>'
            )

            # 아직 답하지 않았으면 버튼 두 개를 보여 준다.
            if choice is None:
                st.html(f'<p class="quiz-message">{esc(T["quiz_question"])}</p>')

                with st.container(horizontal=True):
                    st.button(T["quiz_real_button"], on_click=answer_quiz, args=(REAL,))
                    st.button(T["quiz_fake_button"], on_click=answer_quiz, args=(FAKE,))

            # 답했으면 정답과 이유를 알려 준다.
            else:
                if question["answer"] == REAL:
                    answer_text = T["quiz_answer_real"]
                else:
                    answer_text = T["quiz_answer_fake"]

                if choice == question["answer"]:
                    st.success(T["quiz_correct"] + ". " + answer_text)
                else:
                    st.error(T["quiz_wrong"] + ". " + answer_text)

                st.html(f'<p class="quiz-message">{esc(T[f"quiz{index + 1}_reason"])}</p>')

                if position + 1 == total:
                    next_label = T["quiz_finish"]
                else:
                    next_label = T["quiz_next"]

                st.button(next_label, type="primary", on_click=next_quiz)

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
