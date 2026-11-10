# rules.py
# 유출된 정보로 위험 점수와 할 일을 정하는 규칙
# 점수는 할 일의 순서를 정하기 위한 앱 자체 기준이며 공식 위험 등급이 아니다.

from texts import TEXT

# 유출된 정보마다 매기는 점수
# 금융거래나 본인확인에 쓰일 수 있는 정보일수록 높게 잡았다.
ITEM_WEIGHTS = {
    "이름": 1,
    "아이디": 1,
    "전화번호": 1,
    "이메일": 1,
    "주소": 1,
    "생년월일": 1,
    "비밀번호": 3,
    "계좌번호": 3,
    "주민등록번호": 5,
    "신분증 사본": 5,
}


def calc_risk_score(items):
    """유출된 정보의 점수를 모두 더한다. 목록에 없는 정보는 0점이다."""
    score = 0

    for item in items:
        score += ITEM_WEIGHTS.get(item, 0)

    return score


def get_risk_grade(score):
    """위험 점수를 낮음(0~3), 보통(4~7), 높음(8 이상)으로 나눈다."""
    if score >= 8:
        return "높음"

    if score >= 4:
        return "보통"

    return "낮음"


def make_actions(items):
    """유출된 정보에 맞는 할 일 이름 목록을 만든다. 문구는 texts.py에 있다."""
    actions = []

    if "비밀번호" in items:
        actions.append(TEXT["act_pw_change"])
        actions.append(TEXT["act_pw_other"])
        actions.append(TEXT["act_2fa"])

    if "전화번호" in items or "이메일" in items:
        actions.append(TEXT["act_phishing"])

    if "계좌번호" in items:
        actions.append(TEXT["act_account"])

    if "주민등록번호" in items or "신분증 사본" in items:
        actions.append(TEXT["act_fss"])
        actions.append(TEXT["act_identity"])

    # 모든 기록에 공통으로 넣는 할 일
    actions.append(TEXT["act_lookup"])

    # 점수 목록에 없는 정보는 점수를 매기지 않고 직접 확인하게 한다.
    for item in items:
        if item not in ITEM_WEIGHTS:
            actions.append(TEXT["act_unknown"].format(item=item))

    return actions


def update_action_states(actions, done_flags, today):
    """
    체크 결과(done_flags)를 할 일 목록에 반영한다.

    새로 끝낸 일에는 오늘 날짜를 남기고,
    이미 끝낸 일은 처음 끝낸 날짜를 유지하며,
    체크를 푼 일은 날짜를 지운다.
    """
    updated = []

    for action, done in zip(actions, done_flags):
        if not done:
            done_date = None
        elif action["done"]:
            done_date = action["done_date"]
        else:
            done_date = today

        updated.append(
            {
                "name": action["name"],
                "done": done,
                "done_date": done_date,
            }
        )

    return updated
