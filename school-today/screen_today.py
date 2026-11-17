# screen_today.py
# 오늘 화면: 오늘 급식, 오늘 시간표, 다가오는 일정, 이번 주 우리 반 수행평가를 한 화면에 모은다.

from datetime import timedelta

import streamlit as st

from common import (
    MENU_MEAL,
    MENU_SCHEDULE,
    MENU_TIMETABLE,
    date_long,
    date_short,
    dday_text,
    esc,
    get_profile,
    go_to,
    has_profile,
    show_source,
)
from database import get_events
from days import find_crowded_weeks, monday_of, today_kst
from foods import count_risky_dishes, parse_dishes, parse_kcal
from neis import NeisError, fetch_meals, fetch_timetable
from screen_meal import dishes_html
from screen_schedule import CROWDED_MINIMUM, class_event_html, school_events_for
from screen_settings import show_settings
from texts import TEXT as T

# 다가오는 일정은 오늘부터 이만큼(일) 앞까지 보여 준다.
UPCOMING_DAYS = 28

# 다가오는 일정은 이만큼까지만 보여 준다.
UPCOMING_COUNT = 6


def show_hero(profile):
    """맨 위: 오늘 날짜와 지금 보는 학교·반. 내 설정이 없으면 설정을 권한다."""
    profile_line = T["who_line"].format(
        school=profile["school"]["name"],
        grade=profile["grade"],
        class_nm=profile["class_nm"],
    )

    with st.container(key="sec_hero"):
        st.html(
            f'<p class="hero-who">{esc(profile_line)}</p>'
            f'<h1 class="hero-title">{esc(date_long(today_kst()))}</h1>'
        )

        if not has_profile():
            with st.container(key="card_setup"):
                st.html(
                    f'<h2 class="setup-title">{esc(T["today_setup_title"])}</h2>'
                    f'<p class="setup-body">{esc(T["today_setup_body"])}</p>'
                )

                if st.button(T["today_setup_button"], type="primary", key="setup_open"):
                    show_settings()


def show_meal_card(profile, today):
    """오늘 급식 카드. 내 알레르기 식품이 든 메뉴 수를 맨 위에 알려 준다."""
    with st.container(key="card_today_meal"):
        try:
            meals = fetch_meals(profile["school"], today, today)
        except NeisError:
            st.error(T["err_network"])
            meals = []

        body = ""

        if len(meals) == 0:
            body = f'<p class="muted">{esc(T["today_meal_none"])}</p>'
        else:
            # 알레르기 알림: 등록하지 않았으면 등록을 권한다.
            dishes = []

            for meal in meals:
                dishes += parse_dishes(meal["dishes"])

            risky = count_risky_dishes(dishes, profile["allergies"])

            if len(profile["allergies"]) == 0:
                body += f'<p class="alert-line">{esc(T["today_allergy_unset"])}</p>'
            elif risky > 0:
                body += f'<p class="alert-line is-red">{esc(T["today_allergy_warn"].format(count=risky))}</p>'
            else:
                body += f'<p class="alert-line is-mint">{esc(T["today_allergy_safe"])}</p>'

            for meal in meals:
                body += dishes_html(parse_dishes(meal["dishes"]), profile["allergies"])
                body += (
                    f'<p class="meal-meta"><b>{parse_kcal(meal["kcal"]):,.0f}</b> '
                    f'{esc(T["kcal_unit"])} · {esc(meal["meal"])}</p>'
                )

        st.html(f'<h3 class="info-card-title">{esc(T["today_meal_title"])}</h3>{body}')
        st.button(T["today_more_meal"], key="more_meal", on_click=go_to, args=(MENU_MEAL,))


