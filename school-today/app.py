# app.py
# 학교한눈을 실행하는 파일. 설정을 하고, 위쪽 메뉴를 보여 주고, 고른 화면을 부른다.
# 화면마다 파일이 하나씩 있다.
#   screen_today.py      오늘
#   screen_meal.py       급식
#   screen_timetable.py  시간표
#   screen_schedule.py   일정
#   screen_school.py     학교
#   screen_settings.py   내 설정 창
# 나이스 포털에서 자료를 받는 코드는 neis.py, 직접 등록한 자료를 저장하는 코드는 database.py에 있다.

from pathlib import Path

import streamlit as st

from common import MENU_MEAL, MENU_SCHEDULE, MENU_SCHOOL, MENU_TIMETABLE, MENU_TODAY, esc
from database import create_tables, load_profile
from screen_meal import show_meal
from screen_schedule import show_schedule
from screen_school import show_school
from screen_settings import show_settings
from screen_timetable import show_timetable
from screen_today import show_today
from texts import TEXT as T

APP_FOLDER = Path(__file__).resolve().parent


def show_nav():
    """위쪽 메뉴(로고, 화면 이름 다섯 개, 내 설정 버튼)를 보여 주고 고른 화면 이름을 돌려준다."""
    with st.container(
        key="nav",
        horizontal=True,
        horizontal_alignment="distribute",
        vertical_alignment="center",
    ):
        st.html(
            f'<div class="brand"><span class="brand-mark"></span>{esc(T["app_name"])}</div>',
            width="content",
        )
        menu = st.radio(
            T["app_name"],
            [MENU_TODAY, MENU_MEAL, MENU_TIMETABLE, MENU_SCHEDULE, MENU_SCHOOL],
            key="menu",
            horizontal=True,
            label_visibility="collapsed",
            width="content",
        )

        if st.button(T["nav_settings"], type="primary", key="nav_settings"):
            show_settings()

    return menu


st.set_page_config(
    page_title=T["app_name"],
    page_icon=":material/calendar_month:",
    layout="wide",
)

# 구역, 카드, 알약 모양 버튼 같은 화면 모양을 정하는 CSS
st.html(APP_FOLDER / "style.css")

create_tables()

# 주소창에 ?me=이름표 가 있으면 처음 열 때 그 설정을 불러온다.
if "profile" not in st.session_state and "me" in st.query_params:
    loaded = load_profile(st.query_params["me"])

    if loaded is not None:
        st.session_state["profile"] = loaded

menu = show_nav()

if menu == MENU_TODAY:
    show_today()
elif menu == MENU_MEAL:
    show_meal()
elif menu == MENU_TIMETABLE:
    show_timetable()
elif menu == MENU_SCHEDULE:
    show_schedule()
else:
    show_school()
