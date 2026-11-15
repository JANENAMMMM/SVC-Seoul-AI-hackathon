"""영업시간 문자열 파싱. 모든 시각은 '자정부터의 분'이며 자정을 넘기면 1440을 넘을 수 있다.

반환값은 {요일(0=월): [(시작, 끝), ...]}. 파싱할 수 없으면 None(영업시간 불명).
"""

import re
from collections import Counter

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
KO_DAYS = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}

Intervals = list[tuple[int, int]]
Hours = dict[int, Intervals]


def hhmm_to_min(text: str) -> int:
    h, m = text.split(":")
    return int(h) * 60 + int(m)


def min_to_hhmm(minutes: int) -> str:
    minutes = int(minutes)
    return f"{(minutes // 60) % 24:02d}:{minutes % 60:02d}"


def _to_minutes(hour: int, minute: int, meridiem: str | None) -> int:
    if meridiem == "pm" and hour != 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    return hour * 60 + minute


def _finish(start: int, end: int) -> tuple[int, int]:
    if end <= start:
        end += 1440
    return start, end


_EN_TIME = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.I)


def parse_google_range_text(text: str) -> Intervals | None:
    s = re.sub(r"[  \xa0]", " ", text).replace("–", "-").replace("—", "-").lower().strip()
    if "24 hours" in s:
        return [(0, 1440)]
    if s.startswith("closed") and "-" not in s:
        return []
    result: Intervals = []
    for part in s.split(","):
        pieces = part.strip().split("-")
        if len(pieces) != 2:
            return None
        a, b = _EN_TIME.fullmatch(pieces[0].strip()), _EN_TIME.fullmatch(pieces[1].strip())
        if not a or not b:
            return None
        b_mer = b.group(3)
        end = _to_minutes(int(b.group(1)), int(b.group(2) or 0), b_mer)
        a_mer = a.group(3) or b_mer
        start = _to_minutes(int(a.group(1)), int(a.group(2) or 0), a_mer)
        if not a.group(3) and start > end:
            start -= 720
        result.append(_finish(start, end))
    return result


def parse_google_hours(raw) -> Hours | None:
    """attractions.json의 google.hours. 현재 상태 문구(문자열)면 None."""
    if not isinstance(raw, list):
        return None
    hours: Hours = {}
    for entry in raw:
        for name, text in entry.items():
            if name not in DAY_NAMES:
                continue
            intervals = parse_google_range_text(text)
            if intervals is None:
                return None
            hours[DAY_NAMES.index(name)] = intervals
    return hours or None


_KO_TIME = re.compile(r"(오전|오후)?\s*(\d{1,2}):(\d{2})")
_KO_LINE = re.compile(r"^([월화수목금토일])요일:\s*(.*)$")


def _ko_minutes(hour: int, minute: int, meridiem: str | None) -> int:
    if meridiem == "오후" and hour != 12:
        hour += 12
    if meridiem == "오전" and hour == 12:
        hour = 0
    return hour * 60 + minute


def parse_korean_hours(lines: list[str] | None) -> Hours | None:
    """희윤님 식당 JSON의 opening_text. 비어 있으면 None(영업시간 불명)."""
    if not lines:
        return None
    hours: Hours = {}
    for line in lines:
        m = _KO_LINE.match(line.strip())
        if not m:
            continue
        day, body = KO_DAYS[m.group(1)], m.group(2)
        if "24시간" in body:
            hours[day] = [(0, 1440)]
            continue
        intervals: Intervals = []
        for part in body.split(","):
            sides = part.split("~")
            if len(sides) != 2:
                continue
            a, b = _KO_TIME.search(sides[0]), _KO_TIME.search(sides[1])
            if not a or not b:
                continue
            a_mer = a.group(1)
            b_mer = b.group(1) or a_mer
            start = _ko_minutes(int(a.group(2)), int(a.group(3)), a_mer)
            end = _ko_minutes(int(b.group(2)), int(b.group(3)), b_mer)
            if not b.group(1) and end <= start:
                end += 720
            intervals.append(_finish(start, end))
        hours[day] = intervals
    return hours or None


def intervals_for(hours: Hours | None, weekday: int | None) -> Intervals | None:
    """None은 '영업시간 불명'. 요일을 모르면 가장 흔한 요일 패턴을 쓴다."""
    if hours is None:
        return None
    if weekday is not None:
        return hours.get(weekday, [])
    patterns = Counter(tuple(v) for v in hours.values())
    return list(patterns.most_common(1)[0][0]) if patterns else []


def earliest_start(intervals: Intervals | None, t: int, duration: int) -> int | None:
    """t 이후 duration분을 통째로 수용하는 가장 이른 시작 시각. 불가하면 None."""
    if intervals is None:
        return t
    for start, end in sorted(intervals):
        candidate = max(t, start)
        if candidate + duration <= end:
            return candidate
    return None


def has_weekday_closure(hours: Hours | None) -> bool:
    return bool(hours) and any(not v for v in hours.values())
