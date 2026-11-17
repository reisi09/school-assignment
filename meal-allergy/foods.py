# foods.py
# 급식 자료를 읽는다. 나이스 포털의 급식은 아래처럼 한 글자 덩어리로 온다.
#   메뉴: "쌀밥 <br/>쇠고기콩나물국 (5.6.16)<br/>배추김치 (9)"
#   영양: "탄수화물(g) : 162.3<br/>단백질(g) : 51.1"
# 메뉴 이름 뒤 괄호 숫자는 알레르기 유발 식품 번호다(전국 공통 1~19번).

import re

# 학교 급식의 알레르기 유발 식품 번호
ALLERGENS = {
    1: "난류",
    2: "우유",
    3: "메밀",
    4: "땅콩",
    5: "대두",
    6: "밀",
    7: "고등어",
    8: "게",
    9: "새우",
    10: "돼지고기",
    11: "복숭아",
    12: "토마토",
    13: "아황산류",
    14: "호두",
    15: "닭고기",
    16: "쇠고기",
    17: "오징어",
    18: "조개류",
    19: "잣",
}

# 메뉴 끝의 "(5.6.16)" 부분을 찾는 규칙. 괄호 안에는 숫자와 점만 있다.
CODES_AT_END = re.compile(r"\(([0-9.]+)\)\s*$")


def split_lines(text):
    """<br/>로 나뉜 글자를 줄 목록으로 바꾼다. 빈 줄은 뺀다."""
    lines = []

    for line in (text or "").split("<br/>"):
        line = line.strip()

        if line != "":
            lines.append(line)

    return lines


def parse_dish(line):
    """
    메뉴 한 줄을 이름과 알레르기 번호 목록으로 나눈다.

    예: "김치함박스테이크(수제) (2.5.6)" → ("김치함박스테이크(수제)", [2, 5, 6])
    """
    match = CODES_AT_END.search(line)

    if match is None:
        return line, []

    codes = []

    for part in match.group(1).split("."):
        if part != "":
            codes.append(int(part))

    name = line[: match.start()].strip()

    return name, codes


def parse_dishes(text):
    """급식 메뉴 글자 전체를 (이름, 알레르기 번호 목록) 목록으로 바꾼다."""
    dishes = []

    for line in split_lines(text):
        dishes.append(parse_dish(line))

    return dishes


def parse_pairs(text):
    """
    "이름 : 값" 줄들을 (이름, 값) 목록으로 바꾼다. 영양 정보와 원산지에 쓴다.

    예: "탄수화물(g) : 162.3" → ("탄수화물(g)", "162.3")
    """
    pairs = []

    for line in split_lines(text):
        if " : " in line:
            name, value = line.split(" : ", 1)
            pairs.append((name.strip(), value.strip()))

    return pairs


def parse_kcal(text):
    """"2014.8 Kcal"에서 숫자만 꺼낸다. 숫자가 없으면 0이다."""
    match = re.search(r"[0-9.]+", text or "")

    if match is None:
        return 0

    return float(match.group())


def find_my_allergens(codes, my_codes):
    """메뉴의 알레르기 번호 중 내 알레르기 번호를 골라 이름 목록으로 돌려준다."""
    names = []

    for code in codes:
        if code in my_codes:
            names.append(ALLERGENS.get(code, str(code)))

    return names


def find_watch_words(name, words):
    """메뉴 이름에 들어 있는 주의 낱말을 찾는다. 띄어쓰기는 빼고 비교한다. 예: '아몬드 쿠키'에서 '아몬드'"""
    plain = name.replace(" ", "")
    found = []

    for word in words:
        if word.replace(" ", "") in plain:
            found.append(word)

    return found


def count_risky_dishes(dishes, my_codes):
    """메뉴 목록에서 내 알레르기 식품이 든 메뉴의 수를 센다."""
    count = 0

    for name, codes in dishes:
        if len(find_my_allergens(codes, my_codes)) > 0:
            count += 1

    return count
