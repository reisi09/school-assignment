# app.py
# 유출장부의 화면. 아래 순서로 읽으면 된다.
#   1. 화면 조각을 만드는 함수   HTML 글자를 만들어 돌려준다
#   2. 계산과 동작을 돕는 함수   버튼을 눌렀을 때 하는 일
#   3. 카드를 보여 주는 함수     실제 사례 카드, 기록 카드
#   4. 화면을 보여 주는 함수     위쪽 메뉴, 소개, 기록하기, 할 일
#   5. 프로그램 실행             설정을 하고 메뉴에 맞는 화면을 부른다

import html
from pathlib import Path

import streamlit as st

from api import check_pwned_password
from cases import CASE_SOURCES, REAL_CASES
from database import (
    add_case,
    add_record,
    create_tables,
    get_incidents,
    get_recorded_names,
    save_actions,
    save_pwned_count,
    today_kst,
)
from rules import ITEM_WEIGHTS, calc_risk_score, get_risk_grade, update_action_states
from texts import TEXT as T

APP_FOLDER = Path(__file__).resolve().parent
CATEGORIES = ["금융", "쇼핑", "교육", "게임", "기타"]

# 화면은 세 개다. 이름은 texts.py에서 가져온다.
MENU_INTRO = T["menu_intro"]
MENU_RECORD = T["menu_record"]
MENU_TODO = T["menu_todo"]

# 소개 화면 맨 위에 보여 줄 실제 사례 세 건
FEATURED_CASES = ["할리스 멤버십", "빗썸", "Adobe"]

# 위험 등급마다 쓰는 색 이름(style.css의 pill-*)과 표시 글자
GRADE_PILLS = {
    "높음": ("red", T["risk_high"]),
    "보통": ("yellow", T["risk_mid"]),
    "낮음": ("navy", T["risk_low"]),
}
REGION_NAMES = {
    "국내": T["case_group_domestic"],
    "해외": T["case_group_overseas"],
}
REGION_SOURCES = {
    "국내": T["case_source_domestic"],
    "해외": T["case_source_overseas"],
}


# ---------- 1. 화면 조각을 만드는 함수 ----------
# 사용자가 입력한 글자는 esc()로 바꿔서 넣는다.
# 그대로 넣으면 입력한 글자가 HTML 태그로 동작할 수 있기 때문이다.


def esc(text):
    """글자를 HTML에 안전하게 넣을 수 있도록 바꾼다."""
    return html.escape(str(text))


def pill(text, tone):
    """알약 모양 표시를 만든다. tone은 red, yellow, mint, navy, gray 중 하나."""
    return f'<span class="pill pill-{tone}">{esc(text)}</span>'


def risk_pill(score):
    """위험 등급을 알약 모양으로 만든다."""
    tone, text = GRADE_PILLS[get_risk_grade(score)]
    return pill(text, tone)


def chips(items):
    """유출된 정보를 이름표로 나열한다."""
    tags = ""

    for item in items:
        tags += f'<span class="chip">{esc(item)}</span>'

    return f'<div class="chips">{tags}</div>'


def spec_row(label, value):
    """이름은 왼쪽, 값은 오른쪽에 두는 한 줄을 만든다. value는 HTML이다."""
    return f'<div class="spec"><span>{esc(label)}</span><strong>{value}</strong></div>'


def progress_bar(done, total):
    """끝낸 할 일의 비율을 글자와 막대로 만든다."""
    percent = 0

    if total > 0:
        percent = round(done / total * 100)

    text = T["card_progress"].format(done=done, total=total)

    return (
        f'<p class="progress-text">{esc(text)}</p>'
        f'<div class="progress"><div style="width: {percent}%"></div></div>'
    )


# ---------- 2. 계산과 동작을 돕는 함수 ----------


def go_to(menu, mode=None):
    """버튼을 누르면 다른 화면으로 옮긴다. mode는 기록하기 화면의 방식이다."""
    st.session_state["menu"] = menu

    if mode is not None:
        st.session_state["record_mode"] = mode


