"""한식 판단 결과 모델 (korean_check.py의 Claude 판단을 담는다).

ranking.py의 Candidate와 korean_check.py가 서로를 가져오지 않도록 모델만 따로 둔다.

판단 근거(reason)는 저장하지 않고 메모리에서만 쓴다.
"""

from typing import Literal

from pydantic import BaseModel

Verdict = Literal["korean", "not_korean", "uncertain"]


class KoreanCheck(BaseModel):
    """Claude의 한식 판단. 원본 분류(cuisine_tag, is_korean)는 바꾸지 않고 따로 붙는다."""

    verdict: Verdict
    reason: str  # 한 줄 근거
    checked_by: Literal["claude", "google"] = "claude"  # google = Claude를 못 써서 원본 분류로 대신함
