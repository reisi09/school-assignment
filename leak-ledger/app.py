import html
from pathlib import Path

import streamlit as st

from api import check_pwned_password
from cases import CASE_SOURCE, REAL_CASES
from database import (
    add_case,
    add_incident,
    add_service,
    create_tables,
    get_incidents,
    get_services,
    save_actions,
    save_pwned_count,
    today_kst,
)
from rules import (
    ITEM_WEIGHTS,
    calc_risk_score,
    get_risk_grade,
    make_actions,
    update_action_states,
)

CATEGORIES = ["금융", "쇼핑", "교육", "게임", "기타"]

# 메뉴 이름 앞에 붙이는 아이콘과 화면 설명
MENU_ICONS = {
    "서비스 등록": ":material/apps:",
    "유출 기록": ":material/edit_note:",
    "대응 현황": ":material/checklist:",
    "내 기록 검색": ":material/search:",
}
MENU_INTROS = {
    "서비스 등록": "가입한 서비스를 적어 두면 유출 통지를 받았을 때 바로 기록할 수 있습니다.",
    "유출 기록": "통지받은 내용을 기록하면 위험 점수와 해야 할 조치를 정리해 줍니다.",
    "대응 현황": "남은 조치를 확인하고, 끝낸 조치는 체크해 두세요.",
    "내 기록 검색": "서비스 이름, 분류, 대응 상태로 기록을 다시 찾습니다.",
}

# 위험 등급을 표시할 때 쓰는 파스텔 색 이름 (style.css의 pill-*)
GRADE_TONES = {"높음": "rose", "보통": "butter", "낮음": "mint"}


# ---------- 화면 조각을 만드는 함수 ----------
# 사용자가 입력한 글자는 esc()로 바꿔서 넣는다.
# 그대로 넣으면 입력한 글자가 HTML 태그로 동작할 수 있기 때문이다.


def esc(text):
    """글자를 HTML에 안전하게 넣을 수 있도록 바꾼다."""
    return html.escape(str(text))


def pill(text, tone):
    """알약 모양 표시를 만든다. tone은 aqua, mint, butter, rose, sky, gray 중 하나."""
    return f'<span class="pill pill-{tone}">{esc(text)}</span>'


def spec_row(label, value):
    """이름은 왼쪽, 값은 오른쪽에 두는 한 줄을 만든다. value는 HTML이다."""
    return f'<div class="spec"><span>{esc(label)}</span><strong>{value}</strong></div>'


def risk_pill(score):
    """위험 등급과 점수를 알약 모양으로 만든다."""
    grade = get_risk_grade(score)
    return pill(f"위험 {grade} · {score}점", GRADE_TONES[grade])


def item_pills(items):
    """유출 항목을 알약 모양으로 나열한다."""
    return " ".join(pill(item, "gray") for item in items)


def show_hero(title, intro):
    """화면 맨 위의 제목 영역을 보여 준다."""
    st.html(f'<div class="hero"><h1>{esc(title)}</h1><p>{esc(intro)}</p></div>')


def show_stats(stats):
    """숫자 요약 카드를 한 줄로 보여 준다. stats는 (이름, 값, 색 이름) 목록이다."""
    cards = ""

    for label, value, tone in stats:
        cards += (
            f'<div class="stat"><span><i class="tone-{tone}"></i>{esc(label)}</span>'
            f"<strong>{esc(value)}</strong></div>"
        )

    st.html(f'<div class="stats">{cards}</div>')


def show_empty(message):
    """아직 내용이 없는 자리에 안내 문장을 보여 준다."""
    st.html(f'<div class="empty">{esc(message)}</div>')


# ---------- 계산을 돕는 함수 ----------


def count_remaining(incident):
    """아직 끝내지 않은 조치의 개수를 센다."""
    remaining = 0

    for action in incident["actions"]:
        if not action["done"]:
            remaining += 1

    return remaining


def incident_label(incident):
    """기록끼리 구분되도록 서비스, 통지일, 유출 항목을 함께 적는다."""
    items = ", ".join(incident["leaked_items"])
    return f"{incident['service_name']} · {incident['notified_date']} 통지 ({items})"


def leak_size_text(size):
    """유출 규모를 글자로 바꾼다. 0은 모른다는 뜻이다."""
    if size == 0:
        return "모름"

    return f"{size:,}건"