def record_case(index):
    """실제 사례 카드의 버튼을 누르면 그 사례를 기록하고 할 일 화면으로 옮긴다."""
    case = REAL_CASES[index]

    if add_case(case) == "SUCCESS":
        st.session_state["notice"] = T["case_saved"].format(name=case["name"])

    st.session_state["menu"] = MENU_TODO


def count_remaining(incident):
    """기록 하나에서 아직 끝내지 않은 할 일의 개수를 센다."""
    remaining = 0

    for action in incident["actions"]:
        if not action["done"]:
            remaining += 1

    return remaining


def count_all_remaining(incidents):
    """여러 기록에 남은 할 일을 모두 더한다."""
    total = 0

    for incident in incidents:
        total += count_remaining(incident)

    return total


def size_text(size, unknown):
    """유출 규모를 글자로 바꾼다. 0은 모른다는 뜻이다."""
    if size == 0:
        return unknown

    return f"{size:,}{T['size_unit']}"


def save_checked_actions(incident):
    """체크 상자를 누르면 그 기록의 할 일 상태를 바로 저장한다."""
    done_flags = []

    for index in range(len(incident["actions"])):
        done_flags.append(st.session_state[f"action_{incident['id']}_{index}"])

    actions = update_action_states(
        incident["actions"],
        done_flags,
        today_kst().isoformat(),
    )
    save_actions(incident["id"], actions)


# ---------- 3. 카드를 보여 주는 함수 ----------


def show_case_card(place, index, recorded):
    """
    실제 사례 하나를 카드로 보여 준다.

    place는 카드가 놓인 화면을 구분하는 이름, recorded는 이미 기록한 서비스 이름 집합이다.
    """
    case = REAL_CASES[index]

    with st.container(key=f"card_case_{place}_{index}", height="stretch"):
        st.html(
            '<div class="card-head">'
            f'<span class="card-title">{esc(case["name"])}</span>'
            '<span class="pills">'
            f"{risk_pill(calc_risk_score(case['items']))}"
            f"{pill(REGION_NAMES[case['region']], 'gray')}"
            "</span></div>"
            '<div class="figure">'
            f"<b>{esc(size_text(case['size'], T['case_size_unknown']))}</b>"
            f"<span>{esc(T['case_size_label'])}</span></div>"
            + spec_row(T["case_date_label"], esc(case["date"] or T["case_date_missing"]))
            + spec_row(T["case_items_label"], chips(case["items"]))
            + f'<p class="card-note">{esc(T[case["note"]])}</p>'
        )

        if case["name"].casefold() in recorded:
            st.caption(T["case_already"])
        else:
            st.button(
                T["case_submit"],
                key=f"case_button_{place}_{index}",
                on_click=record_case,
                args=(index,),
                width="stretch",
            )


def show_case_row(place, indexes):
    """실제 사례 카드를 한 줄에 세 개씩 놓는다."""
    # 이미 기록한 사례인지는 카드마다 묻지 않고 여기서 한 번만 조회한다.
    recorded = get_recorded_names()

    for start in range(0, len(indexes), 3):
        columns = st.columns(3, gap="medium")

        for column, index in zip(columns, indexes[start : start + 3]):
            with column:
                show_case_card(place, index, recorded)


def show_incident_card(incident):
    """기록 하나를 카드로 보여 준다. 할 일을 체크하고 비밀번호를 확인할 수 있다."""
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
            + progress_bar(done, total)
        )

        # 체크하면 바로 저장된다.
        for index, action in enumerate(incident["actions"]):
            label = action["name"]

            if action["done"]:
                label += " " + T["done_suffix"].format(date=action["done_date"])

            st.checkbox(
                label,
                value=action["done"],
                key=f"action_{incident['id']}_{index}",
                on_change=save_checked_actions,
                args=(incident,),
            )

        # 비밀번호가 이미 퍼졌는지 확인
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


# ---------- 4. 화면을 보여 주는 함수 ----------


