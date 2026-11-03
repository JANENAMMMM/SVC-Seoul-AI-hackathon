"""설문 원본 응답으로부터 정규화된 ParentProfile을 만든다."""

from .schema import ParentProfile, ParentProfileInput
from .walking_speed import compute_walking_speed


def build_profile(profile_input: ParentProfileInput) -> ParentProfile:
    walking_speed = compute_walking_speed(profile_input.age, profile_input.gender)
    return ParentProfile(walking_speed=walking_speed, **profile_input.model_dump())