def pwned_text(count):
    """비밀번호 유출 목록 조회 결과를 글자로 바꾼다."""
    if count is None:
        return "조회 전"

    if count == 0:
        return "목록에 없음"

    return f"{count:,}번 발견"


def incident_summary(incident):
    """유출 기록 한 건의 머리글과 주요 정보를 HTML로 만든다."""
    total = len(incident["actions"])
    done = total - count_remaining(incident)

    if incident["resolved"]:
        state = pill("대응 완료", "mint")
    else:
        state = pill("진행 중", "sky")

    percent = 0

    if total > 0:
        percent = round(done / total * 100)

    return (
        '<div class="card-head">'
        f'<span class="card-title">{esc(incident["service_name"])}</span>'
        f"{risk_pill(incident['risk_score'])}{state}"
        "</div>"
        + spec_row("통지일", esc(incident["notified_date"]))
        + spec_row("유출 항목", item_pills(incident["leaked_items"]))
        + spec_row("유출 규모", esc(leak_size_text(incident["leak_size"])))
        + spec_row("비밀번호 유출 조회", esc(pwned_text(incident["pwned_count"])))
        + spec_row("끝낸 조치", f"{done} / {total}")
        + f'<div class="progress"><div style="width: {percent}%"></div></div>'
    )


def save_checked_actions(incident):
    """체크 상자를 누르면 그 기록의 조치 상태를 바로 저장한다."""
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
st.set_page_config(page_title="유출장부", layout="wide")

# 카드, 알약 모양 표시 같은 화면 모양을 정하는 CSS
st.html(Path(__file__).resolve().parent / "style.css")

create_tables()

st.sidebar.html('<div class="brand"><span class="brand-mark"></span>유출장부</div>')
st.sidebar.caption("가입한 서비스의 개인정보 유출 통지와 대응 조치를 기록합니다.")

menu = st.sidebar.radio(
    "메뉴",
    list(MENU_ICONS),
    format_func=lambda name: f"{MENU_ICONS[name]} {name}",
)

show_hero(menu, MENU_INTROS[menu])

# 저장 후 화면을 새로 그린 다음에 보여 줄 안내
# notice는 잘된 일, alert는 조심해야 할 일을 알린다.
if "notice" in st.session_state:
    st.success(st.session_state.pop("notice"))

if "alert" in st.session_state:
    st.error(st.session_state.pop("alert"))


# 2. 서비스 등록
if menu == "서비스 등록":
    # 등록에 성공한 다음 실행에서만 입력칸을 비운다.
    # 입력이 잘못됐을 때는 적어 둔 내용을 그대로 둔다.
    if st.session_state.pop("clear_service_form", False):
        st.session_state["service_name"] = ""
        st.session_state["service_account"] = ""
        st.session_state["service_memo"] = ""

    left, right = st.columns([5, 6], gap="large")

    with left:
        st.header("새 서비스", anchor=False)

        with st.form("service_form"):
            name = st.text_input("서비스 이름", key="service_name")
            category = st.selectbox("분류", CATEGORIES)
            account_label = st.text_input("계정 별칭 (선택)", key="service_account")
            st.caption(
                "어느 계정으로 가입했는지 구분하는 이름입니다. 예: 학교 메일 계정. "
                "실제 아이디·이메일·비밀번호는 적지 않습니다."
            )
            memo = st.text_input("메모 (선택)", key="service_memo")
            submitted = st.form_submit_button("서비스 등록", type="primary")

        if submitted:
            status = add_service(name, category, account_label, memo)

            if status == "SUCCESS":
                st.session_state["notice"] = f"'{name.strip()}' 서비스를 등록했습니다."
                st.session_state["clear_service_form"] = True
                st.rerun()

            elif status == "EMPTY":
                st.warning("서비스 이름을 입력하세요.")

            else:
                st.warning(
                    "같은 이름의 서비스가 이미 등록되어 있습니다. "
                    "다른 이름으로 등록하세요."
                )

    with right:
        services = get_services()

        st.header(f"등록된 서비스 {len(services)}개", anchor=False)

        if len(services) == 0:
            show_empty("등록된 서비스가 없습니다. 왼쪽에서 가입한 서비스를 먼저 등록하세요.")
        else:
            # 서비스마다 유출 기록이 몇 건인지 센다.
            incident_counts = {}

            for incident in get_incidents():
                service_id = incident["service_id"]
                incident_counts[service_id] = incident_counts.get(service_id, 0) + 1

            cards = ""

            for service in services:
                count = incident_counts.get(service["id"], 0)

                cards += (
                    '<div class="card"><div class="card-head">'
                    f'<span class="card-title">{esc(service["name"])}</span>'
                    f"{pill(service['category'], 'aqua')}"
                    "</div>"
                    + spec_row("계정 별칭", esc(service["account_label"] or "-"))
                    + spec_row("메모", esc(service["memo"] or "-"))
                    + spec_row("유출 기록", f"{count}건")
                    + "</div>"
                )

            st.html(cards)


