"""부모님 프로필 API. 저장 없이 입력을 정규화해서 반환한다."""

from fastapi import APIRouter

from src.profile.schema import ParentProfile, ParentProfileInput
from src.profile.service import build_profile

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.post("", response_model=ParentProfile)
def create_profile(profile_input: ParentProfileInput) -> ParentProfile:
    return build_profile(profile_input)
