"""Claude로 식당이 한식당인지 판단한다 (선택 기능, 기본 꺼짐).

Google 대표 타입은 한식 분류가 자주 틀린다 (예: 베트남 닭밥집 "Cơm gà"가 korean_restaurant).
이름에 티가 안 나는 한식당도 있어서 규칙 대신 Claude가 이름·위치(필요하면 웹 검색)로 판단한다.

결과는 원본 분류(cuisine_tag, is_korean)를 덮어쓰지 않고 Candidate.korean_check로 옆에 붙는다.
한식 여부 최종값은 Candidate.is_korean_final (korean만 한식, not_korean·uncertain은 한식 아님).

저장 규칙: 판단 결과(근거 문장 포함)는 저장하지 않고 메모리에서만 쓴다. 기본은 꺼짐이고 필요할 때만 켠다.

비용 최소화 설정 (팀 예산 제한):
- 모델 Claude Haiku 5.5, effort low, 관광지당 1회 묶음 호출
- 한 번 실행하는 동안 같은 식당은 다시 묻지 않음 (place_id 캐시)
- 웹 검색은 이름·위치로 모르는 곳만, 호출당 최대 2회. 첫 판단이 uncertain이면 웹 검색을 강제해 한 번 더 확인
- 응답마다 사용량을 합산해 추정 비용이 예산(기본 1달러)을 넘으면 BudgetExceeded

한식당 기준: 한국 음식을 주로 파는 곳 (한식·한국식 BBQ·분식·치킨·한국식 중화요리·매운 라면 포함).
"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import anthropic
from dotenv import load_dotenv

from .google_places import Restaurant
from .korean_judgment import KoreanCheck, Verdict

# 이전 이름과 호환
Judgment = KoreanCheck

MODEL = "claude-haiku-5-5"
EFFORT = "low"
MAX_TOKENS = 4000
WEB_SEARCH_MAX_USES = 2
DEFAULT_BUDGET_USD = 1.0

# 비용 추정용 단가 (Claude Haiku 5.5, 프롬프트 10만 토큰 이하 기준)
USD_PER_INPUT_TOKEN = 0.10 / 1_000_000
USD_PER_OUTPUT_TOKEN = 0.50 / 1_000_000
USD_PER_WEB_SEARCH = 10 / 1000  # 웹 검색 1,000회당 약 10달러 (확인 필요)


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    def __init__(self, limit_usd: float = DEFAULT_BUDGET_USD):
        self.limit_usd = limit_usd
        self.spent_usd = 0.0
        self.calls = 0
        self.web_searches = 0

    def add(self, usage: Any) -> None:
        searches = getattr(getattr(usage, "server_tool_use", None), "web_search_requests", 0) or 0
        self.calls += 1
        self.web_searches += searches
        self.spent_usd += (
            (usage.input_tokens or 0) * USD_PER_INPUT_TOKEN
            + (usage.output_tokens or 0) * USD_PER_OUTPUT_TOKEN
            + searches * USD_PER_WEB_SEARCH
        )

    def check(self) -> None:
        if self.spent_usd >= self.limit_usd:
            raise BudgetExceeded(
                f"Claude 예산 초과: 추정 ${self.spent_usd:.3f} / 상한 ${self.limit_usd:.2f}"
            )


RECORD_TOOL = {
    "name": "record_korean_judgments",
    "description": "후보 식당마다 한식당인지 판단한 결과를 기록한다. 모든 후보를 한 번에 담아 정확히 한 번 호출한다.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "judgments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "place_id": {"type": "string"},
                        "verdict": {"type": "string", "enum": ["korean", "not_korean", "uncertain"]},
                        "reason": {"type": "string"},
                    },
                    "required": ["place_id", "verdict", "reason"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["judgments"],
        "additionalProperties": False,
    },
}

SYSTEM = """너는 여행지 주변 식당 목록에서 한식당을 가려내는 분류기다.

한식당 = 한국 음식을 주로 파는 곳. 한식, 한국식 BBQ, 분식, 한국식 치킨, 한국식 중화요리(짜장면·짬뽕), 한국식 매운 라면집을 포함한다.
한국인이 운영해도 메뉴가 주로 현지식이거나 다른 나라 음식이면 not_korean이다.

