# screen_meal.py
# 급식 화면: 한 주 급식, 메뉴 찾기, 급식 평가와 인기 메뉴
# 메뉴를 HTML로 만드는 dishes_html()은 오늘 화면도 쓴다.

from datetime import timedelta

import streamlit as st

from common import date_short, esc, get_profile, pill, show_page_head, show_source, show_week_nav
from database import add_review, get_recent_reviews, get_top_dishes
from days import from_ymd, today_kst
from foods import ALLERGENS, find_my_allergens, parse_dishes, parse_kcal, parse_pairs
from neis import NeisError, fetch_meals, fetch_schedule
from texts import TEXT as T

# 메뉴 찾기는 오늘 앞뒤로 이만큼(일)의 급식에서 찾는다.
SEARCH_DAYS = 28


def dishes_html(dishes, my_codes):
    """
    메뉴 목록을 HTML로 만든다. 내 알레르기 식품이 든 메뉴는 빨갛게 표시한다.

    dishes는 foods.parse_dishes()가 돌려준 (이름, 알레르기 번호 목록) 목록이다.
    """
    items = ""

    for name, codes in dishes:
        mine = find_my_allergens(codes, my_codes)

        # 알레르기 번호는 작은 회색 글자로 붙인다. 예: 5·6·10
        numbers = ""

        if len(codes) > 0:
            parts = []

            for code in codes:
                parts.append(str(code))

            numbers = f'<span class="codes">{"·".join(parts)}</span>'

        if len(mine) > 0:
            tag = pill(T["my_allergy_tag"] + " · " + ", ".join(mine), "red")
            items += f'<li class="dish is-risky"><span>{esc(name)}</span>{numbers}{tag}</li>'
        else:
            items += f'<li class="dish"><span>{esc(name)}</span>{numbers}</li>'

    return f'<ul class="dishes">{items}</ul>'


def pairs_html(title, text):
    """영양 정보나 원산지를 접는 칸(details)으로 만든다."""
    rows = ""

    for name, value in parse_pairs(text):
        rows += f'<div class="spec"><span>{esc(name)}</span><strong>{esc(value)}</strong></div>'

    if rows == "":
        return ""

    return f'<details class="more"><summary>{esc(title)}</summary>{rows}</details>'


def day_card(day, meals, holidays, my_codes):
    """하루 급식 카드를 HTML로 만든다. meals는 그날 급식 목록(끼니별)이다."""
    head = f'<div class="day-head"><b>{esc(date_short(day))}</b>'

    if day == today_kst():
        head += pill(T["dday_today"], "mint")

    head += "</div>"

    if len(meals) == 0:
        # 급식이 없는 날: 학사일정에 쉬는 날 이름이 있으면 함께 보여 준다.
        reason = ""

        if day in holidays:
            reason = f'<p class="muted">{esc(", ".join(holidays[day]))}</p>'

        # 오늘 뒤의 평일인데 자료가 없으면 학교가 아직 올리지 않은 것이다.
        message = T["meal_none_day"]

        if day > today_kst() and day not in holidays:
            message = T["meal_not_yet"]

        return f'<div class="day-card is-empty">{head}<p class="empty-line">{esc(message)}</p>{reason}</div>'

    body = ""

    for meal in meals:
        body += f'<p class="meal-name">{esc(meal["meal"])}</p>'
        body += dishes_html(parse_dishes(meal["dishes"]), my_codes)
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


def show_week(profile):
    """한 주(월~금) 급식을 카드 다섯 장으로 보여 준다."""
    monday = show_week_nav("meal_week")
    friday = monday + timedelta(days=4)

    try:
        meals = fetch_meals(profile["school"], monday, friday)
        events = fetch_schedule(profile["school"], monday, friday)
    except NeisError:
        st.error(T["err_network"])
        return

    # 날짜마다 급식과 쉬는 날 이름을 모은다.
    meals_by_day = {}

    for meal in meals:
        meals_by_day.setdefault(from_ymd(meal["date"]), []).append(meal)

    holidays = {}

    for event in events:
        if event["holiday"]:
            holidays.setdefault(from_ymd(event["date"]), []).append(event["name"])

    columns = st.columns(5, gap="small")

    for number, column in enumerate(columns):
        day = monday + timedelta(days=number)
        column.html(day_card(day, meals_by_day.get(day, []), holidays, profile["allergies"]))

    st.html(allergy_legend_html(profile["allergies"]))


