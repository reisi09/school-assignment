# days.py
# 날짜 계산. 한국 시간(KST)을 쓴다.

from datetime import datetime, timedelta, timezone

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
