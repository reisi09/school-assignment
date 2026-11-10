# api.py
# Pwned Passwords API로 비밀번호가 공개된 유출 목록에 있는지 조회한다.
# 비밀번호 원문과 해시 전체는 보내지 않고, SHA-1 해시 앞 5자리만 보낸다.

import hashlib

import requests

API_URL = "https://api.pwnedpasswords.com/range/"
TIMEOUT_SECONDS = 10


def check_pwned_password(password):
    """
    반환값: (유출 횟수, 상태값)

    SUCCESS       : 조회 성공 (목록에 없으면 횟수 0)
    EMPTY         : 빈 비밀번호 입력
    NETWORK_ERROR : 연결 실패, 시간 초과, 200이 아닌 응답
    DATA_ERROR    : 응답 형식을 읽을 수 없음
    """

    # 빈 입력은 API를 호출하지 않는다.
    if password == "":
        return None, "EMPTY"

    # 해시 40자리를 앞 5자리와 나머지 35자리로 나눈다.
    sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix = sha1[:5]
    suffix = sha1[5:]

    try:
        response = requests.get(API_URL + prefix, timeout=TIMEOUT_SECONDS)
    except requests.RequestException:
        return None, "NETWORK_ERROR"

    if response.status_code != 200:
        return None, "NETWORK_ERROR"

    # 응답은 "나머지 35자리:유출 횟수" 형식의 줄 목록이다.
    # 내 해시의 나머지 35자리와 같은 줄을 앱이 직접 찾는다.
    try:
        for line in response.text.splitlines():
            line_suffix, count = line.split(":")

            if line_suffix == suffix:
                return int(count), "SUCCESS"

    except ValueError:
        return None, "DATA_ERROR"

    return 0, "SUCCESS"
