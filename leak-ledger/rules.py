# rules.py
# 유출 항목으로 위험 점수와 권장 조치를 정하는 규칙
# 점수는 대응 순서를 정하기 위한 앱 자체 기준이며 공식 위험 등급이 아니다.

# 유출 항목별 가중치
# 금융거래나 본인확인에 쓰일 수 있는 항목일수록 높게 잡았다.
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
    """유출 항목 가중치의 합을 구한다. 목록에 없는 항목은 0점이다."""
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
    """유출 항목에 맞는 권장 조치 이름 목록을 만든다."""
    actions = []

    if "비밀번호" in items:
        actions.append("해당 서비스 비밀번호 변경")
        actions.append("같은 비밀번호를 쓰는 다른 서비스 비밀번호 변경")
        actions.append("2단계 인증 설정")

    if "전화번호" in items or "이메일" in items:
        actions.append("사칭 문자·전화·메일 주의")

    if "계좌번호" in items:
        actions.append("계좌 거래 내역 확인")

    if "주민등록번호" in items or "신분증 사본" in items:
        actions.append("금융감독원 개인정보노출자 사고예방시스템 등록")
        actions.append("명의도용 여부 확인")

    # 모든 유출 기록에 공통으로 넣는 조치
    actions.append("'털린 내 정보 찾기'에서 계정정보 유출 조회")

    # 가중치 목록에 없는 항목은 점수를 매기지 않고 직접 확인하게 한다.
    for item in items:
        if item not in ITEM_WEIGHTS:
            actions.append(f"직접 확인 필요: {item}")

    return actions


def update_action_states(actions, done_flags, today):
    """
    체크 결과(done_flags)를 조치 목록에 반영한다.

    새로 완료한 조치에는 오늘 날짜를 남기고,
    이미 완료한 조치는 처음 완료일을 유지하며,
    체크를 푼 조치는 완료일을 지운다.
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
