# screen_record.py
# 기록하기 화면: 알림문을 붙여넣거나, 직접 적거나, 실제 사례를 골라 기록한다.

import streamlit as st

from cases import CASE_SOURCES, REAL_CASES
from common import (
    CATEGORIES,
    ERROR_TEXTS,
    MENU_TODO,
    REGION_NAMES,
    esc,
    show_case_row,
    show_page_head,
    spec_row,
)
from database import add_record, today_kst
from rules import ITEM_WEIGHTS, find_items_in_text
from texts import TEXT as T

REGION_SOURCES = {
    "국내": T["case_source_domestic"],
    "해외": T["case_source_overseas"],
}


def fill_from_notice():
    """붙여넣은 알림문에서 유출된 정보를 찾아 '유출된 정보' 칸에 골라 둔다."""
    text = st.session_state["paste_text"]

    if text.strip() == "":
        st.session_state["paste_message"] = T["paste_empty"]
        st.session_state["paste_found"] = False
        return

    found = find_items_in_text(text)

    if len(found) == 0:
        st.session_state["paste_message"] = T["paste_none"]
        st.session_state["paste_found"] = False
    else:
        st.session_state["record_items"] = found
        st.session_state["paste_message"] = T["paste_found"].format(
            count=len(found),
            items=", ".join(found),
        )
        st.session_state["paste_found"] = True


def show_paste_box():
    """받은 알림문을 붙여넣는 칸을 보여 준다. 버튼을 누르면 유출된 정보를 찾아 골라 둔다."""
    with st.container(key="card_paste"):
        st.text_area(
            T["paste_label"],
            key="paste_text",
            placeholder=T["paste_placeholder"],
            height=130,
        )
        st.caption(T["paste_help"])
        st.button(T["paste_button"], on_click=fill_from_notice)

        # 찾은 결과를 한 번 알려 준다.
        if "paste_message" in st.session_state:
            message = st.session_state.pop("paste_message")

            if st.session_state.pop("paste_found"):
                st.success(message)
            else:
                st.warning(message)


def show_record_form():
    """유출 알림을 직접 적는 칸을 보여 주고, 저장 버튼을 누르면 기록한다."""
    today = today_kst()

    with st.container(key="card_form"):
        with st.form("record_form"):
            name = st.text_input(
                T["field_service"],
                key="record_name",
                placeholder=T["field_service_placeholder"],
            )
            selected_items = st.multiselect(
                T["field_items"],
                list(ITEM_WEIGHTS),
                key="record_items",
                placeholder=T["field_items_placeholder"],
                select_all=False,
            )
            notified_date = st.date_input(
                T["field_date"],
                value=today,
                max_value=today,
                format="YYYY-MM-DD",
            )

            # 안 적어도 되는 항목은 접어 둔다.
            with st.expander(T["more_label"]):
                category = st.selectbox(
                    T["field_category"],
                    CATEGORIES,
                    index=len(CATEGORIES) - 1,
                )
                leak_size = st.number_input(
                    T["field_size"],
                    min_value=0,
                    step=1,
                    key="record_size",
                )
                st.caption(T["field_size_help"])
                other_items = st.text_input(T["field_other"], key="record_other")
                st.caption(T["field_other_help"])
                memo = st.text_input(T["field_memo"], key="record_memo")

            submitted = st.form_submit_button(T["record_submit"], type="primary")

    if not submitted:
        return

    # 목록에서 고른 정보에 직접 적은 정보를 더한다.
    items = list(selected_items)

    for item in other_items.split(","):
        item = item.strip()

        if item != "" and item not in items:
            items.append(item)

    status = add_record(name, category, memo, notified_date, items, leak_size)

    if status == "SUCCESS":
        # 저장했으면 할 일 화면으로 옮겨 방금 만든 기록을 보여 준다.
        # 화면을 옮기면 적어 둔 내용은 저절로 비워진다.
        st.session_state["notice"] = T["record_saved"].format(name=name.strip())
        st.session_state["pending_menu"] = MENU_TODO
        st.rerun()

    else:
        # 잘못 적었으면 이유를 알려 주고, 적어 둔 내용은 그대로 둔다.
        st.warning(ERROR_TEXTS[status])


def show_record():
    """기록하기 화면: 알림문을 붙여넣거나 직접 적거나 실제 사례에서 고른다."""
    with st.container(key="sec_page"):
        show_page_head(T["record_title"], T["record_intro"])

        # 직접 적을지, 실제 사례에서 고를지 정한다.
        if "record_mode" not in st.session_state:
            st.session_state["record_mode"] = T["record_mode_manual"]

        mode = st.segmented_control(
            T["record_mode_label"],
            [T["record_mode_manual"], T["record_mode_case"]],
            key="record_mode",
            label_visibility="collapsed",
        )

        # 실제 사례에서 고르기: 국내와 해외로 나눠 카드로 보여 준다.
        if mode == T["record_mode_case"]:
            for region in ("국내", "해외"):
                indexes = []

                for index, case in enumerate(REAL_CASES):
                    if case["region"] == region:
                        indexes.append(index)

                st.html(
                    f'<h2 class="group-title">{esc(REGION_NAMES[region])}'
                    f'<a href="{CASE_SOURCES[region]}" target="_blank">'
                    f"{esc(REGION_SOURCES[region])}</a></h2>"
                )
                show_case_row("record", indexes)

        # 직접 적기: 왼쪽에 붙여넣는 칸과 적는 칸, 오른쪽에 위험 점수를 매기는 기준
        else:
            form_column, guide_column = st.columns([7, 5], gap="large")

            with form_column:
                show_paste_box()
                show_record_form()

            rows = ""

            for item, weight in ITEM_WEIGHTS.items():
                rows += spec_row(item, weight)

            guide_column.html(
                f'<div class="soft"><h3>{esc(T["guide_label"])}</h3>'
                f"<p>{esc(T['guide_body'])}</p>"
                f'<div style="margin-top: 1rem">{rows}</div>'
                f'<p style="margin-top: 0.75rem">{esc(T["guide_grades"])}</p></div>'
            )
