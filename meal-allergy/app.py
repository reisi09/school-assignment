# app.py
# 급식 알레르기를 실행하는 파일. 설정을 하고, 위쪽 메뉴를 보여 주고, 고른 화면을 부른다.
# 화면마다 파일이 하나씩 있다.
#   screen_today.py     오늘
#   screen_meal.py      급식표
#   screen_search.py    찾기
#   screen_settings.py  내 설정 창
#   screen_account.py   로그인·회원가입 창
# 나이스 포털에서 자료를 받는 코드는 neis.py, SQLite에 저장하는 코드(계정·급식 기록)는 database.py에 있다.

from pathlib import Path

import streamlit as st

from common import MENU_SEARCH, MENU_TODAY, MENU_WEEK, esc, is_logged_in
from database import create_tables
from screen_account import log_out, show_login, show_recovery_code
from screen_meal import show_meal
from screen_search import show_search
from screen_settings import show_settings
from screen_today import show_today
from texts import TEXT as T

APP_FOLDER = Path(__file__).resolve().parent


def show_nav():
    """위쪽 메뉴(로고, 화면 이름 세 개, 오른쪽 버튼)를 보여 주고 고른 화면 이름을 돌려준다."""
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
            [MENU_TODAY, MENU_WEEK, MENU_SEARCH],
            key="menu",
            horizontal=True,
            label_visibility="collapsed",
            width="content",
        )

        # 오른쪽 버튼: 로그인 전에는 [로그인], 로그인 뒤에는 [내 설정] [로그아웃]
        with st.container(horizontal=True, width="content", key="nav_buttons"):
            if is_logged_in():
                if st.button(T["nav_settings"], type="primary", key="nav_settings"):
                    show_settings()

                st.button(T["nav_logout"], key="nav_logout", on_click=log_out)

            elif st.button(T["nav_login"], type="primary", key="nav_login"):
                show_login()

    return menu


st.set_page_config(
    page_title=T["app_name"],
    page_icon=":material/no_meals:",
    layout="wide",
)

# 구역, 카드, 알약 모양 표시 같은 화면 모양을 정하는 CSS
st.html(APP_FOLDER / "style.css")

create_tables()

menu = show_nav()

# 가입하거나 비밀번호를 바꾼 직후에는 새 복구 코드 창을 한 번 띄운다.
if "recovery_code" in st.session_state:
    show_recovery_code()

if menu == MENU_TODAY:
    show_today()
elif menu == MENU_WEEK:
    show_meal()
else:
    show_search()
