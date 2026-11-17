# neis.py
# 나이스 교육정보 개방 포털(open.neis.go.kr)에서 학교 자료를 받아 온다.
#   학교 찾기·기본 정보, 급식, 학사일정, 시간표, 학년별 반 수
#
# 인증키 없이 쓰면 한 번에 5건까지만 준다. 그래서 기간이 길면 일주일씩, 그래도 넘치면 하루씩 나눠 받는다.
# 인증키가 있으면 .streamlit/secrets.toml에 NEIS_KEY = "키" 한 줄을 넣는다. 이 파일은 git에 올리지 않는다.
# 받은 자료는 st.cache_data로 1시간 동안 기억해서, 같은 자료를 다시 요청하지 않는다.

from datetime import timedelta

import requests
import streamlit as st

from days import monday_of, ymd

API_URL = "https://open.neis.go.kr/hub/"

# 인증키 없이 한 번에 받을 수 있는 건수
FREE_LIMIT = 5

# 학교 종류마다 시간표를 주는 곳이 다르다.
TIMETABLE_SERVICES = {
    "초등학교": "elsTimetable",
    "중학교": "misTimetable",
    "고등학교": "hisTimetable",
}


class NeisError(Exception):
    """나이스 포털에 연결하지 못했거나 이상한 답이 왔을 때 내는 오류"""


def get_key():
    """인증키를 돌려준다. secrets 파일이 없거나 키가 없으면 빈 글자다."""
    try:
        return st.secrets.get("NEIS_KEY", "")
    except FileNotFoundError:
        return ""


def has_key():
    """인증키가 있는지 알려 준다. 없으면 한 번에 5건까지만 받는다."""
    return get_key() != ""


def call(service, params):
    """
    나이스 포털에 자료를 한 번 요청한다.

    반환값: (전체 건수, 받은 줄 목록). 자료가 없으면 (0, [])이다.
    연결하지 못하면 NeisError를 낸다.
    """
    query = {"Type": "json", "pIndex": 1, "pSize": FREE_LIMIT}

    if has_key():
        query["KEY"] = get_key()
        query["pSize"] = 1000

    query.update(params)

    try:
        response = requests.get(API_URL + service, params=query, timeout=10)
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        raise NeisError(str(error))

    # 자료가 있으면 service 이름 아래에 [머리, 몸통]이 온다.
    if service in data:
        head, body = data[service]
        total = head["head"][0]["list_total_count"]
        return total, body["row"]

    # 자료가 없으면 RESULT의 CODE가 INFO-200이다. 다른 코드는 요청이 잘못된 것이다.
    if data.get("RESULT", {}).get("CODE") == "INFO-200":
        return 0, []

    raise NeisError(str(data.get("RESULT")))


def call_range(service, params, from_key, to_key, start, end):
    """start부터 end까지의 자료를 한 번에 요청한다. (전체 건수, 받은 줄 목록)을 돌려준다."""
    query = dict(params)
    query[from_key] = ymd(start)
    query[to_key] = ymd(end)

    return call(service, query)


def fetch_range(service, params, keys, start, end):
    """
    start부터 end까지의 자료를 모두 받는다.

    keys는 (시작 날짜 이름, 끝 날짜 이름, 하루 날짜 이름)이다. 예: ("MLSV_FROM_YMD", "MLSV_TO_YMD", "MLSV_YMD")
    한 번에 다 받지 못하면 일주일씩 다시 받고, 그래도 다 못 받은 주는 하루씩 받는다.
    """
    from_key, to_key, day_key = keys

    total, rows = call_range(service, params, from_key, to_key, start, end)

    if len(rows) >= total:
        return rows

    rows = []
    week_start = monday_of(start)

    while week_start <= end:
        # 기간의 처음과 끝이 주 중간이면 그 부분만 받는다.
        first = max(week_start, start)
        last = min(week_start + timedelta(days=6), end)

        total, week_rows = call_range(service, params, from_key, to_key, first, last)

        if len(week_rows) >= total:
            rows += week_rows
        else:
            day = first

            while day <= last:
                query = dict(params)
                query[day_key] = ymd(day)
                rows += call(service, query)[1]
                day += timedelta(days=1)

        week_start += timedelta(days=7)

    return rows


def school_params(school):
    """요청마다 들어가는 학교 코드(교육청 코드, 학교 코드)를 만든다."""
    return {
        "ATPT_OFCDC_SC_CODE": school["atpt_code"],
        "SD_SCHUL_CODE": school["school_code"],
    }


