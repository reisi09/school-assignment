# stats.py
# 기록 목록을 세어 요약하는 함수
# 할 일 화면의 요약·경고와 통계 화면에서 쓴다.
# incidents는 database.get_incidents()가 돌려준 기록 목록이다.

from rules import calc_remaining_score, get_risk_grade


def count_remaining(incident):
    """기록 하나에서 아직 끝내지 않은 할 일의 개수를 센다."""
    remaining = 0

    for action in incident["actions"]:
        if not action["done"]:
            remaining += 1

    return remaining


def count_all_remaining(incidents):
    """여러 기록에 남은 할 일을 모두 더한다."""
    total = 0

    for incident in incidents:
        total += count_remaining(incident)

    return total


def get_remaining_score(incident):
    """기록 하나의 남은 위험 점수를 구한다. 할 일을 끝낼수록 줄어든다."""
    return calc_remaining_score(
        incident["risk_score"],
        count_remaining(incident),
        len(incident["actions"]),
    )


def sum_remaining_scores(incidents):
    """모든 기록의 남은 위험 점수를 더한다."""
    total = 0

    for incident in incidents:
        total += get_remaining_score(incident)

    return total


def get_done_percent(incidents):
    """전체 할 일 중 끝낸 할 일의 비율(%)을 구한다."""
    total = 0

    for incident in incidents:
        total += len(incident["actions"])

    if total == 0:
        return 0

    done = total - count_all_remaining(incidents)

    return round(done / total * 100)


def count_grades(incidents):
    """위험 등급마다 기록이 몇 건인지 센다."""
    counts = {"높음": 0, "보통": 0, "낮음": 0}

    for incident in incidents:
        counts[get_risk_grade(incident["risk_score"])] += 1

    return counts


def count_items(incidents):
    """
    유출된 정보마다 몇 번 유출됐는지 센다.

    (정보 이름, 횟수)를 횟수가 많은 순서로 돌려준다.
    """
    counts = {}

    for incident in incidents:
        for item in incident["leaked_items"]:
            counts[item] = counts.get(item, 0) + 1

    pairs = []

    # counts.get을 기준으로 정렬하면 횟수가 많은 이름부터 나온다.
    for item in sorted(counts, key=counts.get, reverse=True):
        pairs.append((item, counts[item]))

    return pairs


def find_repeated_items(incidents):
    """
    두 곳 이상의 서비스에서 유출된 정보를 찾는다.

    (정보 이름, 서비스 이름 목록)을 유출된 곳이 많은 순서로 돌려준다.
    """
    # 정보 이름마다 그 정보가 유출된 서비스 이름을 모은다.
    places = {}

    for incident in incidents:
        for item in incident["leaked_items"]:
            if item not in places:
                places[item] = []

            if incident["service_name"] not in places[item]:
                places[item].append(incident["service_name"])

    # 두 곳 이상에서 유출된 정보만 남기고, 유출된 곳의 수를 센다.
    counts = {}

    for item, names in places.items():
        if len(names) >= 2:
            counts[item] = len(names)

    repeated = []

    # counts.get을 기준으로 정렬하면 유출된 곳이 많은 정보부터 나온다.
    for item in sorted(counts, key=counts.get, reverse=True):
        repeated.append((item, places[item]))

    return repeated
