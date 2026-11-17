# screen_settings.py
# 내 설정 창: 학교, 학년, 반, 알레르기를 이름표(별명)로 저장하고 다시 불러온다.
# 저장한 이름표는 주소창의 ?me=이름표 에도 남아서, 새로고침해도 내 설정이 유지된다.

import streamlit as st

from common import esc, get_profile
from database import load_profile, save_profile
from foods import ALLERGENS
from neis import NeisError, count_classes, search_schools
from days import today_kst
from texts import TEXT as T

# 학교 종류마다 학년 수
GRADE_COUNTS = {
    "초등학교": 6,
    "중학교": 3,
    "고등학교": 3,
}


def use_profile(profile):
    """설정을 지금 쓰는 설정으로 정하고, 주소창에 이름표를 남긴다."""
    st.session_state["profile"] = profile
    st.query_params["me"] = profile["nickname"]


def allergy_label(code):
    """알레르기 고르는 칸에 보일 글자. 예: 10. 돼지고기"""
    return f"{code}. {ALLERGENS[code]}"


def school_label(school):
    """학교 고르는 칸에 보일 글자. 주소를 모르면 학교 종류를 붙인다. 예: 고색고등학교 (경기도 수원시 ...)"""
    return f"{school['name']} ({school.get('address', school['kind'])})"


@st.dialog(T["settings_title"], width="medium")
def show_settings():
    """내 설정 창. 위에는 불러오기, 아래에는 저장하기가 있다."""
    profile = get_profile()
    st.html(f'<p class="dialog-intro">{esc(T["settings_intro"])}</p>')

    # 1. 이름표로 불러오기
    with st.container(horizontal=True, vertical_alignment="bottom"):
        load_name = st.text_input(T["load_label"], key="load_name")
        load_clicked = st.button(T["load_button"], key="load_button")

    if load_clicked:
        loaded = load_profile(load_name)

        if loaded is None:
            st.warning(T["load_none"])
        else:
            use_profile(loaded)
            st.toast(T["load_done"].format(nickname=loaded["nickname"]))
            st.rerun()

    st.divider()

    # 2. 학교 찾기: 찾은 학교는 session_state에 두고 고르는 칸에 보여 준다.
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

    # 3. 학년과 반: 반 수는 나이스 포털에서 센다. 못 세면 15반까지 보여 준다.
    grade_count = GRADE_COUNTS.get(school["kind"], 3)
    grades = list(range(1, grade_count + 1))
    grade = st.selectbox(
        T["field_grade"],
        grades,
        index=min(profile["grade"], grade_count) - 1,
        key="grade_choice",
    )

    try:
        class_count = count_classes(school, today_kst().year, grade)
    except NeisError:
        class_count = 0

    if class_count == 0:
        class_count = 15

    classes = list(range(1, class_count + 1))
    class_nm = st.selectbox(
        T["field_class"],
        classes,
        index=min(profile["class_nm"], class_count) - 1,
        key="class_choice",
    )

    # 4. 알레르기
    allergies = st.multiselect(
        T["field_allergies"],
        list(ALLERGENS),
        default=profile["allergies"],
        format_func=allergy_label,
        placeholder=T["allergies_placeholder"],
        key="allergy_choice",
    )
    st.caption(T["allergies_help"])

    # 5. 이름표와 저장
    nickname = st.text_input(T["field_nickname"], value=profile["nickname"], key="nickname_input")
    st.caption(T["nickname_help"])

    if st.button(T["settings_save"], type="primary", key="settings_save"):
        status = save_profile(nickname, school, grade, class_nm, allergies)

        if status == "EMPTY":
            st.warning(T["err_no_nickname"])
        else:
            use_profile(load_profile(nickname))
            st.toast(T["settings_saved"].format(nickname=nickname.strip()))
            st.rerun()

    st.caption(T["shared_notice"])