- Google 대표 타입은 틀린 경우가 많다 (베트남 밥집이 korean_restaurant로 등록되기도 함). 참고만 하라.
- 이름과 위치로 판단할 수 있으면 검색하지 마라. 정말 모르는 곳만 web_search로 확인하라.
- 확신이 없으면 uncertain으로 답하라. 추측해서 korean이라고 하지 마라.
- 판단이 끝나면 모든 후보를 담아 record_korean_judgments를 정확히 한 번 호출하라. reason은 한국어 한 줄(20자 내외)."""


@lru_cache
def _client() -> anthropic.Anthropic:
    """ANTHROPIC_API_KEY는 환경변수가 루트 .env보다 우선한다."""
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
        raise RuntimeError(
            "Claude 설정이 필요합니다: ANTHROPIC_API_KEY. .env.example을 참고해 루트 .env를 작성하세요."
        )
    return anthropic.Anthropic()


def _prompt(restaurants: list[Restaurant], area: str) -> str:
    rows = [
        {
            "place_id": r.place_id,
            "name": r.name,
            "google_primary_type": r.primary_type,
            "lat": round(r.lat, 5),
            "lng": round(r.lng, 5),
        }
        for r in restaurants
    ]
    return f"지역: {area}\n후보 식당 {len(rows)}곳:\n" + json.dumps(rows, ensure_ascii=False, indent=1)


def parse_judgments(content: list[Any], place_ids: list[str]) -> dict[str, KoreanCheck]:
    """응답의 record_korean_judgments 호출을 읽는다. 빠진 식당은 uncertain."""
    found: dict[str, KoreanCheck] = {}
    for block in content:
        if getattr(block, "type", None) == "tool_use" and block.name == RECORD_TOOL["name"]:
            for item in (block.input or {}).get("judgments", []):
                if item.get("place_id") in place_ids:
                    found[item["place_id"]] = KoreanCheck(verdict=item["verdict"], reason=item["reason"])
    for pid in place_ids:
        found.setdefault(pid, KoreanCheck(verdict="uncertain", reason="판단 결과 없음"))
    return found


class KoreanJudge:
    def __init__(
        self,
        budget_usd: float = DEFAULT_BUDGET_USD,
        web_search: bool = True,
        client: Optional[anthropic.Anthropic] = None,
    ):
        self.budget = Budget(budget_usd)
        self.web_search = web_search
        self._client = client
        # 이번 실행 동안만 쓰는 메모리. 파일·DB에 쓰지 않는다.
        self.cache: dict[str, KoreanCheck] = {}

    @property
    def client(self) -> anthropic.Anthropic:
        return self._client or _client()

    def judge(self, restaurants: list[Restaurant], area: str) -> dict[str, KoreanCheck]:
        """아직 판단하지 않은 식당만 1회 묶음 호출로 판단하고, 요청한 식당 전부의 결과를 돌려준다.

        uncertain이 나온 식당은 웹 검색으로 직접 확인하도록 한 번 더 묻는다 (실행마다 판단이
        흔들리는 것을 줄이기 위해). 그래도 uncertain이면 한식 아님으로 처리된다.
        """
        todo = [r for r in restaurants if r.place_id not in self.cache]
        if todo:
            first = self._ask(todo, area)
            self.cache.update(first)
            unsure = [r for r in todo if first[r.place_id].verdict == "uncertain"]
            if unsure and self.web_search:
                self.cache.update(self._ask(unsure, area, must_search=True))
        return {r.place_id: self.cache[r.place_id] for r in restaurants}

    def _ask(
        self, restaurants: list[Restaurant], area: str, must_search: bool = False
    ) -> dict[str, KoreanCheck]:
        self.budget.check()
        tools: list[dict[str, Any]] = [RECORD_TOOL]
        if self.web_search:
            tools.append(
                {"type": "web_search_20250305", "name": "web_search", "max_uses": WEB_SEARCH_MAX_USES}
            )
        prompt = _prompt(restaurants, area)
        if must_search:
            prompt += (
                "\n\n앞선 판단에서 확신하지 못한 식당들이다. 각 식당을 web_search로 직접 검색해 "
                "메뉴·소개를 확인한 뒤 판단하라. 검색해도 알 수 없으면 uncertain으로 답한다."
            )
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        response = None
        for _ in range(3):  # 웹 검색이 길면 pause_turn으로 멈출 수 있어 이어서 진행
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM,
                messages=messages,
                tools=tools,
                output_config={"effort": EFFORT},
            )
            self.budget.add(response.usage)
            if response.stop_reason != "pause_turn":
                break
            messages.append({"role": "assistant", "content": response.content})
        # 이번 호출로 상한을 넘었어도 결과는 쓰고, 다음 호출 직전 check()에서 막는다
        return parse_judgments(response.content if response else [], [r.place_id for r in restaurants])


def apply_judgments(candidates: list, judgments: dict[str, KoreanCheck]) -> None:
    """판단 결과를 후보에 붙인다. 원본 분류(cuisine)는 바꾸지 않는다.

    한식 여부 최종값은 Candidate.is_korean_final:
    - korean: 한식 / not_korean: 한식 아님 / uncertain: 한식 아님으로 처리
    """
    for c in candidates:
        j = judgments.get(c.restaurant.place_id)
        if j is not None:
            c.korean_check = j