# 3. 유출 기록
elif menu == "유출 기록":
    services = get_services()
    left, right = st.columns([5, 6], gap="large")

    with left:
        st.header("통지받은 내용 기록", anchor=False)

        if len(services) == 0:
            show_empty(
                "등록된 서비스가 없습니다. '서비스 등록'에서 먼저 등록하거나, "
                "오른쪽의 실제 사례로 기록을 만들어 보세요."
            )
        else:
            today = today_kst()

            # 선택 상자에는 서비스 번호를 넣고, 화면에는 이름을 보여 준다.
            service_names = {}

            for service in services:
                service_names[service["id"]] = service["name"]

            with st.form("incident_form", clear_on_submit=True):
                service_id = st.selectbox(
                    "서비스",
                    options=list(service_names),
                    format_func=lambda service_id: service_names[service_id],
                )
                notified_date = st.date_input(
                    "통지일",
                    value=today,
                    max_value=today,
                    format="YYYY-MM-DD",
                )
                selected_items = st.multiselect(
                    "유출 항목",
                    list(ITEM_WEIGHTS),
                    placeholder="통지문에 적힌 항목을 고르세요",
                    select_all=False,
                )
                other_items = st.text_input("기타 항목 (선택)")
                st.caption(
                    "위 목록에 없는 항목은 쉼표로 구분해 적습니다. "
                    "점수는 매기지 않고 '직접 확인 필요'로 표시합니다."
                )
                leak_size = st.number_input("유출 규모(건)", min_value=0, step=1)
                st.caption("통지문이나 공지에 적힌 전체 건수입니다. 모르면 0으로 둡니다.")
                submitted = st.form_submit_button("기록 저장", type="primary")

            if submitted:
                items = list(selected_items)

                for item in other_items.split(","):
                    item = item.strip()

                    if item != "" and item not in items:
                        items.append(item)

                status = add_incident(service_id, notified_date, items, leak_size)

                if status == "SUCCESS":
                    st.success(
                        f"'{service_names[service_id]}' 유출 기록을 저장했습니다. "
                        "권장 조치는 '대응 현황'에서 하나씩 체크할 수 있습니다."
                    )

                    actions = ""

                    for action in make_actions(items):
                        actions += f"<li>{esc(action)}</li>"

                    st.html(
                        '<div class="card"><div class="card-head">'
                        '<span class="card-title">권장 조치</span>'
                        f"{risk_pill(calc_risk_score(items))}</div>"
                        f'<ul class="todo">{actions}</ul></div>'
                    )

                elif status == "NO_ITEMS":
                    st.warning("유출 항목을 하나 이상 고르거나 기타 항목에 적으세요.")

                else:
                    st.warning("통지일은 오늘까지만 지정할 수 있습니다.")

        with st.expander("위험 점수 기준"):
            st.write(
                "유출 항목별 가중치를 더한 값입니다. "
                "대응 순서를 정하기 위한 앱 자체 기준이며 공식 위험 등급이 아닙니다."
            )

            weight_table = []

            for item, weight in ITEM_WEIGHTS.items():
                weight_table.append({"유출 항목": item, "가중치(점)": weight})

            st.dataframe(weight_table, width="stretch", hide_index=True)
            st.write("등급: 0~3점 낮음, 4~7점 보통, 8점 이상 높음")

    with right:
        # 실제로 보도된 사례를 눌러서 기록을 만들어 볼 수 있다.
        st.header("실제 사례로 기록 만들기", anchor=False)
        st.caption(
            f"출처: [{CASE_SOURCE['title']}]({CASE_SOURCE['url']}). "
            "기사에 적힌 내용만 옮겼습니다."
        )

        registered_names = [service["name"] for service in services]

        for index, case in enumerate(REAL_CASES):
            score = calc_risk_score(case["items"])

            with st.container(key=f"card_case_{index}"):
                st.html(
                    '<div class="card-head">'
                    f'<span class="card-title">{esc(case["name"])}</span>'
                    f"{risk_pill(score)}{pill(case['category'], 'aqua')}"
                    "</div>"
                    f'<p class="card-note">{esc(case["note"])}</p>'
                    + spec_row(
                        "발표일",
                        esc(case["date"] or "기사에 없음 (오늘 날짜로 기록)"),
                    )
                    + spec_row("유출 규모", esc(leak_size_text(case["size"])))
                    + spec_row("유출 항목", item_pills(case["items"]))
                )

                if case["name"] in registered_names:
                    st.caption("이미 기록한 사례입니다. '대응 현황'에서 확인하세요.")
                elif st.button("이 사례로 기록 만들기", key=f"case_button_{index}"):
                    add_case(case)
                    st.session_state["notice"] = (
                        f"'{case['name']}' 사례를 서비스와 유출 기록으로 등록했습니다. "
                        "'대응 현황'에서 조치를 확인하세요."
                    )
                    st.rerun()


