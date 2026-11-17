# screen_timetable.py
# 시간표 화면: 학년과 반을 골라 한 주(월~금) 시간표를 표로 본다.

from datetime import timedelta

import streamlit as st

from common import date_short, esc, get_profile, show_page_head, show_source, show_week_nav, weekday_name
from days import from_ymd, today_kst
from neis import NeisError, count_classes, fetch_schedule, fetch_timetable, has_key
from screen_settings import GRADE_COUNTS
from texts import TEXT as T


def timetable_html(monday, lessons, holidays):
    """
    한 주 시간표를 표(table)로 만든다.

    lessons는 neis.fetch_timetable()이 돌려준 (날짜, 교시, 과목) 목록이다.
    holidays는 날짜별 쉬는 날 이름이다. 오늘 칸은 민트색으로 표시한다.
    """
    days = []

    for number in range(5):
        days.append(monday + timedelta(days=number))

    # (날짜, 교시)로 과목을 찾을 수 있게 담는다.
    subjects = {}
    last_period = 0

    for lesson in lessons:
        subjects[(from_ymd(lesson["date"]), lesson["period"])] = lesson["subject"]
        last_period = max(last_period, lesson["period"])

    today = today_kst()
    head = "<th></th>"

    for day in days:
        mark = ""

        if day == today:
            mark = f'<span class="today-mark">{esc(T["today_mark"])}</span>'

        head += f"<th><b>{esc(weekday_name(day))}</b><span>{esc(date_short(day))}</span>{mark}</th>"

    body = ""

    for period in range(1, last_period + 1):
        body += f"<tr><th>{esc(T['period_label'].format(n=period))}</th>"

        for day in days:
            classes = []

            if day == today:
                classes.append("is-today")

            if day in holidays:
                classes.append("is-holiday")

            # 쉬는 날은 첫 칸에만 쉬는 날 이름을 적는다.
            text = subjects.get((day, period), "")

            if day in holidays and period == 1 and text == "":
                text = ", ".join(holidays[day])

            body += f'<td class="{" ".join(classes)}">{esc(text)}</td>'

        body += "</tr>"

    return f'<div class="table-wrap"><table class="timetable"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def show_timetable():
    """시간표 화면"""
    profile = get_profile()
    school = profile["school"]

    with st.container(key="sec_page"):
        show_page_head(T["timetable_title"], T["timetable_intro"])

        # 학년과 반은 처음에 내 설정 값으로 정한다.
        if "tt_grade" not in st.session_state:
            st.session_state["tt_grade"] = profile["grade"]
            st.session_state["tt_class"] = profile["class_nm"]

        grade_count = GRADE_COUNTS.get(school["kind"], 3)

        with st.container(horizontal=True, vertical_alignment="bottom", key="tt_pick"):
            grade = st.selectbox(T["field_grade"], list(range(1, grade_count + 1)), key="tt_grade", width=120)

            try:
                class_count = count_classes(school, today_kst().year, grade)
            except NeisError:
                class_count = 0

            if class_count == 0:
                class_count = 15

            # 반 수가 줄어 지금 고른 반이 없으면 1반으로 돌린다.
            if st.session_state["tt_class"] > class_count:
                st.session_state["tt_class"] = 1

            class_nm = st.selectbox(T["field_class"], list(range(1, class_count + 1)), key="tt_class", width=120)

        monday = show_week_nav("tt_week")
        friday = monday + timedelta(days=4)

        try:
            lessons = fetch_timetable(school, grade, class_nm, monday, friday)
            events = fetch_schedule(school, monday, friday)
        except NeisError:
            st.error(T["err_network"])
            return

        holidays = {}

        for event in events:
            if event["holiday"]:
                holidays.setdefault(from_ymd(event["date"]), []).append(event["name"])

        if len(lessons) == 0:
            st.html(f'<div class="empty">{esc(T["timetable_none"])}</div>')
        else:
            st.html(timetable_html(monday, lessons, holidays))

        if not has_key():
            st.info(T["notice_no_key"])

        show_source()
