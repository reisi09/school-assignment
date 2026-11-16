# play.py
# 공격 수법과 문제 자료, 그 자료로 하는 계산
#   해커 시점 체험: 유출된 정보로 공격자가 할 수 있는 일
#   할 일: 할 일을 끝내면 막히는 공격
#   사칭 문자 가려내기: 문자 예시와 정답
# 화면에 나오는 문구는 texts.py에 있다.

# ---------- 해커 시점 체험 ----------

# needs의 정보가 모두 유출됐을 때 할 수 있는 일
# name으로 texts.py의 "attack_이름_title", "attack_이름_body" 문구를 찾는다.
ATTACKS = [
    {"name": "pw", "needs": ["비밀번호"]},
    {"name": "id", "needs": ["아이디"]},
    {"name": "sms", "needs": ["전화번호"]},
    {"name": "call", "needs": ["이름", "전화번호"]},
    {"name": "mail", "needs": ["이메일"]},
    {"name": "birth", "needs": ["이름", "생년월일"]},
    {"name": "address", "needs": ["이름", "주소"]},
    {"name": "account", "needs": ["계좌번호"]},
    {"name": "rrn", "needs": ["주민등록번호"]},
    {"name": "idcard", "needs": ["주민등록번호", "신분증 사본"]},
]


def find_attacks(items):
    """고른 정보로 할 수 있는 일을 찾는다. 필요한 정보를 모두 골랐을 때만 넣는다."""
    found = []

    for attack in ATTACKS:
        ready = True

        for item in attack["needs"]:
            if item not in items:
                ready = False

        if ready:
            found.append(attack)

    return found


# 할 일의 종류(rules.py의 MISSION_TYPES)마다 끝내면 막히는 공격
# 확인만 하는 할 일(lookup, account)은 막는 공격이 없다.
MISSION_BLOCKS = {
    "password": ["pw", "birth"],
    "reuse": ["pw", "id"],
    "otp": ["pw", "id", "birth"],
    "quiz": ["sms", "call", "mail", "address", "account"],
    "fss": ["idcard"],
    "identity": ["rrn"],
}


def find_blocked_attacks(mission_type, items):
    """유출된 정보(items)로 가능한 공격 중에서 이 종류의 할 일을 끝내면 막히는 공격을 찾는다."""
    blocked = []

    for attack in find_attacks(items):
        if attack["name"] in MISSION_BLOCKS.get(mission_type, []):
            blocked.append(attack)

    return blocked


# ---------- 사칭 문자 가려내기 ----------

REAL = "진짜"
FAKE = "사칭"

# 문제 목록. 첫 번째 문제의 문구는 texts.py의 "quiz1_message", "quiz1_reason"이다.
# item은 그 문자와 관련된 유출 정보다. 문자 예시는 모두 연습용으로 만든 가상 문자다.
QUIZ = [
    {"item": "전화번호", "answer": FAKE},      # 1. 보상금을 준다며 링크로 유도
    {"item": "이메일", "answer": REAL},        # 2. 유출된 정보·시점·조치·문의처를 알림
    {"item": "전화번호", "answer": FAKE},      # 3. 앱 설치 요구
    {"item": "비밀번호", "answer": FAKE},      # 4. 링크에서 비밀번호 입력 요구
    {"item": "비밀번호", "answer": REAL},      # 5. 링크 없이 직접 접속해 비밀번호를 새로 정하라는 안내
    {"item": "계좌번호", "answer": FAKE},      # 6. 안전한 계좌로 돈을 옮기라는 요구
    {"item": "주민등록번호", "answer": FAKE},  # 7. 개인 휴대전화 번호로 전화하라는 기관 사칭
    {"item": "이메일", "answer": REAL},        # 8. 홈페이지에 직접 접속해 공지를 보라는 안내
]


def order_quiz(leaked_items):
    """
    문제를 낼 순서를 정한다. QUIZ에서의 위치(0부터)를 목록으로 돌려준다.

    내 기록에서 유출된 정보와 관련된 문제를 앞에 둔다.
    """
    first = []
    rest = []

    for index, question in enumerate(QUIZ):
        if question["item"] in leaked_items:
            first.append(index)
        else:
            rest.append(index)

    return first + rest
