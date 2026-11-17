# screen_schedule.py
# 일정 화면: 학사일정(나이스 포털)과 우리 반 일정(학생이 등록)을 한 달씩 함께 본다.
# 우리 반 일정을 등록·지우기·찾기 하고, 수행평가가 한 주에 몰린 주를 알려 준다.
# 학사일정을 내 학년 것만 고르는 school_events_for()는 오늘 화면도 쓴다.

from datetime import date, timedelta

import streamlit as st

from common import date_short, dday_text, esc, get_profile, pill, show_page_head, show_source
from database import add_event, delete_event, get_events
from days import add_months, find_crowded_weeks, first_of_month, from_ymd, last_of_month, today_kst
from neis import NeisError, fetch_schedule
from texts import TEXT as T

# 수행평가가 이만큼 이상 한 주에 있으면 몰렸다고 본다.
CROWDED_MINIMUM = 3

# 몰린 주는 오늘부터 이만큼(일) 앞까지 찾는다.
CROWDED_DAYS = 90


def school_events_for(school, grade, start, end):
    """
    start~end 학사일정 중 내 학년 일정만 날짜 순서로 돌려준다.

    주말 일정(토요휴업일 등)은 매주 반복되어 뺀다. 날짜는 date로 바꿔 둔다.
    """
    events = []

    for event in fetch_schedule(school, start, end):
        day = from_ymd(event["date"])

        # weekday()가 5, 6이면 토요일, 일요일이다.
        if day.weekday() >= 5:
            continue

        # 학년 정보가 없으면 모든 학년 일정으로 본다.
        if len(event["grades"]) > 0 and grade not in event["grades"]:
            continue

        events.append({"date": day, "name": event["name"], "holiday": event["holiday"]})

    return events


def school_event_html(event):
    """학사일정 한 줄. 쉬는 날이면 표시를 붙이고, 앞으로 올 일정이면 남은 날을 붙인다."""
    tags = ""

    if event["holiday"]:
        tags += pill(T["holiday_tag"], "mint")

    if event["date"] >= today_kst():
        tags += pill(dday_text(event["date"]), "gray")

    return (
        f'<div class="event-row"><span class="event-date">{esc(date_short(event["date"]))}</span>'
        f'<b>{esc(event["name"])}</b><span class="event-tags">{tags}</span></div>'
    )


def class_event_html(event):
    """우리 반 일정 한 줄. 종류, 과목, 내용, 메모, 남은 날이 있다."""
    tone = "gray"

    # 첫 번째 종류(수행평가)는 빨갛게 둔다.
    if event["kind"] == T["event_kinds"][0]:
        tone = "red"

    tags = pill(event["kind"], tone)

    if event["due_date"] >= today_kst():
        tags += pill(dday_text(event["due_date"]), "gray")

    memo = ""

    if event["memo"] != "":
        memo = f'<span class="event-memo">{esc(event["memo"])}</span>'

    return (
        f'<div class="event-row"><span class="event-date">{esc(date_short(event["due_date"]))}</span>'
        f'<div><b>{esc(event["subject"])} · {esc(event["title"])}</b>{memo}</div>'
        f'<span class="event-tags">{tags}</span></div>'
    )


def remove_event(event):
    """지우기 버튼을 누르면 우리 반 일정 하나를 지운다."""
    delete_event(event["id"])
    st.toast(T["event_deleted"].format(title=event["title"]))


def move_month(count):
    """지난달·다음 달 버튼을 누르면 보고 있는 달을 옮긴다. 0이면 이번 달이다."""
    if count == 0:
        st.session_state["sch_month"] = first_of_month(today_kst())
    else:
        st.session_state["sch_month"] = add_months(st.session_state["sch_month"], count)


def show_month_nav():
    """지난달·이번 달·다음 달 버튼과 지금 보는 달을 보여 주고, 그달 1일을 돌려준다."""
    if "sch_month" not in st.session_state:
        st.session_state["sch_month"] = first_of_month(today_kst())

    month = st.session_state["sch_month"]

    with st.container(horizontal=True, vertical_alignment="center", key="sch_nav"):
        st.button(T["month_prev"], key="sch_prev", on_click=move_month, args=(-1,))
        st.button(T["month_this"], key="sch_this", on_click=move_month, args=(0,))
        st.button(T["month_next"], key="sch_next", on_click=move_month, args=(1,))
        st.html(
            f'<span class="nav-label">'
            f"{esc(T['month_label'].format(year=month.year, month=month.month))}</span>"
        )

    return month


