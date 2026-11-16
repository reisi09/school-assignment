# screen_todo.py
# 할 일 화면: 기록마다 카드 하나를 보여 준다.
# 카드에서 할 일을 체크하고, 비밀번호를 확인하고, 기록을 고치거나 지운다.

from datetime import date

import streamlit as st

from api import check_pwned_password
from common import (
    CATEGORIES,
    ERROR_TEXTS,
    chips,
    confetti,
    esc,
    pill,
    progress_bar,
    repeat_box,
    risk_pill,
    show_empty,
    show_page_head,
    size_text,
    spec_row,
)
from database import (
    delete_record,
    get_incidents,
    save_actions,
    save_pwned_count,
    today_kst,
    update_record,
)
from rules import ITEM_WEIGHTS, update_action_states
from stats import count_all_remaining, count_remaining, get_remaining_score
from texts import TEXT as T


def save_checked_actions(incident):
    """체크 상자를 누르면 그 기록의 할 일 상태를 바로 저장한다."""
    done_flags = []

    for action in incident["actions"]:
        done_flags.append(st.session_state[f"action_{incident['id']}_{action['name']}"])

    actions = update_action_states(
        incident["actions"],
        done_flags,
        today_kst().isoformat(),
    )
    save_actions(incident["id"], actions)

    # 할 일을 모두 끝냈으면 다음 화면에서 축하 표시를 보여 준다.
    if all(done_flags):
        st.session_state["cheer"] = incident["service_name"]


def save_edit(incident):
    """고치기 칸의 저장 버튼을 누르면 적은 내용으로 기록을 고친다."""
    incident_id = incident["id"]
    name = st.session_state[f"edit_name_{incident_id}"]

    status = update_record(
        incident_id,
        name,
        st.session_state[f"edit_category_{incident_id}"],
        st.session_state[f"edit_memo_{incident_id}"],
        st.session_state[f"edit_date_{incident_id}"],
        st.session_state[f"edit_items_{incident_id}"],
        st.session_state[f"edit_size_{incident_id}"],
    )

    if status == "SUCCESS":
        st.session_state["notice"] = T["edit_saved"].format(name=name.strip())

    elif status in ERROR_TEXTS:
        st.session_state[f"edit_error_{incident_id}"] = ERROR_TEXTS[status]


def remove_record(incident):
    """지우기 버튼을 누르면 그 기록을 지운다."""
    delete_record(incident["id"])
    st.session_state["notice"] = T["delete_done"].format(name=incident["service_name"])


def show_password_check(incident):
    """기록 카드 안에서 비밀번호가 이미 퍼졌는지 확인하는 칸을 보여 준다."""
    with st.expander(T["pw_label"]):
        st.write(T["pw_body"])
        st.warning(T["pw_demo_warning"])

        with st.form(f"pw_form_{incident['id']}", clear_on_submit=True):
            password = st.text_input(T["pw_input"], type="password")
            submitted = st.form_submit_button(T["pw_button"])

        if submitted:
            with st.spinner(T["pw_button"]):
                count, status = check_pwned_password(password)

            if status == "SUCCESS":
                # 결과는 횟수만 저장하고, 저장된 값으로 화면을 다시 그린다.
                save_pwned_count(incident["id"], count)
                st.rerun()

            elif status == "EMPTY":
                st.warning(T["err_pw_empty"])

            elif status == "NETWORK_ERROR":
                st.error(T["err_network"])

            else:
                st.error(T["err_data"])

        # 이 기록에 저장된 마지막 확인 결과
        if incident["pwned_count"] is None:
            st.caption(T["pw_none"])
        elif incident["pwned_count"] == 0:
            st.info(T["pw_clean"])
        else:
            st.error(T["pw_found"].format(count=f"{incident['pwned_count']:,}"))


