# screen_settings.py
# 내 설정 창(로그인한 사람만): 학교와 알레르기를 골라 내 계정에 저장한다.

import streamlit as st

from common import esc, get_profile
from database import save_settings
from foods import ALLERGENS
from neis import NeisError, search_schools
from texts import TEXT as T


def allergy_label(code):
    """알레르기 고르는 칸에 보일 글자. 예: 10. 돼지고기"""
    return f"{code}. {ALLERGENS[code]}"


def school_label(school):
    """학교 고르는 칸에 보일 글자. 주소를 모르면 학교 종류를 붙인다. 예: 고색고등학교 (경기도 수원시 ...)"""
    return f"{school['name']} ({school.get('address', school['kind'])})"


@st.dialog(T["settings_title"], width="medium")
def show_settings():
    """내 설정 창. 학교를 찾아 고르고, 알레르기를 골라 저장한다."""
    profile = get_profile()
    st.html(f'<p class="dialog-intro">{esc(T["settings_intro"])}</p>')

    # 1. 학교 찾기: 찾은 학교는 session_state에 두고 고르는 칸에 보여 준다.
    with st.container(horizontal=True, vertical_alignment="bottom"):
        school_name = st.text_input(
            T["field_school"],
            key="school_query",
            placeholder=T["school_placeholder"],
        )
        search_clicked = st.button(T["school_search_button"], key="school_search")

    if search_clicked and school_name.strip() != "":
        try:
            total, schools = search_schools(school_name.strip())
        except NeisError:
            st.error(T["err_network"])
            total, schools = 0, []

        st.session_state["found_schools"] = schools

        if total == 0:
            st.warning(T["school_none"])
        elif total > len(schools):
            st.info(T["school_too_many"].format(count=total))

    # 찾은 학교가 없으면 지금 쓰는 학교를 그대로 고른다.
    choices = st.session_state.get("found_schools", [])

    if len(choices) == 0:
        choices = [profile["school"]]

    school = st.selectbox(T["school_pick"], choices, format_func=school_label, key="school_choice")

    # 2. 알레르기
    allergies = st.multiselect(
        T["field_allergies"],
        list(ALLERGENS),
        default=profile["allergies"],
        format_func=allergy_label,
        placeholder=T["allergies_placeholder"],
        key="allergy_choice",
    )
    st.caption(T["allergies_help"])

    # 3. 저장: 내 계정(users 테이블의 내 줄)에 저장하고, 바뀐 계정 정보를 지금 쓰는 정보로 바꾼다.
    if st.button(T["settings_save"], type="primary", key="settings_save"):
        st.session_state["user"] = save_settings(profile["id"], school, allergies)
        st.toast(T["settings_saved"])
        st.rerun()
