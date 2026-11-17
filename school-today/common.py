# common.py
# 여러 화면이 함께 쓰는 값과 함수
#   1. 기본값: 기본 학교, 기본 설정, 메뉴 이름
#   2. HTML 조각: esc, pill, spec_row 같은 작은 조각
#   3. 날짜 글자: date_short, date_long, dday_text
#   4. 함께 쓰는 화면 부분: 화면 제목, 주 바꾸기 버튼, 화면 아래 출처
#
# 사용자가 입력한 글자는 esc()로 바꿔서 HTML에 넣는다.
# 그대로 넣으면 입력한 글자가 HTML 태그로 동작할 수 있기 때문이다.

import html
from datetime import timedelta

import streamlit as st

from days import d_day, monday_of, today_kst
from texts import TEXT as T

# ---------- 1. 기본값 ----------

# 내 설정을 저장하기 전에 보여 줄 학교
DEFAULT_SCHOOL = {
    "name": "고색고등학교",
    "kind": "고등학교",
    "atpt_code": "J10",
    "school_code": "7530878",
}

DEFAULT_PROFILE = {
    "nickname": "",
    "school": DEFAULT_SCHOOL,
    "grade": 2,
    "class_nm": 1,
    "allergies": [],
}

MENU_TODAY = T["menu_today"]
MENU_MEAL = T["menu_meal"]
MENU_TIMETABLE = T["menu_timetable"]
MENU_SCHEDULE = T["menu_schedule"]
MENU_SCHOOL = T["menu_school"]


def get_profile():
    """지금 쓰는 설정을 돌려준다. 저장한 설정이 없으면 기본 설정이다."""
    return st.session_state.get("profile", DEFAULT_PROFILE)


def has_profile():
    """내 설정을 저장했거나 불러왔는지 알려 준다."""
    return "profile" in st.session_state


def go_to(menu):
    """버튼을 누르면 다른 화면으로 옮긴다."""
    st.session_state["menu"] = menu


# ---------- 2. HTML 조각 ----------


def esc(text):
    """글자를 HTML에 안전하게 넣을 수 있도록 바꾼다."""
    return html.escape(str(text))


def pill(text, tone):
    """알약 모양 표시를 만든다. tone은 red, yellow, mint, navy, gray 중 하나."""
    return f'<span class="pill pill-{tone}">{esc(text)}</span>'


def spec_row(label, value):
    """이름은 왼쪽, 값은 오른쪽에 두는 한 줄을 만든다. value는 HTML이다."""
    return f'<div class="spec"><span>{esc(label)}</span><strong>{value}</strong></div>'


def card(title, body, tone=""):
    """제목과 내용(HTML)이 있는 카드 하나를 만든다. tone이 alert면 빨간 테두리다."""
    return (
        f'<div class="info-card {tone}">'
        f'<h3 class="info-card-title">{esc(title)}</h3>{body}</div>'
    )


# ---------- 3. 날짜 글자 ----------


def weekday_name(day):
    """요일 한 글자. weekday()는 월요일이 0이다."""
    return T["weekdays"][day.weekday()]


def date_short(day):
    """11.17 (화) 모양의 짧은 날짜"""
    return T["date_short"].format(month=day.month, day=day.day, weekday=weekday_name(day))


def date_long(day):
    """11월 17일 화요일 모양의 날짜"""
    return T["date_long"].format(month=day.month, day=day.day, weekday=weekday_name(day))


def dday_text(target):
    """오늘부터 target까지 남은 날을 글자로 바꾼다. 오늘이면 '오늘'이다."""
    days = d_day(target, today_kst())

    if days == 0:
        return T["dday_today"]

    return T["dday_left"].format(days=days)


# ---------- 4. 함께 쓰는 화면 부분 ----------


def show_page_head(title, intro):
    """화면 제목과 한 줄 설명을 보여 준다."""
    st.html(f'<h1 class="title">{esc(title)}</h1><p class="lead">{esc(intro)}</p>')


def move_week(key, days):
    """주 바꾸기 버튼을 누르면 보고 있는 주의 월요일을 days일만큼 옮긴다. 0이면 이번 주다."""
    if days == 0:
        st.session_state[key] = monday_of(today_kst())
    else:
        st.session_state[key] = st.session_state[key] + timedelta(days=days)


def show_week_nav(key):
    """
    지난주·이번 주·다음 주 버튼과 지금 보는 주를 보여 준다.

    key는 보고 있는 주의 월요일을 session_state에 둘 이름이다. 그 월요일을 돌려준다.
    """
    if key not in st.session_state:
        st.session_state[key] = monday_of(today_kst())

    monday = st.session_state[key]
    friday = monday + timedelta(days=4)

    with st.container(horizontal=True, vertical_alignment="center", key=key + "_nav"):
        st.button(T["week_prev"], key=key + "_prev", on_click=move_week, args=(key, -7))
        st.button(T["week_this"], key=key + "_this", on_click=move_week, args=(key, 0))
        st.button(T["week_next"], key=key + "_next", on_click=move_week, args=(key, 7))
        st.html(
            f'<span class="nav-label">'
            f"{esc(T['week_label'].format(start=date_short(monday), end=date_short(friday)))}</span>"
        )

    return monday


def show_source():
    """화면 맨 아래에 자료 출처를 작게 보여 준다."""
    st.html(f'<p class="source">{esc(T["source_note"])}</p>')
