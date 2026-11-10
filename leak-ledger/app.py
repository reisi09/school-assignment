from pathlib import Path

import streamlit as st

from api import check_pwned_password
from database import (
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

# 위험 등급을 표시할 때 쓰는 색 (높음만 빨간색으로 눈에 띄게 한다)
GRADE_COLORS = {"높음": "red", "보통": "orange", "낮음": "gray"}


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


def show_risk_badge(score):
    """위험 등급과 점수를 색이 있는 표시로 보여 준다."""
    grade = get_risk_grade(score)
    st.badge(f"위험 {grade} · {score}점", color=GRADE_COLORS[grade])


def make_service_table(services):
    """서비스 목록을 화면에 보여 줄 표로 바꾼다."""
    table = []

    for service in services:
        table.append(
            {
                "서비스": service["name"],
                "분류": service["category"],
                "계정 별칭": service["account_label"] or "-",
                "메모": service["memo"] or "-",
            }
        )

    return table


def make_incident_table(incidents):
    """유출 기록 목록을 화면에 보여 줄 표로 바꾼다."""
    table = []

    for incident in incidents:
        score = incident["risk_score"]

        if incident["pwned_count"] is None:
            pwned = "조회 전"
        elif incident["pwned_count"] == 0:
            pwned = "목록에 없음"
        else:
            pwned = f"{incident['pwned_count']:,}번"

        # 좁은 화면에서도 보이도록 위험 등급을 앞쪽에 둔다.
        table.append(
            {
                "서비스": incident["service_name"],
                "위험 등급": get_risk_grade(score),
                "위험 점수": score,
                "남은 조치": count_remaining(incident),
                "대응 상태": "완료" if incident["resolved"] else "진행 중",
                "통지일": incident["notified_date"],
                "유출 항목": ", ".join(incident["leaked_items"]),
                "비밀번호 유출 조회": pwned,
            }
        )

    return table


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
st.set_page_config(page_title="유출장부")

# 글자색 대비와 포커스 표시를 보완하는 CSS
st.html(Path(__file__).resolve().parent / "style.css")

create_tables()

st.sidebar.markdown("**유출장부**")
st.sidebar.caption("가입한 서비스의 개인정보 유출 통지와 대응 조치를 기록합니다.")

menu = st.sidebar.radio(
    "메뉴",
    ["서비스 등록", "유출 기록", "대응 현황", "내 기록 검색"],
)

# 제목 옆의 링크 아이콘은 쓰지 않으므로 anchor=False로 끈다.
st.title(menu, anchor=False)

# 저장 후 화면을 새로 그린 다음에 보여 줄 안내
if "notice" in st.session_state:
    st.success(st.session_state.pop("notice"))


# 2. 서비스 등록
if menu == "서비스 등록":
    # 등록에 성공한 다음 실행에서만 입력칸을 비운다.
    # 입력이 잘못됐을 때는 적어 둔 내용을 그대로 둔다.
    if st.session_state.pop("clear_service_form", False):
        st.session_state["service_name"] = ""
        st.session_state["service_account"] = ""
        st.session_state["service_memo"] = ""

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

    st.header("등록된 서비스", anchor=False)

    services = get_services()

    if len(services) == 0:
        st.info("등록된 서비스가 없습니다. 위에서 가입한 서비스를 먼저 등록하세요.")
    else:
        st.dataframe(make_service_table(services), width="stretch", hide_index=True)


# 3. 유출 기록
elif menu == "유출 기록":
    services = get_services()

    if len(services) == 0:
        st.info("등록된 서비스가 없습니다. '서비스 등록'에서 가입한 서비스를 먼저 등록하세요.")
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
                st.success(f"'{service_names[service_id]}' 유출 기록을 저장했습니다.")
                show_risk_badge(calc_risk_score(items))

                lines = ["권장 조치는 '대응 현황'에서 하나씩 체크할 수 있습니다.", ""]

                for action in make_actions(items):
                    lines.append(f"- {action}")

                st.markdown("\n".join(lines))

            elif status == "NO_ITEMS":
                st.warning("유출 항목을 하나 이상 고르거나 기타 항목에 적으세요.")

            else:
                st.warning("통지일은 오늘까지만 지정할 수 있습니다.")

    # 방금 저장한 기록을 같은 화면에서 확인한다.
    st.header("최근 기록", anchor=False)

    recent = sorted(
        get_incidents(),
        key=lambda incident: incident["id"],
        reverse=True,
    )[:3]

    if len(recent) == 0:
        st.info("저장된 유출 기록이 없습니다.")
    else:
        lines = []

        for incident in recent:
            score = incident["risk_score"]
            lines.append(
                f"- {incident_label(incident)} · "
                f"위험 {get_risk_grade(score)} {score}점 · "
                f"남은 조치 {count_remaining(incident)}개"
            )

        st.markdown("\n".join(lines))

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


# 4. 대응 현황
elif menu == "대응 현황":
    incidents = get_incidents()

    if len(incidents) == 0:
        st.info("저장된 유출 기록이 없습니다. '유출 기록'에서 통지받은 내용을 먼저 기록하세요.")
    else:
        # 4-1. 남은 조치 (위험 점수가 높은 기록부터)
        open_incidents = [item for item in incidents if not item["resolved"]]
        remaining_total = 0
        high_count = 0

        for item in open_incidents:
            remaining_total += count_remaining(item)

            if get_risk_grade(item["risk_score"]) == "높음":
                high_count += 1

        st.header(f"남은 조치 {remaining_total}개", anchor=False)
        st.caption(
            f"진행 중인 기록 {len(open_incidents)}건 · "
            f"위험 등급이 높은 기록 {high_count}건"
        )

        if remaining_total == 0:
            st.info("남은 조치가 없습니다. 모든 기록의 대응을 마쳤습니다.")
        else:
            lines = []

            for item in open_incidents:
                grade = get_risk_grade(item["risk_score"])
                lines.append(
                    f"**{item['service_name']}** · 위험 {grade} · "
                    f"{item['notified_date']} 통지"
                )

                for action in item["actions"]:
                    if not action["done"]:
                        lines.append(f"- {action['name']}")

                lines.append("")

            st.markdown("\n".join(lines))

        # 4-2. 기록 선택
        # 선택 상자에는 기록 번호를 넣는다. 기록 내용을 통째로 넣으면
        # 저장한 뒤에도 예전 내용이 남아 있을 수 있다.
        st.header("기록별 조치 체크", anchor=False)

        incident_by_id = {}

        for item in incidents:
            incident_by_id[item["id"]] = item

        incident_id = st.selectbox(
            "유출 기록",
            options=sorted(incident_by_id),
            format_func=lambda incident_id: incident_label(incident_by_id[incident_id]),
        )
        incident = incident_by_id[incident_id]

        show_risk_badge(incident["risk_score"])

        if incident["leak_size"] == 0:
            leak_size = "모름"
        else:
            leak_size = f"{incident['leak_size']:,}건"

        st.caption(
            f"대응 상태: {'완료' if incident['resolved'] else '진행 중'} · "
            f"유출 규모: {leak_size}"
        )

        # 4-3. 조치 완료 체크 (누르는 즉시 저장된다)
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

        if incident["resolved"]:
            st.success("이 기록의 조치를 모두 끝냈습니다.")
        else:
            st.caption("체크하면 바로 저장됩니다.")

        # 4-4. 비밀번호 유출 목록 조회
        st.header("비밀번호 유출 목록 조회", anchor=False)
        st.write(
            "위에서 고른 서비스에서 쓰던 비밀번호가 이미 공개된 유출 목록에 있는지 확인합니다. "
            "비밀번호는 저장하지 않습니다. 조회할 때는 비밀번호를 되돌릴 수 없는 값(SHA-1 해시)으로 "
            "바꾼 뒤 앞 5자리만 외부로 보냅니다."
        )
        st.warning(
            "이 앱은 학교 과제로 만든 시연용입니다. "
            "실제로 쓰는 비밀번호는 넣지 말고 시연용 비밀번호로만 확인하세요."
        )

        with st.form("pwned_form", clear_on_submit=True):
            password = st.text_input("비밀번호", type="password")
            submitted = st.form_submit_button("유출 목록 조회")

        if submitted:
            with st.spinner("유출 목록을 조회하고 있습니다..."):
                count, status = check_pwned_password(password)

            if status == "SUCCESS":
                # 결과는 횟수만 저장하고, 아래에서 저장된 값을 읽어 보여 준다.
                save_pwned_count(incident["id"], count)
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

        # 이 기록에 저장된 마지막 조회 결과
        if incident["pwned_count"] is None:
            st.caption("이 기록으로는 아직 조회하지 않았습니다.")
        elif incident["pwned_count"] == 0:
            st.info(
                "마지막 조회 결과: 공개된 유출 목록에 없는 비밀번호입니다. "
                "목록에 없다는 뜻일 뿐 안전하다는 보장은 아닙니다."
            )
        else:
            st.error(
                f"마지막 조회 결과: 공개된 유출 목록에서 {incident['pwned_count']:,}번 "
                "발견된 비밀번호입니다. 이 비밀번호를 쓰는 서비스는 모두 바꾸세요."
            )

    # 4-5. 신고·상담 경로
    st.header("신고·상담 경로", anchor=False)
    st.markdown(
        """
- 계정정보 유출 조회: [털린 내 정보 찾기](https://kidc.eprivacy.go.kr)
- 개인정보 침해 신고·상담: 국번 없이 118
- 보이스피싱·스미싱 신고·상담: 국번 없이 1394
- 명의도용 금융거래 예방: [개인정보노출자 사고예방시스템](https://pd.fss.or.kr)
- 명의도용 휴대전화 개통 확인: [엠세이퍼](https://www.msafer.or.kr)
"""
    )


# 5. 내 기록 검색
elif menu == "내 기록 검색":
    # 검색 버튼을 눌러야 조건이 적용된다.
    with st.form("search_form"):
        keyword = st.text_input("서비스 이름")
        left, right = st.columns(2)
        category = left.selectbox("분류", ["전체"] + CATEGORIES)
        status = right.selectbox("대응 상태", ["전체", "진행 중", "완료"])
        st.form_submit_button("검색", type="primary")

    st.header("유출 기록", anchor=False)

    incidents = get_incidents(keyword, category, status)

    if len(incidents) == 0:
        st.info(
            "조건에 맞는 유출 기록이 없습니다. "
            "검색어를 지우거나 분류와 대응 상태를 '전체'로 바꿔 보세요."
        )
    else:
        st.dataframe(
            make_incident_table(incidents),
            width="stretch",
            hide_index=True,
        )

        # 남은 조치는 기록마다 펼쳐서 다시 본다.
        for incident in incidents:
            remaining = count_remaining(incident)

            if remaining == 0:
                continue

            with st.expander(f"{incident_label(incident)} · 남은 조치 {remaining}개"):
                lines = []

                for action in incident["actions"]:
                    if not action["done"]:
                        lines.append(f"- {action['name']}")

                st.markdown("\n".join(lines))

    st.header("서비스", anchor=False)

    services = get_services(keyword, category)

    if len(services) == 0:
        st.info("조건에 맞는 서비스가 없습니다.")
    else:
        st.dataframe(make_service_table(services), width="stretch", hide_index=True)
