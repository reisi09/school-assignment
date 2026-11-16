# screen_intro.py
# 소개 화면: 앱이 무엇을 해 주는지 알리고, 기록하기나 체험하기로 보낸다.

import streamlit as st

from cases import CASE_SOURCES, REAL_CASES
from common import MENU_PLAY, MENU_RECORD, MENU_TODO, esc, go_to, show_case_row
from database import get_incidents
from stats import count_all_remaining
from texts import TEXT as T

# 소개 화면 맨 위에 보여 줄 실제 사례 세 건
FEATURED_CASES = ["할리스 멤버십", "빗썸", "Adobe"]


def show_intro():
    """소개 화면: 머리 구역, 사용 방법, 체험 안내, 큰 숫자, 해 주는 일과 하지 않는 일."""
    incidents = get_incidents()

    # 머리 구역: 큰 제목, 시작 버튼, 실제 사례 카드 세 장
    with st.container(key="sec_hero"):
        hero_left, hero_right = st.columns([7, 5], vertical_alignment="bottom")

        hero = (
            '<h1 class="hero-title">'
            f"<span>{esc(T['hero_line1'])}</span><span>{esc(T['hero_line2'])}</span></h1>"
            f'<p class="hero-lead">{esc(T["intro_hero_body"])}</p>'
        )

        if len(incidents) > 0:
            progress = T["intro_progress"].format(
                remaining=count_all_remaining(incidents),
                records=len(incidents),
            )
            hero += f'<p class="hero-progress">{esc(progress)}</p>'

        hero_left.html(hero)

        with hero_right:
            with st.container(
                key="hero_actions",
                horizontal=True,
                horizontal_alignment="right",
            ):
                st.button(
                    T["intro_example_button"],
                    on_click=go_to,
                    args=(MENU_RECORD, T["record_mode_case"]),
                )

                # 기록이 있으면 할 일 화면으로, 없으면 기록하기 화면으로 보낸다.
                if len(incidents) > 0:
                    st.button(
                        T["intro_progress_button"],
                        type="primary",
                        on_click=go_to,
                        args=(MENU_TODO,),
                    )
                else:
                    st.button(
                        T["intro_start_button"],
                        type="primary",
                        on_click=go_to,
                        args=(MENU_RECORD, T["record_mode_manual"]),
                    )

        featured = []

        for index, case in enumerate(REAL_CASES):
            if case["name"] in FEATURED_CASES:
                featured.append(index)

        show_case_row("hero", featured)

    # 사용 방법 세 단계
    steps = ""

    for number in (1, 2, 3):
        steps += (
            f'<div class="soft"><span class="step-number">{number}</span>'
            f"<h3>{esc(T[f'step{number}_title'])}</h3>"
            f"<p>{esc(T[f'step{number}_body'])}</p></div>"
        )

    with st.container(key="sec_steps"):
        st.html(
            f'<h2 class="title">{esc(T["steps_line1"])}<br>{esc(T["steps_line2"])}</h2>'
            f'<div class="steps">{steps}</div>'
        )

    # 체험하기 화면을 알리는 남색 구역
    with st.container(key="sec_play"):
        st.html(
            f'<h2 class="title">{esc(T["intro_play_title"])}</h2>'
            f'<p class="lead">{esc(T["intro_play_body"])}</p>'
        )
        st.button(T["intro_play_button"], type="primary", on_click=go_to, args=(MENU_PLAY,))

    # 왜 필요한지: 큰 숫자 세 개 (앞의 두 숫자는 연합뉴스 2026.11.1. 보도)
    stats = [
        ("25곳", T["stat1_label"]),
        ("534만 건", T["stat2_label"]),
        (f"{len(REAL_CASES)}{T['size_unit']}", T["stat3_label"]),
    ]
    cells = ""

    for value, label in stats:
        cells += f'<div class="stat"><b>{esc(value)}</b><span>{esc(label)}</span></div>'

    with st.container(key="sec_stats"):
        st.html(
            f'<h2 class="title">{esc(T["intro_why_title"])}</h2>'
            f'<p class="lead">{esc(T["intro_why_body"])}</p>'
            f'<div class="stats">{cells}</div>'
            f'<p class="source"><a href="{CASE_SOURCES["국내"]}" target="_blank">'
            f"{esc(T['intro_why_source_label'])}</a></p>"
        )

    # 해 주는 일과 하지 않는 일
    does = ""

    for line in T["intro_does"]:
        does += f"<li>{esc(line)}</li>"

    does_not = ""

    for line in T["intro_does_not"]:
        does_not += f"<li>{esc(line)}</li>"

    with st.container(key="sec_about"):
        st.html(
            '<div class="two">'
            f'<div class="soft"><h3>{esc(T["intro_does_title"])}</h3><ul>{does}</ul></div>'
            f'<div class="soft"><h3>{esc(T["intro_does_not_title"])}</h3><ul>{does_not}</ul></div>'
            "</div>"
        )
        st.warning(T["intro_shared_notice"])