def show_search(profile):
    """메뉴 이름으로 오늘 앞뒤 4주의 급식을 찾는다."""
    st.html(f'<h2 class="group-title">{esc(T["meal_search_title"])}</h2>')

    with st.form("meal_search"):
        with st.container(horizontal=True, vertical_alignment="bottom"):
            keyword = st.text_input(
                T["meal_search_label"],
                placeholder=T["meal_search_placeholder"],
                width=320,
            )
            submitted = st.form_submit_button(T["meal_search_button"])

    st.caption(T["meal_search_range"])

    if not submitted or keyword.strip() == "":
        return

    today = today_kst()

    try:
        meals = fetch_meals(
            profile["school"],
            today - timedelta(days=SEARCH_DAYS),
            today + timedelta(days=SEARCH_DAYS),
        )
    except NeisError:
        st.error(T["err_network"])
        return

    # 띄어쓰기를 빼고 비교해서 "돈 까스"로 찾아도 "돈까스"가 나오게 한다.
    word = keyword.replace(" ", "")
    rows = ""
    count = 0

    for meal in meals:
        for name, codes in parse_dishes(meal["dishes"]):
            if word in name.replace(" ", ""):
                count += 1
                rows += (
                    f'<div class="spec"><span>{esc(date_short(from_ymd(meal["date"])))}</span>'
                    f"<strong>{dishes_html([(name, codes)], profile['allergies'])}</strong></div>"
                )

    if count == 0:
        st.html(f'<div class="empty">{esc(T["meal_search_none"])}</div>')
    else:
        st.html(
            f'<p class="summary">{esc(T["meal_search_result"].format(count=count))}</p>'
            f'<div class="soft">{rows}</div>'
        )


def show_reviews(profile):
    """급식 평가를 남기고, 인기 메뉴 순위와 최근 한줄평을 본다."""
    school_code = profile["school"]["school_code"]
    today = today_kst()

    st.html(
        f'<h2 class="group-title">{esc(T["review_title"])}</h2>'
        f'<p class="lead small">{esc(T["review_intro"])}</p>'
    )

    left, right = st.columns([6, 5], gap="large")

    with left:
        try:
            meals = fetch_meals(profile["school"], today, today)
        except NeisError:
            st.error(T["err_network"])
            meals = []

        dish_names = []

        for meal in meals:
            for name, codes in parse_dishes(meal["dishes"]):
                dish_names.append(name)

        if len(dish_names) == 0:
            st.html(f'<div class="empty">{esc(T["review_no_meal"])}</div>')
        else:
            with st.container(key="card_review"):
                with st.form("review_form", clear_on_submit=True):
                    dish = st.selectbox(
                        T["review_dish"],
                        dish_names,
                        index=None,
                        placeholder=T["review_dish_placeholder"],
                    )
                    # 별점 칸에는 이름이 없어서 위에 작은 글자로 이름을 붙인다.
                    st.caption(T["review_stars"])
                    stars = st.feedback("stars")
                    comment = st.text_input(
                        T["review_comment"],
                        placeholder=T["review_comment_placeholder"],
                        max_chars=60,
                    )
                    submitted = st.form_submit_button(T["review_submit"], type="primary")

                if submitted:
                    # st.feedback은 별 다섯 개를 0~4로 돌려준다. 1을 더해 1~5점으로 저장한다.
                    score = None

                    if stars is not None:
                        score = stars + 1

                    status = add_review(school_code, today, dish, score, comment)

                    if status == "NO_DISH":
                        st.warning(T["err_review_dish"])
                    elif status == "NO_STARS":
                        st.warning(T["err_review_stars"])
                    else:
                        st.toast(T["review_saved"].format(dish=dish))

            st.caption(T["shared_notice"])

    with right:
        top = get_top_dishes(school_code)
        rows = ""

        for rank, (dish, average, count) in enumerate(top, start=1):
            rows += (
                f'<li><span class="rank">{rank}</span><div><b>{esc(dish)}</b>'
                f'<span>{esc(T["top_line"].format(avg=average, count=count))}</span></div></li>'
            )

        if rows == "":
            body = f'<p class="muted">{esc(T["top_none"])}</p>'
        else:
            body = f'<ol class="ranking">{rows}</ol>'

        recent = ""

        for review in get_recent_reviews(school_code):
            recent += (
                f'<li><b>{esc(review["dish"])}</b> {"★" * review["stars"]}'
                f'<span>{esc(review["comment"])}</span></li>'
            )

        if recent != "":
            body += f'<h3 class="info-card-title sub">{esc(T["review_recent_title"])}</h3><ul class="recent">{recent}</ul>'

        st.html(f'<div class="info-card"><h3 class="info-card-title">{esc(T["top_title"])}</h3>{body}</div>')


def show_meal():
    """급식 화면"""
    profile = get_profile()

    with st.container(key="sec_page"):
        show_page_head(T["meal_title"], T["meal_intro"])
        show_week(profile)
        show_search(profile)
        show_reviews(profile)
        show_source()
