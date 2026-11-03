"""나이·성별로 기준 보행속도를 찾는 로직.

국내 보행속도 연구(한국인 다기관 등록 연구, 압력 기반 보행 분석)의 연령대(5세
단위)·성별 평균값 표를 사용한다. "건강한 인구" 기준 평균값이므로, 생활형 질문(계단,
연속보행 등)으로 이 기준 속도를 보정하는 로직은 아직 없다 (확장 포인트는
schema.WalkingSpeed의 주석 참고).
"""

from .schema import Gender, WalkingSpeed

# (연령 하한, 연령 상한 또는 None=상한 없음, 여성 평균 m/s, 남성 평균 m/s)
_AGE_BAND_TABLE: list[tuple[int, int | None, float, float]] = [
    (50, 59, 1.1646, 1.2055),
    (60, 64, 1.1164, 1.1489),
    (65, 69, 1.0525, 1.1041),
    (70, 74, 1.0012, 1.0994),
    (75, 79, 1.0723, 1.0162),
    (80, None, 0.9522, 0.9366),
]


def compute_walking_speed(age: int, gender: Gender) -> WalkingSpeed | None:
    """50세 미만은 표 범위 밖이라 매핑하지 않고 None을 반환한다."""
    if age < _AGE_BAND_TABLE[0][0]:
        return None

    low, high, female_speed, male_speed = next(
        band for band in _AGE_BAND_TABLE if band[1] is None or age <= band[1]
    )
    speed = female_speed if gender == "female" else male_speed
    age_band = f"{low}세 이상" if high is None else f"{low}~{high}세"
    return WalkingSpeed(age_band=age_band, base_speed_mps=speed)
