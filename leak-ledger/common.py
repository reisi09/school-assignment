# common.py
# 여러 화면이 함께 쓰는 값과 함수. 아래 순서로 들어 있다.
#   1. 화면 조각을 만드는 함수   HTML 글자를 만들어 돌려준다 (esc, pill, chips, gauge, phone, ...)
#   2. 화면을 옮기는 함수         go_to, record_case
#   3. 함께 쓰는 화면 부분        화면 제목, 기록이 없을 때의 안내, 실제 사례 카드
#
# 사용자가 입력한 글자는 esc()로 바꿔서 HTML에 넣는다.
# 그대로 넣으면 입력한 글자가 HTML 태그로 동작할 수 있기 때문이다.
#
# 움직임은 모두 style.css가 그린다. 여기서는 style="--from: 3; --to: 1"처럼
# 움직이기 전 값(--from)과 움직인 뒤 값(--to)만 HTML에 적어 준다.

import html

import streamlit as st

from cases import REAL_CASES
from database import add_case, get_recorded_names
from rules import calc_risk_score, get_risk_grade
from stats import find_repeated_items
from texts import TEXT as T

CATEGORIES = ["금융", "쇼핑", "교육", "게임", "기타"]

# 화면은 다섯 개다. 이름은 texts.py에서 가져온다.
MENU_INTRO = T["menu_intro"]
MENU_RECORD = T["menu_record"]
MENU_TODO = T["menu_todo"]
MENU_STATS = T["menu_stats"]
MENU_PLAY = T["menu_play"]

# 위험 등급마다 쓰는 색 이름(style.css의 pill-*)과 표시 글자
GRADE_PILLS = {
    "높음": ("red", T["risk_high"]),
    "보통": ("yellow", T["risk_mid"]),
    "낮음": ("navy", T["risk_low"]),
}

# 계기판 색: 위험이 낮으면 민트, 보통이면 노랑, 높으면 빨강
GAUGE_TONES = {
    "높음": "red",
    "보통": "yellow",
    "낮음": "mint",
}
REGION_NAMES = {
    "국내": T["case_group_domestic"],
    "해외": T["case_group_overseas"],
}

# 기록을 저장하거나 고치지 못했을 때 database.py가 돌려주는 값과 보여 줄 문구
ERROR_TEXTS = {
    "EMPTY": T["err_no_name"],
    "NO_ITEMS": T["err_no_items"],
    "FUTURE_DATE": T["err_future_date"],
    "DUPLICATE": T["err_name_taken"],
}

# 색종이 조각의 색 이름(style.css의 confetti-*)
CONFETTI_TONES = ["mint", "navy", "yellow", "red"]


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


def percent_of(part, whole):
    """part가 whole의 몇 %인지 0~100 사이 정수로 돌려준다."""
    if whole <= 0:
        return 0

    return min(100, round(part / whole * 100))


def progress_bar(text, done, total, previous=None):
    """
    진행 정도를 글자와 막대로 만든다.

    previous를 주면 막대가 previous에서 done까지 늘어나거나 줄어드는 움직임이 있다.
    """
    if previous is None:
        previous = done

    return (
        f'<p class="progress-text">{esc(text)}</p>'
        f'<div class="progress"><div style="--from: {percent_of(previous, total)}%; '
        f'--to: {percent_of(done, total)}%"></div></div>'
    )


def count_number(value, previous):
    """
    숫자를 보여 준다. 나타날 때 previous에서 value까지 숫자가 바뀌며 움직인다.

    움직이는 숫자는 CSS가 그리고, 화면 읽기 프로그램은 안쪽의 진짜 숫자를 읽는다.
    """
    return (
        f'<span class="count" style="--from: {previous}; --to: {value}">'
        f'<span class="sr-only">{value}</span></span>'
    )


def gauge(value, previous, maximum):
    """
    위험 점수 계기판을 만든다. 바늘과 색 띠가 previous에서 value까지 움직인다.

    maximum은 계기판이 가득 찼을 때의 점수다.
    """
    now = percent_of(value, maximum)
    before = percent_of(previous, maximum)

    # 점수가 오르면 계기판이 흔들리고, 내려가면 민트색으로 빛난다.
    move = ""

    if value > previous:
        move = " is-up"
    elif value < previous:
        move = " is-down"

    tone = GAUGE_TONES[get_risk_grade(value)]

    # 반원 띠는 0~100 중 --to만큼 칠하고, 바늘은 왼쪽 끝(0)에서 오른쪽 끝(100) 사이를 돈다.
    # 그림은 style.css의 .gauge-dial이 그린다. (Streamlit은 HTML 안의 SVG 그림을 지운다.)
    return (
        f'<div class="gauge gauge-{tone}{move}" style="--from: {before}; --to: {now}">'
        '<div class="gauge-dial"><span class="gauge-needle"></span></div>'
        f'<div class="gauge-number">{count_number(value, previous)}'
        f"<span>{esc(T['score_unit'])}</span></div>"
        "</div>"
    )


