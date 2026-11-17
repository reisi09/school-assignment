# screen_meal.py
# 급식표 화면: 한 주(월~금) 급식을 날짜별 카드로 보여 준다.
# 메뉴를 HTML로 만드는 dishes_html()과 급식을 날짜별로 묶는 함수는 오늘 화면과 찾기 화면도 쓴다.

from datetime import timedelta

import streamlit as st

from common import date_short, esc, get_profile, my_words, pill, show_page_head, show_source, show_week_nav
from days import from_ymd, school_days, today_kst
from foods import ALLERGENS, find_my_allergens, find_watch_words, parse_dishes, parse_kcal, parse_pairs
from neis import NeisError, fetch_meals, fetch_schedule
from texts import TEXT as T


def group_meals(meals):
    """급식 목록을 날짜별로 묶는다. {날짜: 그날 급식 목록}을 돌려준다."""
    by_day = {}

    for meal in meals:
        by_day.setdefault(from_ymd(meal["date"]), []).append(meal)

    return by_day


def group_holidays(events):
    """학사일정에서 쉬는 날의 이름을 날짜별로 묶는다. {날짜: 이름 목록}을 돌려준다."""
    holidays = {}

    for event in events:
        if event["holiday"]:
            holidays.setdefault(from_ymd(event["date"]), []).append(event["name"])

    return holidays


def empty_message(day, holidays):
    """급식이 없는 날에 보여 줄 말. 오늘 뒤의 평일인데 쉬는 날도 아니면 학교가 아직 올리지 않은 것이다."""
    if day > today_kst() and day not in holidays:
        return T["meal_not_yet"]

    return T["meal_none_day"]


def dishes_html(dishes, my_codes, words):
    """
    메뉴 목록을 HTML로 만든다. 내 알레르기 식품이 든 메뉴는 빨갛게, 주의 낱말이 든 메뉴는 남색으로 표시한다.

    dishes는 foods.parse_dishes()가 돌려준 (이름, 알레르기 번호 목록) 목록이다.
    words는 내 주의 낱말 목록이다.
    """
    items = ""

    for name, codes in dishes:
        mine = find_my_allergens(codes, my_codes)
        watched = find_watch_words(name, words)

        # 알레르기 번호는 작은 회색 글자로 붙인다. 예: 5·6·10
        numbers = ""

        if len(codes) > 0:
            parts = []

            for code in codes:
                parts.append(str(code))

            numbers = f'<span class="codes">{"·".join(parts)}</span>'

        tags = ""
        classes = "dish"

        if len(mine) > 0:
            tags += pill(T["my_allergy_tag"] + " · " + ", ".join(mine), "red")
            classes += " is-risky"

        if len(watched) > 0:
            tags += pill(T["watch_tag"] + " · " + ", ".join(watched), "navy")
            classes += " is-watched"

        items += f'<li class="{classes}"><span>{esc(name)}</span>{numbers}{tags}</li>'

    return f'<ul class="dishes">{items}</ul>'


def pairs_html(title, text):
    """영양 정보나 원산지를 접는 칸(details)으로 만든다."""
    rows = ""

    for name, value in parse_pairs(text):
        rows += f'<div class="spec"><span>{esc(name)}</span><strong>{esc(value)}</strong></div>'

    if rows == "":
        return ""

    return f'<details class="more"><summary>{esc(title)}</summary>{rows}</details>'


def day_card(day, meals, holidays, my_codes, words):
    """하루 급식 카드를 HTML로 만든다. meals는 그날 급식 목록(끼니별)이다."""
    head = f'<div class="day-head"><b>{esc(date_short(day))}</b>'

    if day == today_kst():
        head += pill(T["today_mark"], "mint")

    head += "</div>"

    if len(meals) == 0:
        # 급식이 없는 날: 학사일정에 쉬는 날 이름이 있으면 함께 보여 준다.
        reason = ""

        if day in holidays:
            reason = f'<p class="muted">{esc(", ".join(holidays[day]))}</p>'

        message = empty_message(day, holidays)

        return f'<div class="day-card is-empty">{head}<p class="empty-line">{esc(message)}</p>{reason}</div>'

    body = ""

    for meal in meals:
        body += f'<p class="meal-name">{esc(meal["meal"])}</p>'
        body += dishes_html(parse_dishes(meal["dishes"]), my_codes, words)
        body += (
            f'<p class="meal-meta"><b>{parse_kcal(meal["kcal"]):,.0f}</b> {esc(T["kcal_unit"])}'
            f' · {esc(T["meal_headcount"].format(count=f"{float(meal["headcount"] or 0):,.0f}"))}</p>'
        )
        body += pairs_html(T["meal_nutrition_title"], meal["nutrition"])
        body += pairs_html(T["meal_origin_title"], meal["origin"])

    today_class = ""

    if day == today_kst():
        today_class = " is-today"

    return f'<div class="day-card{today_class}">{head}{body}</div>'


def allergy_legend_html(my_codes):
    """알레르기 번호표를 접는 칸으로 만든다. 내 알레르기는 빨갛게 표시한다."""
    items = ""

    for code, name in ALLERGENS.items():
        mine = ""

        if code in my_codes:
            mine = ' class="is-mine"'

        items += f"<li{mine}><b>{code}</b>{esc(name)}</li>"

    return (
        f'<details class="more legend"><summary>{esc(T["allergy_legend_title"])}</summary>'
        f'<ul class="legend-list">{items}</ul></details>'
    )


def show_meal():
    """급식표 화면: 한 주(월~금) 급식을 카드 다섯 장으로 보여 준다."""
    profile = get_profile()

    with st.container(key="sec_page"):
        show_page_head(T["week_title"], T["week_intro"])
        monday = show_week_nav("meal_week")
        friday = monday + timedelta(days=4)

        try:
            meals = fetch_meals(profile["school"], monday, friday)
            events = fetch_schedule(profile["school"], monday, friday)
        except NeisError:
            st.error(T["err_network"])
            meals, events = [], []

        by_day = group_meals(meals)
        holidays = group_holidays(events)

        # 월~금 날짜와 칸 다섯 개를 짝지어 하나씩 채운다.
        columns = st.columns(5, gap="small")
        words = my_words(profile)

        for day, column in zip(school_days(monday), columns):
            column.html(day_card(day, by_day.get(day, []), holidays, profile["allergies"], words))

        st.html(allergy_legend_html(profile["allergies"]))
        show_source()