def show_edit_form(incident):
    """기록 카드 안에서 기록을 고치거나 지우는 칸을 보여 준다."""
    incident_id = incident["id"]

    # 목록에 없는 정보가 기록에 있으면 고를 수 있게 목록 뒤에 붙인다.
    options = list(ITEM_WEIGHTS)

    for item in incident["leaked_items"]:
        if item not in options:
            options.append(item)

    # 실제 사례로 만든 기록처럼 분류가 목록에 없으면 "기타"로 둔다.
    category_index = len(CATEGORIES) - 1

    if incident["category"] in CATEGORIES:
        category_index = CATEGORIES.index(incident["category"])

    # 고치지 못했으면 접힌 칸을 펼쳐서 이유를 보여 준다.
    error = st.session_state.pop(f"edit_error_{incident_id}", None)

    with st.expander(T["edit_label"], expanded=error is not None):
        st.caption(T["edit_help"])

        # 저장 버튼을 누르면 save_edit이 아래 칸의 값을 key로 읽어 간다.
        with st.form(f"edit_form_{incident_id}"):
            st.text_input(
                T["field_service"],
                value=incident["service_name"],
                key=f"edit_name_{incident_id}",
            )
            st.caption(T["edit_name_help"])
            st.multiselect(
                T["field_items"],
                options,
                default=incident["leaked_items"],
                key=f"edit_items_{incident_id}",
                accept_new_options=True,
                select_all=False,
            )
            st.caption(T["edit_items_help"])
            st.date_input(
                T["field_date"],
                value=date.fromisoformat(incident["notified_date"]),
                max_value=today_kst(),
                format="YYYY-MM-DD",
                key=f"edit_date_{incident_id}",
            )
            st.selectbox(
                T["field_category"],
                CATEGORIES,
                index=category_index,
                key=f"edit_category_{incident_id}",
            )
            st.number_input(
                T["field_size"],
                min_value=0,
                step=1,
                value=incident["leak_size"],
                key=f"edit_size_{incident_id}",
            )
            st.text_input(
                T["field_memo"],
                value=incident["memo"],
                key=f"edit_memo_{incident_id}",
            )
            st.form_submit_button(T["edit_submit"], on_click=save_edit, args=(incident,))

        if error is not None:
            st.warning(error)

        # 확인 상자에 체크해야 지우기 버튼을 누를 수 있다.
        confirmed = st.checkbox(T["delete_confirm"], key=f"delete_confirm_{incident_id}")
        st.button(
            T["delete_button"],
            key=f"delete_button_{incident_id}",
            disabled=not confirmed,
            on_click=remove_record,
            args=(incident,),
        )


def show_incident_card(incident):
    """기록 하나를 카드로 보여 준다. 할 일을 체크하면 남은 위험 점수가 줄어든다."""
    total = len(incident["actions"])
    done = total - count_remaining(incident)

    if incident["resolved"]:
        state_pill = pill(T["pill_done"], "mint")
    else:
        state_pill = pill(T["pill_open"], "gray")

    # 분류 · 알림 받은 날 · 유출 규모
    meta = incident["category"] + " · " + T["card_meta"].format(
        date=incident["notified_date"],
        size=size_text(incident["leak_size"], T["size_unknown"]),
    )

    # 메모는 적었을 때만 보여 준다.
    memo = ""

    if incident["memo"] != "":
        memo = f'<p class="card-note">{esc(incident["memo"])}</p>'

    with st.container(key=f"card_incident_{incident['id']}"):
        st.html(
            '<div class="card-head">'
            f'<span class="card-title">{esc(incident["service_name"])}</span>'
            f'<span class="pills">{risk_pill(incident["risk_score"])}{state_pill}</span>'
            "</div>"
            f'<p class="card-meta">{esc(meta)}</p>'
            + chips(incident["leaked_items"])
            + memo
            + '<div class="figure">'
            f"<b>{get_remaining_score(incident)}{esc(T['score_unit'])}</b>"
            f"<span>{esc(T['card_risk_label'].format(score=incident['risk_score']))}</span></div>"
            + progress_bar(T["card_progress"].format(done=done, total=total), done, total)
        )

        # 체크하면 바로 저장된다.
        # key에 할 일 이름을 넣어서, 기록을 고쳐 할 일의 순서가 바뀌어도 체크가 따라간다.
        for action in incident["actions"]:
            label = action["name"]

            if action["done"]:
                label += " " + T["done_suffix"].format(date=action["done_date"])

            st.checkbox(
                label,
                value=action["done"],
                key=f"action_{incident['id']}_{action['name']}",
                on_change=save_checked_actions,
                args=(incident,),
            )

        show_password_check(incident)
        show_edit_form(incident)


