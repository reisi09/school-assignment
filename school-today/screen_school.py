# screen_school.py
# 학교 화면: 학교 기본 정보, 학년별 학급 수, 알레르기 번호표, 앱과 자료 안내

import streamlit as st

from common import esc, get_profile, show_page_head, show_source, spec_row
from days import today_kst
from foods import ALLERGENS
from neis import NeisError, count_classes, fetch_school_info
from screen_settings import GRADE_COUNTS
from texts import TEXT as T


def show_school():
    """학교 화면"""
    profile = get_profile()
    school = profile["school"]

    with st.container(key="sec_page"):
        show_page_head(T["school_title"], school["name"])

        try:
            info = fetch_school_info(school)
        except NeisError:
            st.error(T["err_network"])
            return

        left, right = st.columns(2, gap="large")

        with left:
            rows = ""

            if info is not None:
                homepage = ""

                if info["homepage"]:
                    homepage = f'<a href="{esc(info["homepage"])}" target="_blank">{esc(info["homepage"])}</a>'

                rows += spec_row(T["school_address"], esc(info["address"]))
                rows += spec_row(T["school_phone"], esc(info["phone"]))
                rows += spec_row(T["school_homepage"], homepage)
                rows += spec_row(T["school_kind"], esc(info["kind"]))
                rows += spec_row(T["school_gender"], esc(info["gender"]))
                rows += spec_row(T["school_found"], esc(info["found"]))

            # 학년마다 반 수를 센다.
            classes = ""

            for grade in range(1, GRADE_COUNTS.get(school["kind"], 3) + 1):
                try:
                    count = count_classes(school, today_kst().year, grade)
                except NeisError:
                    count = 0

                classes += f"<li>{esc(T['classes_line'].format(grade=grade, count=count))}</li>"

            st.html(
                f'<div class="info-card"><h3 class="info-card-title">{esc(info["name"] if info else school["name"])}</h3>{rows}</div>'
                f'<div class="info-card"><h3 class="info-card-title">{esc(T["classes_title"])}</h3>'
                f'<ul class="plain">{classes}</ul></div>'
            )

        with right:
            items = ""

            for code, name in ALLERGENS.items():
                mine = ""

                if code in profile["allergies"]:
                    mine = ' class="is-mine"'

                items += f"<li{mine}><b>{code}</b>{esc(name)}</li>"

            about = ""

            for line in T["about_lines"]:
                about += f"<li>{esc(line)}</li>"

            st.html(
                f'<div class="info-card"><h3 class="info-card-title">{esc(T["allergy_table_title"])}</h3>'
                f'<p class="muted">{esc(T["allergy_table_intro"])}</p>'
                f'<ul class="legend-list">{items}</ul></div>'
                f'<div class="info-card"><h3 class="info-card-title">{esc(T["about_title"])}</h3>'
                f'<ul class="plain">{about}</ul></div>'
            )

        show_source()
