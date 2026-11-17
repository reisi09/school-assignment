# screen_today.py
# 오늘 화면: 오늘 급식의 알레르기 경고, 이번 주 미리 보기, 내 알레르기를 한 화면에 모은다.

from datetime import timedelta

import streamlit as st

from common import MENU_WEEK, date_long, date_short, esc, get_profile, go_to, pill, show_source
from days import monday_of, school_days, today_kst
from foods import ALLERGENS, count_risky_dishes, parse_dishes, parse_kcal
from neis import NeisError, fetch_meals, fetch_schedule
from screen_meal import dishes_html, empty_message, group_holidays, group_meals
from screen_settings import show_settings
from texts import TEXT as T


def dishes_of(meals):
    """그날 급식(끼니별) 메뉴를 한 목록으로 모은다."""
    dishes = []

    for meal in meals:
        dishes += parse_dishes(meal["dishes"])

    return dishes


def show_hero(profile):
    """맨 위: 오늘 날짜와 학교. 알레르기를 등록하지 않았으면 등록을 권한다."""
    school_name = profile["school"]["name"]

    with st.container(key="sec_hero"):
        st.html(
            f'<p class="hero-who">{esc(school_name)}</p>'
            f'<h1 class="hero-title">{esc(date_long(today_kst()))}</h1>'
        )

        if len(profile["allergies"]) == 0:
            with st.container(key="card_setup"):
                st.html(
                    f'<h2 class="setup-title">{esc(T["setup_title"])}</h2>'
                    f'<p class="setup-body">{esc(T["setup_body"].format(school=school_name))}</p>'
                )

                if st.button(T["setup_button"], type="primary", key="setup_open"):
                    show_settings()


def show_meal_card(profile, meals, holiday_names):
    """오늘 급식 카드. 내 알레르기 식품이 든 메뉴 수를 맨 위에 알려 준다."""
    my_codes = profile["allergies"]

    with st.container(key="card_today_meal"):
        if len(meals) == 0:
            body = f'<p class="muted">{esc(T["today_meal_none"])}</p>'

            # 쉬는 날이면 그 이름을 함께 보여 준다. 예: 재량휴업일
            if len(holiday_names) > 0:
                body += f'<p class="muted">{esc(", ".join(holiday_names))}</p>'
        else:
            risky = count_risky_dishes(dishes_of(meals), my_codes)

            if len(my_codes) == 0:
                body = f'<p class="alert-line">{esc(T["today_allergy_unset"])}</p>'
            elif risky > 0:
                body = f'<p class="alert-line is-red">{esc(T["today_allergy_warn"].format(count=risky))}</p>'
            else:
                body = f'<p class="alert-line is-mint">{esc(T["today_allergy_safe"])}</p>'

            for meal in meals:
                body += dishes_html(parse_dishes(meal["dishes"]), my_codes)
                body += (
                    f'<p class="meal-meta"><b>{parse_kcal(meal["kcal"]):,.0f}</b> '
                    f'{esc(T["kcal_unit"])} · {esc(meal["meal"])}</p>'
                )

        st.html(f'<h3 class="info-card-title">{esc(T["today_meal_title"])}</h3>{body}')
        st.button(T["today_more_week"], key="more_week", on_click=go_to, args=(MENU_WEEK,))


def day_status(day, meals, holidays, my_codes):
    """이번 주 미리 보기 한 줄의 오른쪽 알약. 그날 내 알레르기 메뉴 수를 알려 준다."""
    if len(meals) == 0:
        if day in holidays:
            return pill(", ".join(holidays[day]), "gray")

        return pill(empty_message(day, holidays), "gray")

    dishes = dishes_of(meals)

    if len(my_codes) == 0:
        return pill(T["week_summary_dishes"].format(count=len(dishes)), "gray")

    risky = count_risky_dishes(dishes, my_codes)

    if risky > 0:
        return pill(T["week_summary_risky"].format(count=risky), "red")

    return pill(T["week_summary_safe"], "mint")


def show_week_card(profile, monday, by_day, holidays):
    """이번 주 미리 보기 카드: 월~금 날짜마다 내 알레르기 메뉴 수를 보여 준다."""
    rows = ""

    for day in school_days(monday):
        status = day_status(day, by_day.get(day, []), holidays, profile["allergies"])
        today_class = ""

        if day == today_kst():
            today_class = ' class="is-today"'

        rows += f"<li{today_class}><span>{esc(date_short(day))}</span>{status}</li>"

    with st.container(key="card_today_week"):
        st.html(
            f'<h3 class="info-card-title">{esc(T["week_summary_title"])}</h3>'
            f'<ul class="week-list">{rows}</ul>'
        )


def show_allergy_card(profile):
    """내 알레르기 카드: 등록한 식품을 빨간 알약으로 보여 준다."""
    with st.container(key="card_today_allergy"):
        if len(profile["allergies"]) == 0:
            body = f'<p class="muted">{esc(T["my_allergy_none"])}</p>'
        else:
            chips = ""

            for code in profile["allergies"]:
                chips += pill(f"{code}. {ALLERGENS[code]}", "red")

            body = f'<div class="chips">{chips}</div>'

        st.html(f'<h3 class="info-card-title">{esc(T["my_allergy_title"])}</h3>{body}')

        if st.button(T["my_allergy_edit"], key="allergy_edit"):
            show_settings()


def show_today():
    """오늘 화면"""
    profile = get_profile()
    today = today_kst()
    monday = monday_of(today)
    friday = monday + timedelta(days=4)

    show_hero(profile)

    with st.container(key="sec_page"):
        # 이번 주 급식과 학사일정을 한 번에 받아 오늘 카드와 미리 보기 카드가 함께 쓴다.
        try:
            meals = fetch_meals(profile["school"], monday, friday)
            events = fetch_schedule(profile["school"], monday, friday)
        except NeisError:
            st.error(T["err_network"])
            meals, events = [], []

        by_day = group_meals(meals)
        holidays = group_holidays(events)

        left, right = st.columns(2, gap="medium")

        with left:
            show_meal_card(profile, by_day.get(today, []), holidays.get(today, []))

        with right:
            show_week_card(profile, monday, by_day, holidays)
            show_allergy_card(profile)

        show_source()
