# rules.py
# 유출된 정보로 위험 점수와 할 일을 정하는 규칙
# 점수는 할 일의 순서를 정하기 위한 앱 자체 기준이며 공식 위험 등급이 아니다.

import math
import string

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

# 알림문에서 유출된 정보를 찾을 때 쓰는 낱말
# 회사마다 부르는 이름이 달라서 정보 하나에 낱말을 여러 개 둔다.
ITEM_KEYWORDS = {
    "이름": ["이름", "성명"],
    "아이디": ["아이디", "ID"],
    "전화번호": ["전화번호", "휴대폰", "휴대전화", "핸드폰"],
    "이메일": ["메일"],
    "주소": ["주소"],
    "생년월일": ["생년월일", "생일"],
    "비밀번호": ["비밀번호", "패스워드"],
    "계좌번호": ["계좌"],
    "주민등록번호": ["주민등록번호", "주민번호"],
    "신분증 사본": ["신분증"],
}

# 집 주소가 아닌데 "주소"라는 글자가 들어가는 말
NOT_HOME_ADDRESS = ["메일 주소", "메일주소", "홈페이지 주소", "인터넷 주소", "IP 주소", "IP주소"]

# 이 낱말이 들어간 부분은 유출된 정보를 말하는 곳이 아니라고 보고 건너뛴다.
# 예: "비밀번호는 유출되지 않았습니다", "비밀번호를 변경해 주세요", "문의: 고객센터 전화번호"
SKIP_WORDS = ["않", "없", "아닙", "안전", "변경", "바꾸", "바꿔", "문의", "고객센터", "상담"]


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


def calc_remaining_score(score, remaining, total):
    """
    남은 할 일의 비율만큼 위험 점수를 남긴다.

    예: 6점짜리 기록의 할 일 4개 중 2개가 남았으면 3점이다.
    소수점은 올림해서, 할 일을 모두 끝내야 0점이 된다.
    """
    if total == 0:
        return 0

    return math.ceil(score * remaining / total)


def find_items_in_text(text):
    """
    붙여넣은 알림문에서 유출된 정보를 찾아 목록으로 돌려준다.

    낱말이 들어 있는지만 보는 단순한 방법이라 틀릴 수 있다.
    그래서 화면에서는 찾은 결과를 사용자가 확인하고 고치게 한다.
    """
    # "이메일 주소"의 "주소"를 집 주소로 읽지 않도록 "주소" 글자를 뺀다.
    for phrase in NOT_HOME_ADDRESS:
        text = text.replace(phrase, phrase.replace("주소", ""))

    # 줄바꿈과 "~며", "~지만", "~으나"에서 끊어 짧은 부분으로 나눈다.
    for mark in ["\n", "며 ", "지만 ", "으나 "]:
        text = text.replace(mark, ".")

    found = []

    for part in text.split("."):
        skip = False

        for word in SKIP_WORDS:
            if word in part:
                skip = True

        if skip:
            continue

        for item, keywords in ITEM_KEYWORDS.items():
            for keyword in keywords:
                if keyword in part and item not in found:
                    found.append(item)

    # 점수 목록과 같은 순서로 돌려준다.
    ordered = []

    for item in ITEM_WEIGHTS:
        if item in found:
            ordered.append(item)

    return ordered


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


# 할 일마다 '해 보기' 창의 종류를 정한다. screen_missions.py가 종류에 맞는 창을 연다.
# 목록에 없는 할 일(직접 확인하기: ...)은 "note"다.
MISSION_TYPES = {
    TEXT["act_pw_change"]: "password",
    TEXT["act_pw_other"]: "reuse",
    TEXT["act_2fa"]: "otp",
    TEXT["act_phishing"]: "quiz",
    TEXT["act_account"]: "account",
    TEXT["act_fss"]: "fss",
    TEXT["act_identity"]: "identity",
    TEXT["act_lookup"]: "lookup",
}


def get_mission_type(action_name):
    """할 일 이름으로 '해 보기' 창의 종류를 찾는다."""
    return MISSION_TYPES.get(action_name, "note")


def finish_action(actions, index, result, today):
    """
    할 일 하나(index번째)를 끝낸 상태로 바꾼 새 목록을 돌려준다.

    result는 해 보기 창에서 나온 결과 한 줄이고, today는 끝낸 날짜다.
    """
    updated = []

    for position, action in enumerate(actions):
        if position == index:
            action = {
                "name": action["name"],
                "done": True,
                "done_date": today,
                "result": result,
            }

        updated.append(action)

    return updated


def undo_action(actions, index):
    """끝낸 할 일 하나(index번째)를 다시 안 끝낸 상태로 바꾼 새 목록을 돌려준다."""
    updated = []

    for position, action in enumerate(actions):
        if position == index:
            action = {"name": action["name"], "done": False, "done_date": None, "result": None}

        updated.append(action)

    return updated


def count_char_kinds(password):
    """
    비밀번호에 섞인 문자 종류(영문 대문자, 영문 소문자, 숫자, 특수문자)의 수를 센다.

    특수문자는 키보드의 기호(string.punctuation)만 센다. 한글과 띄어쓰기는 세지 않는다.
    """
    has_upper = False
    has_lower = False
    has_digit = False
    has_symbol = False

    for char in password:
        if "A" <= char <= "Z":
            has_upper = True
        elif "a" <= char <= "z":
            has_lower = True
        elif "0" <= char <= "9":
            has_digit = True
        elif char in string.punctuation:
            has_symbol = True

    # True는 1, False는 0으로 더해진다.
    return has_upper + has_lower + has_digit + has_symbol


def is_strong_password(password):
    """
    한국인터넷진흥원(KISA) 안내 기준을 지키는지 확인한다.

    문자 종류를 3가지 이상 섞으면 8자 이상, 2가지 이상 섞으면 10자 이상이어야 한다.
    """
    kinds = count_char_kinds(password)

    if kinds >= 3 and len(password) >= 8:
        return True

    if kinds >= 2 and len(password) >= 10:
        return True

    return False
