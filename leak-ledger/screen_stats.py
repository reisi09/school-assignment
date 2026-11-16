# screen_stats.py
# 통계 화면: 내 기록을 큰 숫자와 막대그래프로 보여 준다.

import streamlit as st

from common import bar_rows, esc, repeat_box, show_empty, show_page_head
from database import get_incidents, get_quiz_summary
from play import QUIZ
from stats import count_grades, count_items, get_done_percent, sum_remaining_scores
from texts import TEXT as T


def show_stats():
    """통계 화면: 큰 숫자 세 개, 막대그래프 두 개, 반복 유출, 사칭 문자 가려내기 결과."""
    incidents = get_incidents()

    with st.container(key="sec_page"):
        show_page_head(T["stats_title"], T["stats_intro"])

        if len(incidents) == 0:
            show_empty(T["stats_empty"])
            return

        # 큰 숫자 세 개: 기록 수, 남은 위험 점수 합계, 끝낸 할 일의 비율
        numbers = [
            (f"{len(incidents)}{T['size_unit']}", T["stats_records_label"]),
            (f"{sum_remaining_scores(incidents)}{T['score_unit']}", T["stats_risk_label"]),
            (f"{get_done_percent(incidents)}%", T["stats_done_label"]),
        ]
        cells = ""

        for value, label in numbers:
            cells += f'<div class="stat"><b>{esc(value)}</b><span>{esc(label)}</span></div>'

        st.html(f'<div class="stats">{cells}</div>')

        # 막대그래프 1: 위험 등급마다 기록이 몇 건인지
        grades = count_grades(incidents)
        grade_rows = [
            (T["risk_high"], grades["높음"], "red"),
            (T["risk_mid"], grades["보통"], "yellow"),
            (T["risk_low"], grades["낮음"], "navy"),
        ]

        # 막대그래프 2: 정보마다 몇 번 유출됐는지 (많은 순)
        item_rows = []

        for item, count in count_items(incidents):
            item_rows.append((item, count, "mint"))

        st.html(
            '<div class="two">'
            f'<div class="soft"><h3>{esc(T["stats_grade_title"])}</h3>{bar_rows(grade_rows)}</div>'
            f'<div class="soft"><h3>{esc(T["stats_items_title"])}</h3>{bar_rows(item_rows)}</div>'
            "</div>"
        )

        # 같은 정보가 여러 곳에서 유출됐으면 알려 준다.
        warning = repeat_box(incidents)

        if warning != "":
            st.html(warning)

        # 사칭 문자 가려내기 결과
        best, count = get_quiz_summary()

        if count == 0:
            quiz_line = T["stats_quiz_none"]
        else:
            quiz_line = T["stats_quiz_line"].format(best=best, total=len(QUIZ), count=count)

        st.html(
            f'<div class="soft"><h3>{esc(T["stats_quiz_title"])}</h3>'
            f"<p>{esc(quiz_line)}</p></div>"
        )
