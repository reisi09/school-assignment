# screen_todo.py
# 할 일 화면: 기록마다 카드 하나를 보여 준다.
# 카드에서 할 일을 하나씩 직접 해 보고(screen_missions.py의 창), 비밀번호를 확인하고,
# 기록을 고치거나 지운다.

from datetime import date

import streamlit as st

from api import check_pwned_password
from common import (
    CATEGORIES,
    ERROR_TEXTS,
    chips,
    confetti,
    esc,
    gauge,
    icon,
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
    save_pwned_count,
    today_kst,
    update_record,
)
from play import find_blocked_attacks
from rules import ITEM_WEIGHTS, get_mission_type
from screen_missions import clear_mission_state, show_mission
from stats import count_all_remaining, count_remaining, get_remaining_score
from texts import TEXT as T


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


def mission_row(number, action, blocked, flash):
    """
    할 일 한 줄을 만든다. 번호(끝냈으면 체크 표시), 할 일 이름, 결과, 막는 공격 이름표가 있다.

    flash가 True면 방금 끝낸 줄이라 한 번 반짝인다.
    """
    classes = "mission-row"

    if action["done"]:
        classes += " is-done"
        mark = f'<span class="mission-mark">{icon("check")}</span>'
        result = action.get("result") or T["pill_done"]
        line = T["mission_done_line"].format(date=action["done_date"], result=result)
        sub = f'<p class="mission-sub">{esc(line)}</p>'
        label = T["mission_blocked_label"]
    else:
        mark = f'<span class="mission-mark">{number}</span>'
        sub = ""
        label = T["mission_blocks_label"]

    if flash:
        classes += " just-done"

    tags = ""

    for attack in blocked:
        tags += f'<span class="attack-tag">{esc(T["attack_" + attack["name"] + "_title"])}</span>'

    if tags != "":
        tags = f'<div class="mission-tags"><span>{esc(label)}</span>{tags}</div>'

    return (
        f'<div class="{classes}">{mark}'
        f'<div><p class="mission-name">{esc(action["name"])}</p>{sub}{tags}</div></div>'
    )


def show_mission_rows(incident, just_done):
    """
    할 일마다 한 줄과 버튼을 보여 준다. 버튼을 누르면 그 할 일을 해 보는 창이 열린다.

    just_done은 방금 끝낸 할 일의 "기록번호_할일순서"다. 아직 안 끝낸 첫 할 일은 눈에 띄게 한다.
    """
    next_marked = False

    for index, action in enumerate(incident["actions"]):
        row_id = f"{incident['id']}_{index}"
        blocked = find_blocked_attacks(get_mission_type(action["name"]), incident["leaked_items"])

        # key가 mnext_로 시작하는 줄은 style.css에서 버튼이 숨 쉬듯 빛난다.
        if not action["done"] and not next_marked:
            row_key = "mnext_" + row_id
            button_type = "primary"
            next_marked = True
        else:
            row_key = "mrow_" + row_id
            button_type = "secondary"

        if action["done"]:
            label = T["mission_review"]
        else:
            label = T["mission_start"]

        # wrap=False: 글이 길어도 버튼이 아랫줄로 내려가지 않고 오른쪽에 붙어 있다.
        with st.container(key=row_key, horizontal=True, vertical_alignment="center", wrap=False):
            st.html(mission_row(index + 1, action, blocked, just_done == row_id), width="stretch")

            if st.button(label, key="mission_" + row_id, type=button_type):
                # 창을 열 때마다 처음부터 시작한다.
                clear_mission_state("m_" + row_id)
                show_mission(incident, index)


def show_incident_card(incident, just_done):
    """기록 하나를 카드로 보여 준다. 할 일을 끝낼수록 계기판의 남은 위험 점수가 줄어든다."""
    total = len(incident["actions"])
    done = total - count_remaining(incident)

    # 지난번에 보여 준 점수와 끝낸 수를 기억해 두고, 거기서 지금 값까지 계기판과 막대가 움직인다.
    # 처음 볼 때는 처음 위험 점수에서 남은 위험 점수까지 바늘이 내려온다.
    remaining = get_remaining_score(incident)
    score_key = f"shown_score_{incident['id']}"
    done_key = f"shown_done_{incident['id']}"
    previous_score = st.session_state.get(score_key, incident["risk_score"])
    previous_done = st.session_state.get(done_key, 0)
    st.session_state[score_key] = remaining
    st.session_state[done_key] = done

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
            + '<div class="card-gauge">'
            + gauge(remaining, previous_score, incident["risk_score"])
            + '<div class="card-gauge-text">'
            + f'<p class="card-gauge-label">{esc(T["card_risk_label"].format(score=incident["risk_score"]))}</p>'
            + progress_bar(
                T["card_progress"].format(done=done, total=total),
                done,
                total,
                previous_done,
            )
            + "</div></div>"
        )

        show_mission_rows(incident, just_done)

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

        # 할 일을 끝내거나 되돌렸으면 화면 구석에 알림을 잠깐 띄운다.
        if "mission_toast" in st.session_state:
            st.toast(st.session_state.pop("mission_toast"), icon=":material/verified_user:")

        # 방금 끝낸 할 일 줄을 한 번만 반짝이게 꺼내 둔다.
        just_done = st.session_state.pop("just_done", None)

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
                        show_incident_card(incident, just_done)

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