# 4. 대응 현황
elif menu == "대응 현황":
    incidents = get_incidents()

    # 4-1. 숫자 요약
    open_incidents = [item for item in incidents if not item["resolved"]]
    remaining_total = 0
    high_count = 0

    for item in open_incidents:
        remaining_total += count_remaining(item)

        if get_risk_grade(item["risk_score"]) == "높음":
            high_count += 1

    show_stats(
        [
            ("남은 조치", f"{remaining_total}개", "aqua"),
            ("진행 중인 기록", f"{len(open_incidents)}건", "sky"),
            ("위험 등급 높음", f"{high_count}건", "rose"),
            ("대응 완료", f"{len(incidents) - len(open_incidents)}건", "mint"),
        ]
    )

    if len(incidents) == 0:
        show_empty(
            "저장된 유출 기록이 없습니다. '유출 기록'에서 통지받은 내용을 먼저 기록하세요."
        )
    else:
        left, right = st.columns([6, 5], gap="large")

        with left:
            # 4-2. 기록마다 조치를 체크한다 (누르는 즉시 저장된다).
            st.header("기록별 조치", anchor=False)
            st.caption("위험 점수가 높은 기록부터 보여 줍니다. 체크하면 바로 저장됩니다.")

            for incident in incidents:
                with st.container(key=f"card_incident_{incident['id']}"):
                    st.html(incident_summary(incident))

                    for index, action in enumerate(incident["actions"]):
                        label = action["name"]

                        if action["done"]:
                            label += f" (완료일 {action['done_date']})"

                        st.checkbox(
                            label,
                            value=action["done"],
                            key=f"action_{incident['id']}_{index}",
                            on_change=save_checked_actions,
                            args=(incident,),
                        )

        with right:
            # 4-3. 비밀번호 유출 목록 조회
            st.header("비밀번호 유출 목록 조회", anchor=False)

            # 선택 상자에는 기록 번호를 넣는다. 기록 내용을 통째로 넣으면
            # 저장한 뒤에도 예전 내용이 남아 있을 수 있다.
            incident_by_id = {}

            for item in incidents:
                incident_by_id[item["id"]] = item

            with st.form("pwned_form", clear_on_submit=True):
                incident_id = st.selectbox(
                    "어느 기록의 비밀번호인가요?",
                    options=sorted(incident_by_id),
                    format_func=lambda incident_id: incident_label(
                        incident_by_id[incident_id]
                    ),
                )
                password = st.text_input("비밀번호", type="password")
                st.caption(
                    "비밀번호는 저장하지 않습니다. 조회할 때는 되돌릴 수 없는 값(SHA-1 해시)으로 "
                    "바꾼 뒤 앞 5자리만 외부로 보냅니다."
                )
                submitted = st.form_submit_button("유출 목록 조회", type="primary")

            st.warning(
                "이 앱은 학교 과제로 만든 시연용입니다. "
                "실제로 쓰는 비밀번호는 넣지 말고 시연용 비밀번호로만 확인하세요."
            )

            if submitted:
                with st.spinner("유출 목록을 조회하고 있습니다..."):
                    count, status = check_pwned_password(password)

                if status == "SUCCESS":
                    # 결과는 횟수만 저장하고, 화면은 저장된 값으로 다시 그린다.
                    save_pwned_count(incident_id, count)
                    name = incident_by_id[incident_id]["service_name"]

                    if count > 0:
                        st.session_state["alert"] = (
                            f"'{name}' 기록의 비밀번호는 공개된 유출 목록에서 {count:,}번 "
                            "발견됐습니다. 이 비밀번호를 쓰는 서비스는 모두 바꾸세요."
                        )
                    else:
                        st.session_state["notice"] = (
                            f"'{name}' 기록의 비밀번호는 공개된 유출 목록에 없습니다. "
                            "목록에 없다는 뜻일 뿐 안전하다는 보장은 아닙니다."
                        )

                    st.rerun()

                elif status == "EMPTY":
                    st.warning("비밀번호를 입력하세요.")

                elif status == "NETWORK_ERROR":
                    st.error(
                        "유출 목록 서버에 연결하지 못했습니다. "
                        "저장된 기록은 그대로입니다. 잠시 뒤 다시 조회하세요."
                    )

                else:
                    st.error(
                        "유출 목록 서버의 응답을 읽지 못했습니다. "
                        "저장된 기록은 그대로입니다. 잠시 뒤 다시 조회하세요."
                    )

            # 4-4. 신고·상담 경로
            st.header("신고·상담 경로", anchor=False)
            st.html(
                '<div class="card">'
                + spec_row(
                    "계정정보 유출 조회",
                    '<a href="https://kidc.eprivacy.go.kr" target="_blank">털린 내 정보 찾기</a>',
                )
                + spec_row("개인정보 침해 신고·상담", "국번 없이 118")
                + spec_row("보이스피싱·스미싱 신고·상담", "국번 없이 1394")
                + spec_row(
                    "명의도용 금융거래 예방",
                    '<a href="https://pd.fss.or.kr" target="_blank">개인정보노출자 사고예방시스템</a>',
                )
                + spec_row(
                    "명의도용 휴대전화 개통 확인",
                    '<a href="https://www.msafer.or.kr" target="_blank">엠세이퍼</a>',
                )
                + "</div>"
            )


