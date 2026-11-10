import html
from pathlib import Path

import streamlit as st

from api import check_pwned_password
from cases import CASE_SOURCES, REAL_CASES
from database import (
    add_case,
    add_record,
    create_tables,
    find_service_id,
    get_incidents,
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
MENU_ICONS = {
    MENU_INTRO: ":material/home:",
    MENU_RECORD: ":material/edit_note:",
    MENU_TODO: ":material/checklist:",
}

# 위험 등급마다 쓰는 색 이름(style.css의 pill-*)과 표시 글자
GRADE_PILLS = {
    "높음": ("red", T["risk_high"]),
    "보통": ("yellow", T["risk_mid"]),
    "낮음": ("gray", T["risk_low"]),
}


# ---------- 화면 조각을 만드는 함수 ----------
# 사용자가 입력한 글자는 esc()로 바꿔서 넣는다.
# 그대로 넣으면 입력한 글자가 HTML 태그로 동작할 수 있기 때문이다.


def esc(text):
    """글자를 HTML에 안전하게 넣을 수 있도록 바꾼다."""
    return html.escape(str(text))


def pill(text, tone):
    """알약 모양 표시를 만든다. tone은 red, yellow, gray, navy, mint 중 하나."""
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


def show_page_head(title, intro):
    """화면 제목과 한 줄 설명을 보여 준다."""
    st.html(f'<div class="page-head"><h1>{esc(title)}</h1><p>{esc(intro)}</p></div>')


def show_empty(message):
    """아직 내용이 없는 자리에 안내 문장을 보여 준다."""
    st.html(f'<div class="empty">{esc(message)}</div>')


def show_notice():
    """저장한 뒤 화면을 새로 그린 다음에 보여 줄 안내를 꺼내 보여 준다."""
    if "notice" in st.session_state:
        st.success(st.session_state.pop("notice"))

    # 방금 기록했다면 할 일 화면으로 가는 버튼을 함께 보여 준다.
    if st.session_state.pop("offer_todo", False):
        st.button(
            T["record_saved_next_button"],
            type="primary",
            on_click=go_to,
            args=(MENU_TODO,),
        )


# ---------- 계산과 동작을 돕는 함수 ----------


def go_to(menu, mode=None):
    """버튼을 누르면 다른 화면으로 옮긴다. mode는 기록하기 화면의 방식이다."""
    st.session_state["menu"] = menu

    if mode is not None:
        st.session_state["record_mode"] = mode


def count_remaining(incident):
    """아직 끝내지 않은 할 일의 개수를 센다."""
    remaining = 0

    for action in incident["actions"]:
        if not action["done"]:
            remaining += 1

    return remaining


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


# 1. 프로그램 설정
st.set_page_config(
    page_title="유출장부",
    page_icon=str(APP_FOLDER / "static" / "logo.png"),
)

# 카드, 알약 모양 표시 같은 화면 모양을 정하는 CSS
st.html(APP_FOLDER / "style.css")

create_tables()

st.sidebar.html(
    '<div class="brand"><img src="app/static/logo.png" alt="">유출장부</div>'
)
st.sidebar.caption(T["tagline"])

menu = st.sidebar.radio(
    "유출장부 메뉴",
    list(MENU_ICONS),
    format_func=lambda name: f"{MENU_ICONS[name]} {name}",
    key="menu",
    label_visibility="collapsed",
)


# 2. 소개
if menu == MENU_INTRO:
    incidents = get_incidents()
    remaining_total = 0

    for incident in incidents:
        remaining_total += count_remaining(incident)

    # 2-1. 머리 영역: 이 앱이 무엇인지와 시작 버튼
    with st.container(key="hero"):
        hero = f"<h1>{esc(T['intro_hero_title'])}</h1><p>{esc(T['intro_hero_body'])}</p>"

        if len(incidents) > 0:
            progress = T["intro_progress"].format(
                remaining=remaining_total,
                records=len(incidents),
            )
            hero += f'<p class="hero-progress">{esc(progress)}</p>'

        st.html(hero)

        with st.container(horizontal=True):
            if len(incidents) > 0:
                st.button(
                    T["intro_progress_button"],
                    type="primary",
                    on_click=go_to,
                    args=(MENU_TODO,),
                )
                start_type = "secondary"
            else:
                start_type = "primary"

            st.button(
                T["intro_start_button"],
                type=start_type,
                on_click=go_to,
                args=(MENU_RECORD, T["record_mode_manual"]),
            )
            st.button(
                T["intro_example_button"],
                on_click=go_to,
                args=(MENU_RECORD, T["record_mode_case"]),
            )

    # 2-2. 사용 방법 3단계
    st.header(T["intro_steps_title"], anchor=False)

    steps = ""

    for number in (1, 2, 3):
        steps += (
            f'<div class="step"><b>{number}</b>'
            f"<strong>{esc(T[f'step{number}_title'])}</strong>"
            f"<p>{esc(T[f'step{number}_body'])}</p></div>"
        )

    st.html(f'<div class="steps">{steps}</div>')

    # 2-3. 왜 필요한지
    st.html(
        f'<div class="card"><h2>{esc(T["intro_why_title"])}</h2>'
        f"<p>{esc(T['intro_why_body'])}</p>"
        f'<p class="source"><a href="{CASE_SOURCES["국내"]}" target="_blank">'
        f"{esc(T['intro_why_source_label'])}</a></p></div>"
    )

    # 2-4. 해 주는 일과 하지 않는 일
    does = ""

    for line in T["intro_does"]:
        does += f"<li>{esc(line)}</li>"

    does_not = ""

    for line in T["intro_does_not"]:
        does_not += f"<li>{esc(line)}</li>"

    st.html(
        '<div class="two">'
        f'<div class="card"><h2>{esc(T["intro_does_title"])}</h2><ul>{does}</ul></div>'
        f'<div class="card"><h2>{esc(T["intro_does_not_title"])}</h2><ul>{does_not}</ul></div>'
        "</div>"
    )

    st.warning(T["intro_shared_notice"])


# 3. 기록하기
elif menu == MENU_RECORD:
    show_page_head(T["record_title"], T["record_intro"])
    show_notice()

    # 직접 적을지, 실제 사례에서 고를지 정한다.
    if "record_mode" not in st.session_state:
        st.session_state["record_mode"] = T["record_mode_manual"]

    mode = st.segmented_control(
        T["record_mode_label"],
        [T["record_mode_manual"], T["record_mode_case"]],
        key="record_mode",
    )

    # 3-1. 실제 사례에서 고르기
    if mode == T["record_mode_case"]:
        group_names = {
            "국내": T["case_group_domestic"],
            "해외": T["case_group_overseas"],
        }

        case_index = st.selectbox(
            T["case_select_label"],
            options=range(len(REAL_CASES)),
            format_func=lambda index: (
                f"{group_names[REAL_CASES[index]['region']]} · {REAL_CASES[index]['name']}"
            ),
        )
        case = REAL_CASES[case_index]

        with st.container(key="card_case"):
            st.html(
                '<div class="card-head">'
                f'<span class="card-title">{esc(case["name"])}</span>'
                f"{risk_pill(calc_risk_score(case['items']))}"
                "</div>"
                f'<p class="card-note">{esc(T[case["note"]])}</p>'
                + spec_row(T["case_date_label"], esc(case["date"] or T["case_date_missing"]))
                + spec_row(
                    T["case_size_label"],
                    esc(size_text(case["size"], T["case_size_unknown"])),
                )
                + spec_row(T["case_items_label"], chips(case["items"]))
            )

            if find_service_id(case["name"]) is not None:
                st.caption(T["case_already"])
            elif st.button(T["case_submit"], type="primary"):
                add_case(case)
                st.session_state["notice"] = T["case_saved"].format(name=case["name"])
                st.session_state["offer_todo"] = True
                st.rerun()

        if case["region"] == "국내":
            source = T["case_source_domestic"]
        else:
            source = T["case_source_overseas"]

        st.caption(f"[{source}]({CASE_SOURCES[case['region']]})")

    # 3-2. 직접 적기
    else:
        # 저장에 성공한 다음 실행에서만 입력칸을 비운다.
        # 입력이 잘못됐을 때는 적어 둔 내용을 그대로 둔다.
        if st.session_state.pop("clear_record_form", False):
            st.session_state["record_name"] = ""
            st.session_state["record_items"] = []
            st.session_state["record_size"] = 0
            st.session_state["record_other"] = ""
            st.session_state["record_memo"] = ""

        today = today_kst()

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

        if submitted:
            items = list(selected_items)

            for item in other_items.split(","):
                item = item.strip()

                if item != "" and item not in items:
                    items.append(item)

            status = add_record(name, category, memo, notified_date, items, leak_size)

            if status == "SUCCESS":
                st.session_state["notice"] = T["record_saved"].format(name=name.strip())
                st.session_state["offer_todo"] = True
                st.session_state["clear_record_form"] = True
                st.rerun()

            elif status == "EMPTY":
                st.warning(T["err_no_name"])

            elif status == "NO_ITEMS":
                st.warning(T["err_no_items"])

            else:
                st.warning(T["err_future_date"])

    # 3-3. 위험 점수를 매기는 기준
    with st.expander(T["guide_label"]):
        st.write(T["guide_body"])

        weight_table = []

        for item, weight in ITEM_WEIGHTS.items():
            weight_table.append(
                {T["guide_col_item"]: item, T["guide_col_score"]: weight}
            )

        st.dataframe(weight_table, width="stretch", hide_index=True)
        st.write(T["guide_grades"])


# 4. 할 일
elif menu == MENU_TODO:
    show_page_head(T["todo_title"], T["todo_intro"])
    show_notice()

    all_incidents = get_incidents()

    if len(all_incidents) == 0:
        show_empty(T["todo_empty"])
        st.button(
            T["todo_empty_button"],
            type="primary",
            on_click=go_to,
            args=(MENU_RECORD, T["record_mode_manual"]),
        )
    else:
        # 4-1. 요약 한 줄
        remaining_total = 0

        for incident in all_incidents:
            remaining_total += count_remaining(incident)

        if remaining_total == 0:
            summary = T["todo_all_done"]
        else:
            summary = T["todo_summary"].format(
                remaining=remaining_total,
                records=len(all_incidents),
            )

        st.html(f'<div class="summary">{esc(summary)}</div>')

        # 4-2. 찾기: 버튼을 눌러야 조건이 적용된다.
        with st.form("search_form"):
            first, second, third = st.columns([5, 5, 2], vertical_alignment="bottom")
            keyword = first.text_input(T["todo_search_label"])
            state = second.segmented_control(
                T["todo_state_label"],
                [T["state_all"], T["state_open"], T["state_done"]],
                default=T["state_all"],
            )
            third.form_submit_button(T["todo_search_button"])

        # 화면의 말을 database.py가 쓰는 상태 이름으로 바꾼다.
        if state == T["state_open"]:
            status = "진행 중"
        elif state == T["state_done"]:
            status = "완료"
        else:
            status = "전체"

        incidents = get_incidents(keyword, "전체", status)

        if len(incidents) == 0:
            show_empty(T["todo_no_match"])

        # 4-3. 기록마다 카드 하나 (위험 점수가 높은 기록부터)
        for incident in incidents:
            total = len(incident["actions"])
            done = total - count_remaining(incident)
            percent = 0

            if total > 0:
                percent = round(done / total * 100)

            if incident["resolved"]:
                state_pill = pill(T["pill_done"], "mint")
            else:
                state_pill = pill(T["pill_open"], "navy")

            meta = T["card_meta"].format(
                date=incident["notified_date"],
                size=size_text(incident["leak_size"], T["size_unknown"]),
            )
            progress = T["card_progress"].format(done=done, total=total)

            with st.container(key=f"card_incident_{incident['id']}"):
                st.html(
                    '<div class="card-head">'
                    f'<span class="card-title">{esc(incident["service_name"])}</span>'
                    f"{risk_pill(incident['risk_score'])}{state_pill}"
                    "</div>"
                    f'<p class="card-meta">{esc(meta)}</p>'
                    + chips(incident["leaked_items"])
                    + f'<p class="progress-text">{esc(progress)}</p>'
                    f'<div class="progress"><div style="width: {percent}%"></div></div>'
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

                # 4-4. 비밀번호가 이미 퍼졌는지 확인
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
                        st.error(
                            T["pw_found"].format(count=f"{incident['pwned_count']:,}")
                        )

    # 4-5. 신고하거나 상담받을 곳
    with st.expander(T["help_label"]):
        st.html(
            spec_row(
                T["help_lookup"],
                '<a href="https://kidc.eprivacy.go.kr" target="_blank">kidc.eprivacy.go.kr</a>',
            )
            + spec_row(T["help_privacy"], "118")
            + spec_row(T["help_phishing"], "1394")
            + spec_row(
                T["help_finance"],
                '<a href="https://pd.fss.or.kr" target="_blank">pd.fss.or.kr</a>',
            )
            + spec_row(
                T["help_phone"],
                '<a href="https://www.msafer.or.kr" target="_blank">msafer.or.kr</a>',
            )
        )
