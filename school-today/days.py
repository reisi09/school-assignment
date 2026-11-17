# days.py
# 날짜 계산. 한국 시간(KST)을 쓴다.

from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def today_kst():
    """한국 시간으로 오늘 날짜를 돌려준다."""
    return datetime.now(KST).date()


def now_kst():
    """한국 시간으로 지금 시각을 글자로 돌려준다. 저장할 때 쓴다."""
    return datetime.now(KST).isoformat(timespec="seconds")


def ymd(day):
    """날짜를 나이스 포털이 쓰는 20261117 모양의 글자로 바꾼다."""
    return day.strftime("%Y%m%d")


def from_ymd(text):
    """20261117 모양의 글자를 날짜로 바꾼다."""
    return datetime.strptime(text, "%Y%m%d").date()


def monday_of(day):
    """그 날짜가 들어 있는 주의 월요일을 돌려준다. weekday()는 월요일이 0이다."""
    return day - timedelta(days=day.weekday())


def school_days(monday):
    """월요일부터 금요일까지 닷새의 날짜 목록을 돌려준다."""
    days = []

    for number in range(5):
        days.append(monday + timedelta(days=number))

    return days


def d_day(target, today):
    """target까지 남은 날 수. 오늘이면 0, 지났으면 음수다."""
    return (target - today).days


def first_of_month(day):
    """그달 1일을 돌려준다."""
    return date(day.year, day.month, 1)


def add_months(day, count):
    """그달 1일에서 count달 뒤(음수면 앞)의 1일을 돌려준다."""
    month_index = day.year * 12 + (day.month - 1) + count

    return date(month_index // 12, month_index % 12 + 1, 1)


def last_of_month(day):
    """그달 마지막 날을 돌려준다. 다음 달 1일의 하루 전이다."""
    return add_months(first_of_month(day), 1) - timedelta(days=1)


def find_crowded_weeks(events, kind, minimum=3):
    """
    한 주에 kind 종류의 일정이 minimum개 이상 몰린 주를 찾는다.

    events는 database.get_events()가 돌려준 일정 목록이다.
    반환값: (그 주 월요일, 일정 수) 목록. 이른 주부터 놓는다.
    """
    counts = {}

    for event in events:
        if event["kind"] == kind:
            monday = monday_of(event["due_date"])
            counts[monday] = counts.get(monday, 0) + 1

    crowded = []

    for monday in sorted(counts):
        if counts[monday] >= minimum:
            crowded.append((monday, counts[monday]))

    return crowded