def show_todo():
    """할 일 화면: 요약, 반복 유출 경고, 찾기, 기록 카드, 신고·상담할 곳."""
    all_incidents = get_incidents()

    with st.container(key="sec_page"):
        show_page_head(T["todo_title"], T["todo_intro"])

        # 안내가 있든 없든 안내가 들어갈 자리를 먼저 잡아 둔다.
        # 안내가 사라질 때 아래 칸들의 순서가 밀리면 펼쳐 둔 칸이 도로 접히기 때문이다.
        notice_area = st.container()

        # 기록을 저장하거나 고치고 넘어왔으면 안내를 한 번 보여 준다.
        if "notice" in st.session_state:
            notice_area.success(st.session_state.pop("notice"))

        # 방금 한 기록의 할 일을 모두 끝냈으면 축하 표시를 한 번 보여 준다.
        if "cheer" in st.session_state:
            notice_area.success(T["todo_cheer"].format(name=st.session_state.pop("cheer")))
            notice_area.html(confetti())

        if len(all_incidents) == 0:
            show_empty(T["todo_empty"])
        else:
            # 요약 한 줄
            remaining_total = count_all_remaining(all_incidents)

            if remaining_total == 0:
                summary = T["todo_all_done"]
            else:
                summary = T["todo_summary"].format(
                    remaining=remaining_total,
                    records=len(all_incidents),
                )

            st.html(f'<p class="summary">{esc(summary)}</p>')

            # 같은 정보가 여러 곳에서 유출됐으면 알려 준다.
            warning = repeat_box(all_incidents)

            if warning != "":
                st.html(warning)

            # 찾기: 버튼을 눌러야 조건이 적용된다.
            with st.form("search_form"):
                with st.container(horizontal=True, vertical_alignment="bottom"):
                    keyword = st.text_input(T["todo_search_label"], width=320)
                    state = st.segmented_control(
                        T["todo_state_label"],
                        [T["state_all"], T["state_open"], T["state_done"]],
                        default=T["state_all"],
                        width="content",
                    )
                    st.form_submit_button(T["todo_search_button"])

            # 화면의 말을 database.py가 쓰는 상태 이름으로 바꾼다.
            if state == T["state_open"]:
                status = "진행 중"
            elif state == T["state_done"]:
                status = "완료"
            else:
                status = "전체"

            incidents = get_incidents(keyword, status)

            if len(incidents) == 0:
                st.html(f'<div class="empty">{esc(T["todo_no_match"])}</div>')

            # 기록마다 카드 하나. 한 줄에 두 개씩, 위험 점수가 높은 기록부터 놓는다.
            for start in range(0, len(incidents), 2):
                columns = st.columns(2, gap="medium")

                for column, incident in zip(columns, incidents[start : start + 2]):
                    with column:
                        show_incident_card(incident)

        # 신고하거나 상담받을 곳
        st.html(
            f'<h2 class="group-title">{esc(T["help_label"])}</h2>'
            '<div class="soft" style="margin-top: 1rem">'
            + spec_row(
                T["help_lookup"],
                '<a href="https://kidc.eprivacy.go.kr" target="_blank">kidc.eprivacy.go.kr</a>',
            )
            # 전화번호는 이름에 들어 있어서 오른쪽 값은 비워 둔다.
            + spec_row(T["help_privacy"], "")
            + spec_row(T["help_phishing"], "")
            + spec_row(
                T["help_finance"],
                '<a href="https://pd.fss.or.kr" target="_blank">pd.fss.or.kr</a>',
            )
            + spec_row(
                T["help_phone"],
                '<a href="https://www.msafer.or.kr" target="_blank">msafer.or.kr</a>',
            )
            + "</div>"
        )