# 5. 내 기록 검색
elif menu == "내 기록 검색":
    # 검색 버튼을 눌러야 조건이 적용된다.
    with st.form("search_form"):
        first, second, third = st.columns([4, 2, 3])
        keyword = first.text_input("서비스 이름")
        category = second.selectbox("분류", ["전체"] + CATEGORIES)
        status = third.segmented_control(
            "대응 상태",
            ["전체", "진행 중", "완료"],
            default="전체",
        )
        st.form_submit_button("검색", type="primary")

    # 고른 상태를 다시 눌러 선택을 풀면 전체로 본다.
    if status is None:
        status = "전체"

    incidents = get_incidents(keyword, category, status)
    services = get_services(keyword, category)

    left, right = st.columns([6, 5], gap="large")

    with left:
        st.header(f"유출 기록 {len(incidents)}건", anchor=False)

        if len(incidents) == 0:
            show_empty(
                "조건에 맞는 유출 기록이 없습니다. "
                "검색어를 지우거나 분류와 대응 상태를 '전체'로 바꿔 보세요."
            )
        else:
            cards = ""

            for incident in incidents:
                todo = ""

                for action in incident["actions"]:
                    if not action["done"]:
                        todo += f"<li>{esc(action['name'])}</li>"

                if todo != "":
                    todo = f'<ul class="todo">{todo}</ul>'

                cards += f'<div class="card">{incident_summary(incident)}{todo}</div>'

            st.html(cards)

    with right:
        st.header(f"서비스 {len(services)}개", anchor=False)

        if len(services) == 0:
            show_empty("조건에 맞는 서비스가 없습니다.")
        else:
            cards = ""

            for service in services:
                cards += (
                    '<div class="card"><div class="card-head">'
                    f'<span class="card-title">{esc(service["name"])}</span>'
                    f"{pill(service['category'], 'aqua')}"
                    "</div>"
                    + spec_row("계정 별칭", esc(service["account_label"] or "-"))
                    + spec_row("메모", esc(service["memo"] or "-"))
                    + "</div>"
                )

            st.html(cards)