@st.cache_data(ttl=3600, show_spinner=False)
def search_schools(name):
    """
    학교 이름으로 학교를 찾는다.

    반환값: (전체 건수, 학교 목록). 학교마다 이름, 종류, 교육청 코드, 학교 코드, 주소가 있다.
    """
    total, rows = call("schoolInfo", {"SCHUL_NM": name})
    schools = []

    for row in rows:
        schools.append(
            {
                "name": row["SCHUL_NM"],
                "kind": row["SCHUL_KND_SC_NM"],
                "atpt_code": row["ATPT_OFCDC_SC_CODE"],
                "school_code": row["SD_SCHUL_CODE"],
                "address": row["ORG_RDNMA"],
            }
        )

    return total, schools


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_school_info(school):
    """학교 기본 정보(주소, 전화, 홈페이지, 종류, 남녀 구분, 설립 구분)를 받는다."""
    total, rows = call("schoolInfo", school_params(school))

    if total == 0:
        return None

    row = rows[0]

    return {
        "name": row["SCHUL_NM"],
        "address": (row["ORG_RDNMA"] or "") + " " + (row["ORG_RDNDA"] or ""),
        "phone": row["ORG_TELNO"],
        "homepage": row["HMPG_ADRES"],
        "kind": row["SCHUL_KND_SC_NM"],
        "gender": row["COEDU_SC_NM"],
        "found": row["FOND_SC_NM"],
    }


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_meals(school, start, end):
    """
    start부터 end까지의 급식을 받는다.

    반환값: 급식 목록. 급식마다 날짜, 끼니, 메뉴 글자, 열량, 영양, 원산지, 급식 인원이 있다.
    메뉴 글자는 foods.py의 parse_dishes()로 읽는다.
    """
    rows = fetch_range(
        "mealServiceDietInfo",
        school_params(school),
        ("MLSV_FROM_YMD", "MLSV_TO_YMD", "MLSV_YMD"),
        start,
        end,
    )
    meals = []

    for row in rows:
        meals.append(
            {
                "date": row["MLSV_YMD"],
                "meal": row["MMEAL_SC_NM"],
                "dishes": row["DDISH_NM"],
                "kcal": row["CAL_INFO"],
                "nutrition": row["NTR_INFO"],
                "origin": row["ORPLC_INFO"],
                "headcount": row["MLSV_FGR"],
            }
        )

    return meals


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_schedule(school, start, end):
    """
    start부터 end까지의 학사일정을 받는다.

    반환값: 일정 목록. 일정마다 날짜, 행사 이름, 쉬는 날인지, 학년별 해당 여부(1~6학년)가 있다.
    """
    rows = fetch_range(
        "SchoolSchedule",
        school_params(school),
        ("AA_FROM_YMD", "AA_TO_YMD", "AA_YMD"),
        start,
        end,
    )
    events = []

    for row in rows:
        # 학년별 해당 여부. Y면 그 학년 일정이다.
        grades = []
        flags = [
            "ONE_GRADE_EVENT_YN",
            "TW_GRADE_EVENT_YN",
            "THREE_GRADE_EVENT_YN",
            "FR_GRADE_EVENT_YN",
            "FIV_GRADE_EVENT_YN",
            "SIX_GRADE_EVENT_YN",
        ]

        for number, flag in enumerate(flags, start=1):
            if row.get(flag) == "Y":
                grades.append(number)

        events.append(
            {
                "date": row["AA_YMD"],
                "name": row["EVENT_NM"],
                # 수업공제일명이 휴업일·공휴일이면 쉬는 날이다.
                "holiday": row.get("SBTR_DD_SC_NM") in ("휴업일", "공휴일"),
                "grades": grades,
            }
        )

    return events


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_timetable(school, grade, class_nm, start, end):
    """
    start부터 end까지 한 반의 시간표를 받는다.

    반환값: 시간표 목록. 줄마다 날짜, 교시(숫자), 과목이 있다.
    인증키가 없으면 하루에 5교시까지만 받는다.
    """
    service = TIMETABLE_SERVICES.get(school["kind"], "hisTimetable")
    params = school_params(school)
    params["GRADE"] = grade
    params["CLASS_NM"] = class_nm

    rows = fetch_range(
        service,
        params,
        ("TI_FROM_YMD", "TI_TO_YMD", "ALL_TI_YMD"),
        start,
        end,
    )
    lessons = []

    for row in rows:
        lessons.append(
            {
                "date": row["ALL_TI_YMD"],
                "period": int(row["PERIO"]),
                "subject": row["ITRT_CNTNT"],
            }
        )

    return lessons


@st.cache_data(ttl=3600, show_spinner=False)
def count_classes(school, year, grade):
    """그 해 그 학년의 반 수를 센다. 반 목록은 5건까지만 오지만 전체 건수는 정확하다."""
    params = school_params(school)
    params["AY"] = year
    params["GRADE"] = grade

    return call("classInfo", params)[0]