def icon(name):
    """작은 그림(check, cross, question, lock)을 만든다. 모양은 style.css의 .icon-이름이 그린다."""
    return f'<span class="icon icon-{name}" aria-hidden="true"></span>'


def verdict(ok, text):
    """
    결과를 알리는 띠를 만든다.

    ok가 True면 민트색 띠(맞음·막음), False면 빨간 띠(틀림·뚫림), None이면 회색 띠(모름)다.
    """
    if ok is None:
        return f'<div class="verdict verdict-maybe">{icon("question")}<p>{esc(text)}</p></div>'

    if ok:
        return f'<div class="verdict verdict-ok">{icon("check")}<p>{esc(text)}</p></div>'

    return f'<div class="verdict verdict-no">{icon("cross")}<p>{esc(text)}</p></div>'


def stamp(text, tone):
    """문자 위에 찍는 도장 모양 글자를 만든다. tone은 red 또는 mint."""
    return f'<span class="stamp stamp-{tone}">{esc(text)}</span>'


def phone(message, title, state="", mark=""):
    """
    가상 휴대전화 화면에 문자 한 통을 보여 준다.

    state가 "is-arriving"이면 '입력 중' 점이 잠깐 보인 뒤 문자가 나타나고,
    "is-wrong"이면 휴대전화가 흔들린다. mark는 문자 위에 찍을 도장(HTML)이다.
    """
    return (
        f'<div class="phone {state}">'
        '<div class="phone-bar"><span>9:41</span><span class="phone-signal"></span></div>'
        f'<p class="phone-title">{esc(title)}</p>'
        '<div class="phone-screen">'
        '<div class="typing"><i></i><i></i><i></i></div>'
        f'<div class="phone-sms">{esc(message)}{mark}</div>'
        "</div></div>"
    )


def bar_rows(rows):
    """
    막대그래프를 만든다. rows는 (이름, 건수, 색 이름) 목록이다.

    가장 큰 건수의 막대가 칸을 가득 채우고, 나머지는 그 비율만큼 그린다.
    """
    biggest = 1

    for name, count, tone in rows:
        if count > biggest:
            biggest = count

    bars = ""

    for name, count, tone in rows:
        percent = round(count / biggest * 100)
        bars += (
            f'<div class="bar-row"><span>{esc(name)}</span>'
            f'<div class="bar"><div class="bar-{tone}" style="width: {percent}%"></div></div>'
            f"<strong>{count}{esc(T['size_unit'])}</strong></div>"
        )

    return f'<div class="bars">{bars}</div>'


def repeat_box(incidents):
    """여러 곳에서 유출된 정보를 알리는 상자를 만든다. 없으면 빈 글자를 돌려준다."""
    repeated = find_repeated_items(incidents)

    if len(repeated) == 0:
        return ""

    rows = ""

    for item, names in repeated:
        line = T["repeat_line"].format(count=len(names), names=", ".join(names))
        rows += spec_row(item, esc(line))

    return (
        f'<div class="soft"><h3><span class="dot-red"></span>{esc(T["repeat_title"])}</h3>'
        f"<p>{esc(T['repeat_body'])}</p>"
        f'<div style="margin-top: 1rem">{rows}</div></div>'
    )


def confetti():
    """할 일을 모두 끝냈을 때 위에서 떨어지는 색종이 조각 24개를 만든다."""
    pieces = ""

    for index in range(24):
        left = index * 4 + 2  # 가로 위치(%)
        delay = (index % 6) * 0.08  # 떨어지기 시작하는 시간(초)
        tone = CONFETTI_TONES[index % 4]
        pieces += (
            f'<span class="confetti-{tone}" '
            f'style="left: {left}%; animation-delay: {delay}s"></span>'
        )

    return f'<div class="confetti" aria-hidden="true">{pieces}</div>'


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


def size_text(size, unknown):
    """유출 규모를 글자로 바꾼다. 0은 모른다는 뜻이다."""
    if size == 0:
        return unknown

    return f"{size:,}{T['size_unit']}"


def show_page_head(title, intro):
    """화면 제목과 한 줄 설명을 보여 준다."""
    st.html(f'<h1 class="title">{esc(title)}</h1><p class="lead">{esc(intro)}</p>')


def show_empty(text):
    """기록이 없을 때 안내와 기록하기 화면으로 가는 버튼을 보여 준다."""
    st.html(f'<div class="empty">{esc(text)}</div>')

    with st.container(horizontal=True, horizontal_alignment="center"):
        st.button(
            T["todo_empty_button"],
            type="primary",
            on_click=go_to,
            args=(MENU_RECORD, T["record_mode_manual"]),
        )


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
