# screen_search.py
# 찾기 화면: 메뉴 이름이나 알레르기 식품으로 급식 기록을 찾는다.
# 찾기 전에 지난 4주와 앞으로 4주 급식을 나이스 포털에서 받아 SQLite meals 테이블에 저장한다.
# 그래서 한 번 저장된 급식은 4주가 지나도 계속 찾을 수 있다.

from datetime import timedelta

import streamlit as st

from common import date_short, esc, get_profile, pill, show_page_head, show_source
from database import count_meals, save_meals, search_meals
from days import today_kst
from foods import ALLERGENS
from neis import NeisError, fetch_meals
from screen_meal import dishes_html
from screen_settings import allergy_label
from texts import TEXT as T

# 찾기 전에 오늘 앞뒤로 이만큼(일)의 급식을 저장한다.
SAVE_DAYS = 28


def results_html(found, my_codes):
    """찾은 메뉴를 한 줄씩 HTML로 만든다. 줄마다 날짜·끼니 아래에 메뉴와 번호가 있다."""
    rows = ""

    for item in found:
        today_tag = ""

        if item["meal_date"] == today_kst():
            today_tag = pill(T["today_mark"], "mint")

        rows += (
            f'<div class="result-row">'
            f'<span class="result-date">{esc(date_short(item["meal_date"]))} · {esc(item["meal_name"])}{today_tag}</span>'
            f'{dishes_html([(item["dish"], item["codes"])], my_codes)}</div>'
        )

    return f'<div class="soft">{rows}</div>'


def show_search():
    """찾기 화면"""
    profile = get_profile()
    school = profile["school"]

    with st.container(key="sec_page"):
        show_page_head(T["search_title"], T["search_intro"])

        with st.form("meal_search"):
            with st.container(horizontal=True, vertical_alignment="bottom"):
                keyword = st.text_input(
                    T["search_keyword_label"],
                    placeholder=T["search_keyword_placeholder"],
                    width=280,
                )
                allergen = st.selectbox(
                    T["search_allergen_label"],
                    list(ALLERGENS),
                    index=None,
                    format_func=allergy_label,
                    placeholder=T["search_allergen_placeholder"],
                    width=260,
                )
                submitted = st.form_submit_button(T["search_button"], type="primary")

        st.caption(T["search_range"])

        if submitted:
            if keyword.strip() == "" and allergen is None:
                st.warning(T["err_search_empty"])
            else:
                today = today_kst()

                # 먼저 앞뒤 4주 급식을 저장한다. 연결에 실패해도 이미 저장된 기록에서는 찾는다.
                try:
                    meals = fetch_meals(
                        school,
                        today - timedelta(days=SAVE_DAYS),
                        today + timedelta(days=SAVE_DAYS),
                    )
                    save_meals(school["school_code"], meals)
                except NeisError:
                    st.error(T["err_network"])

                found = search_meals(school["school_code"], keyword.strip(), allergen)

                if len(found) == 0:
                    st.html(f'<div class="empty">{esc(T["search_none"])}</div>')
                else:
                    st.html(
                        f'<p class="summary">{esc(T["search_result"].format(count=len(found)))}</p>'
                        + results_html(found, profile["allergies"])
                    )

        st.caption(T["search_saved_count"].format(count=count_meals(school["school_code"])))
        show_source()
