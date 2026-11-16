# app.py
# 유출장부를 실행하는 파일. 설정을 하고, 위쪽 메뉴를 보여 주고, 고른 화면을 부른다.
# 화면마다 파일이 하나씩 있다.
#   screen_intro.py   소개
#   screen_record.py  기록하기
#   screen_todo.py    할 일
#   screen_stats.py   통계
#   screen_play.py    체험하기
# 여러 화면이 함께 쓰는 값과 함수는 common.py에 있다.

from pathlib import Path

import streamlit as st

from common import MENU_INTRO, MENU_PLAY, MENU_RECORD, MENU_STATS, MENU_TODO, go_to
from database import create_tables
from screen_intro import show_intro
from screen_play import show_play
from screen_record import show_record
from screen_stats import show_stats
from screen_todo import show_todo
from texts import TEXT as T

APP_FOLDER = Path(__file__).resolve().parent


def show_nav():
    """위쪽 메뉴(로고, 화면 이름 다섯 개, 기록하기 버튼)를 보여 주고 고른 화면 이름을 돌려준다."""
    with st.container(
        key="nav",
        horizontal=True,
        horizontal_alignment="distribute",
        vertical_alignment="center",
    ):
        st.html(
            '<div class="brand"><img src="app/static/logo.png" alt=""><span>유출장부</span></div>',
            width="content",
        )
        menu = st.radio(
            "유출장부 메뉴",
            [MENU_INTRO, MENU_RECORD, MENU_TODO, MENU_STATS, MENU_PLAY],
            key="menu",
            horizontal=True,
            label_visibility="collapsed",
            width="content",
        )
        st.button(
            T["nav_cta"],
            type="primary",
            on_click=go_to,
            args=(MENU_RECORD, T["record_mode_manual"]),
        )

    return menu


st.set_page_config(
    page_title="유출장부",
    page_icon=str(APP_FOLDER / "static" / "logo.png"),
    layout="wide",
)

# 구역, 카드, 알약 모양 버튼 같은 화면 모양을 정하는 CSS
st.html(APP_FOLDER / "style.css")

create_tables()

# 기록을 저장한 다음 실행에서 옮겨 갈 화면이 정해져 있으면 먼저 반영한다.
if "pending_menu" in st.session_state:
    st.session_state["menu"] = st.session_state.pop("pending_menu")

menu = show_nav()

if menu == MENU_INTRO:
    show_intro()
elif menu == MENU_RECORD:
    show_record()
elif menu == MENU_TODO:
    show_todo()
elif menu == MENU_STATS:
    show_stats()
else:
    show_play()