def show_timetable_card(profile, today):
    """오늘 시간표 카드. 교시와 과목을 차례로 보여 준다."""
    with st.container(key="card_today_timetable"):
        try:
            lessons = fetch_timetable(
                profile["school"],
                profile["grade"],
                profile["class_nm"],
                today,
                today,
            )
        except NeisError:
            st.error(T["err_network"])
            lessons = []

        if len(lessons) == 0:
            body = f'<p class="muted">{esc(T["today_timetable_none"])}</p>'
        else:
            rows = ""

            for lesson in lessons:
                rows += (
                    f'<li><span class="period">{esc(T["period_label"].format(n=lesson["period"]))}</span>'
                    f"<b>{esc(lesson['subject'])}</b></li>"
                )

            body = f'<ol class="lessons">{rows}</ol>'

        st.html(f'<h3 class="info-card-title">{esc(T["today_timetable_title"])}</h3>{body}')
        st.button(T["today_more_timetable"], key="more_timetable", on_click=go_to, args=(MENU_TIMETABLE,))


def show_upcoming_card(profile, today):
    """다가오는 일정 카드: 4주 안의 학사일정과 우리 반 일정을 날짜 순서로 섞어 보여 준다."""
    end = today + timedelta(days=UPCOMING_DAYS)

    with st.container(key="card_today_upcoming"):
        items = []

        try:
            for event in school_events_for(profile["school"], profile["grade"], today, end):
                items.append((event["date"], event["name"], "navy"))
        except NeisError:
            st.error(T["err_network"])

        events = get_events(
            profile["school"]["school_code"],
            profile["grade"],
            profile["class_nm"],
            today,
            end,
        )

        for event in events:
            items.append((event["due_date"], event["subject"] + " · " + event["title"], "red"))

        # (날짜, 이름, 색) 묶음은 날짜 순서로 정렬된다.
        items.sort()

        rows = ""

        for day, name, tone in items[:UPCOMING_COUNT]:
            rows += (
                f'<li><span class="dday dday-{tone}">{esc(dday_text(day))}</span>'
                f"<div><b>{esc(name)}</b><span>{esc(date_short(day))}</span></div></li>"
            )

        if rows == "":
            body = f'<p class="muted">{esc(T["today_upcoming_none"])}</p>'
        else:
            body = f'<ul class="upcoming">{rows}</ul>'

        st.html(f'<h3 class="info-card-title">{esc(T["today_upcoming_title"])}</h3>{body}')
        st.button(T["today_more_schedule"], key="more_schedule", on_click=go_to, args=(MENU_SCHEDULE,))


def show_week_card(profile, today):
    """이번 주 우리 반 수행평가 카드. 3개 이상 몰리면 빨갛게 경고한다."""
    monday = monday_of(today)
    sunday = monday + timedelta(days=6)
    assessment = T["event_kinds"][0]

    with st.container(key="card_today_week"):
        events = get_events(
            profile["school"]["school_code"],
            profile["grade"],
            profile["class_nm"],
            monday,
            sunday,
        )

        assessments = []

        for event in events:
            if event["kind"] == assessment:
                assessments.append(event)

        body = ""

        if len(find_crowded_weeks(assessments, assessment, CROWDED_MINIMUM)) > 0:
            body += f'<p class="alert-line is-red">{esc(T["today_crowded"].format(count=len(assessments)))}</p>'

        if len(assessments) == 0:
            body += f'<p class="muted">{esc(T["today_week_none"])}</p>'
        else:
            for event in assessments:
                body += class_event_html(event)

        st.html(f'<h3 class="info-card-title">{esc(T["today_week_title"])}</h3>{body}')
        st.button(T["today_add_event"], key="add_event", on_click=go_to, args=(MENU_SCHEDULE,))


def show_today():
    """오늘 화면"""
    profile = get_profile()
    today = today_kst()

    show_hero(profile)

    with st.container(key="sec_page"):
        left, right = st.columns(2, gap="medium")

        with left:
            show_meal_card(profile, today)
            show_upcoming_card(profile, today)

        with right:
            show_timetable_card(profile, today)
            show_week_card(profile, today)

        show_source()