def show_add_form(profile):
    """우리 반 일정을 등록하는 칸"""
    school_code = profile["school"]["school_code"]

    st.html(f'<h2 class="group-title" id="add-event">{esc(T["event_add_title"])}</h2>')

    with st.container(key="card_event_form"):
        with st.form("event_form", clear_on_submit=True):
            with st.container(horizontal=True):
                kind = st.selectbox(T["field_kind"], T["event_kinds"])
                due = st.date_input(T["field_due"], value=today_kst(), format="YYYY-MM-DD")

            subject = st.text_input(T["field_subject"], placeholder=T["subject_placeholder"])
            title = st.text_input(T["field_event_title"], placeholder=T["event_title_placeholder"])
            memo = st.text_input(T["field_memo"])
            submitted = st.form_submit_button(T["event_submit"], type="primary")

        if submitted:
            status = add_event(
                school_code,
                profile["grade"],
                profile["class_nm"],
                kind,
                subject,
                title,
                due,
                memo,
            )

            if status == "NO_SUBJECT":
                st.warning(T["err_event_subject"])
            elif status == "NO_TITLE":
                st.warning(T["err_event_title"])
            else:
                st.toast(T["event_saved"].format(title=title.strip()))

        st.caption(T["shared_notice"])


def show_crowded(profile):
    """오늘부터 90일 안에 수행평가가 한 주에 3개 이상 몰린 주를 보여 준다."""
    today = today_kst()
    events = get_events(
        profile["school"]["school_code"],
        profile["grade"],
        profile["class_nm"],
        today,
        today + timedelta(days=CROWDED_DAYS),
    )
    crowded = find_crowded_weeks(events, T["event_kinds"][0], CROWDED_MINIMUM)

    rows = ""

    for monday, count in crowded:
        rows += f'<li>{esc(T["crowded_line"].format(start=date_short(monday), count=count))}</li>'

    if rows == "":
        body = f'<p class="muted">{esc(T["crowded_none"])}</p>'
        tone = ""
    else:
        body = f'<ul class="crowded">{rows}</ul>'
        tone = "is-alert"

    st.html(f'<div class="info-card {tone}"><h3 class="info-card-title">{esc(T["crowded_title"])}</h3>{body}</div>')


def show_search(profile):
    """우리 반 일정을 과목·내용·메모의 낱말로 찾는다."""
    with st.form("event_search"):
        with st.container(horizontal=True, vertical_alignment="bottom"):
            keyword = st.text_input(
                T["event_search_label"],
                placeholder=T["event_search_placeholder"],
                width=320,
            )
            submitted = st.form_submit_button(T["event_search_button"])

    if not submitted or keyword.strip() == "":
        return

    events = get_events(
        profile["school"]["school_code"],
        profile["grade"],
        profile["class_nm"],
        date(2000, 1, 1),
        date(2100, 12, 31),
        keyword,
    )

    if len(events) == 0:
        st.html(f'<div class="empty">{esc(T["event_search_none"])}</div>')
        return

    rows = ""

    for event in events:
        rows += class_event_html(event)

    st.html(f'<div class="soft">{rows}</div>')


def show_schedule():
    """일정 화면"""
    profile = get_profile()

    with st.container(key="sec_page"):
        show_page_head(T["schedule_title"], T["schedule_intro"])
        month = show_month_nav()
        last = last_of_month(month)

        left, right = st.columns(2, gap="large")

        # 왼쪽: 학사일정
        with left:
            try:
                events = school_events_for(profile["school"], profile["grade"], month, last)
            except NeisError:
                st.error(T["err_network"])
                events = []

            rows = ""

            for event in events:
                rows += school_event_html(event)

            if rows == "":
                rows = f'<p class="muted">{esc(T["school_events_none"])}</p>'

            st.html(f'<div class="info-card"><h3 class="info-card-title">{esc(T["school_events_title"])}</h3>{rows}</div>')

        # 오른쪽: 우리 반 일정. 줄마다 지우기 버튼이 있다.
        with right:
            with st.container(key="card_class_events"):
                st.html(f'<h3 class="info-card-title">{esc(T["class_events_title"])}</h3>')

                class_events = get_events(
                    profile["school"]["school_code"],
                    profile["grade"],
                    profile["class_nm"],
                    month,
                    last,
                )

                if len(class_events) == 0:
                    st.html(f'<p class="muted">{esc(T["class_events_none"])}</p>')

                for event in class_events:
                    with st.container(horizontal=True, vertical_alignment="center", key=f"ev_{event['id']}"):
                        st.html(class_event_html(event), width="stretch")
                        st.button(
                            T["event_delete"],
                            key=f"del_{event['id']}",
                            on_click=remove_event,
                            args=(event,),
                        )

        left, right = st.columns([7, 5], gap="large")

        with left:
            show_add_form(profile)

        with right:
            show_crowded(profile)
            show_search(profile)

        show_source()