def show_page_head(title, intro):
    """화면 제목과 한 줄 설명을 보여 준다."""
    st.html(f'<h1 class="title">{esc(title)}</h1><p class="lead">{esc(intro)}</p>')


def show_nav():
    """위쪽 메뉴(로고, 화면 이름 세 개, 기록하기 버튼)를 보여 주고 고른 화면 이름을 돌려준다."""
    with st.container(
        key="nav",
        horizontal=True,
        horizontal_alignment="distribute",
        vertical_alignment="center",
    ):
        st.html(
            '<div class="brand"><img src="app/static/logo.png" alt="">유출장부</div>',
            width="content",
        )
        menu = st.radio(
            "유출장부 메뉴",
            [MENU_INTRO, MENU_RECORD, MENU_TODO],
            key="menu",
            horizontal=True,
            label_visibility="collapsed",
            width="content",
        )
        st.button(
            T["nav_cta"],
            type="primary",
            on_click=go_to,
            args=(MENU_RECORD, T["record_mode_manual"]),
        )

    return menu


def show_intro():
    """소개 화면: 머리 구역, 사용 방법, 큰 숫자, 해 주는 일과 하지 않는 일."""
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


def show_record_form():
    """유출 알림을 직접 적는 칸을 보여 주고, 저장 버튼을 누르면 기록한다."""
    # 저장에 성공한 다음 실행에서만 입력칸을 비운다.
    # 입력이 잘못됐을 때는 적어 둔 내용을 그대로 둔다.
    if st.session_state.pop("clear_record_form", False):
        st.session_state["record_name"] = ""
        st.session_state["record_items"] = []
        st.session_state["record_size"] = 0
        st.session_state["record_other"] = ""
        st.session_state["record_memo"] = ""

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
        st.session_state["notice"] = T["record_saved"].format(name=name.strip())
        st.session_state["clear_record_form"] = True
        st.session_state["pending_menu"] = MENU_TODO
        st.rerun()

    elif status == "EMPTY":
        st.warning(T["err_no_name"])

    elif status == "NO_ITEMS":
        st.warning(T["err_no_items"])

    else:
        st.warning(T["err_future_date"])


def show_record():
    """기록하기 화면: 직접 적거나 실제 사례에서 고른다."""
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

        # 직접 적기: 왼쪽에 적는 칸, 오른쪽에 위험 점수를 매기는 기준
        else:
            form_column, guide_column = st.columns([7, 5], gap="large")

            with form_column:
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


def show_todo():
    """할 일 화면: 요약, 찾기, 기록 카드, 신고·상담할 곳."""
    all_incidents = get_incidents()

    with st.container(key="sec_page"):
        show_page_head(T["todo_title"], T["todo_intro"])

        # 기록을 저장하고 넘어왔으면 안내를 한 번 보여 준다.
        if "notice" in st.session_state:
            st.success(st.session_state.pop("notice"))

        if len(all_incidents) == 0:
            st.html(f'<div class="empty">{esc(T["todo_empty"])}</div>')

            with st.container(horizontal=True, horizontal_alignment="center"):
                st.button(
                    T["todo_empty_button"],
                    type="primary",
                    on_click=go_to,
                    args=(MENU_RECORD, T["record_mode_manual"]),
                )
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


# ---------- 5. 프로그램 실행 ----------

st.set_page_config(
    page_title="유출장부",
    page_icon=str(APP_FOLDER / "static" / "logo.png"),
    layout="wide",
)

# 구역, 카드, 알약 모양 버튼 같은 화면 모양을 정하는 CSS
st.html(APP_FOLDER / "style.css")

create_tables()

# 기록을 저장한 다음 실행에서 옮겨 갈 화면이 정해져 있으면 먼저 반영한다.
if "pending_menu" in st.session_state:
    st.session_state["menu"] = st.session_state.pop("pending_menu")

menu = show_nav()

if menu == MENU_INTRO:
    show_intro()
elif menu == MENU_RECORD:
    show_record()
else:
    show_todo()
