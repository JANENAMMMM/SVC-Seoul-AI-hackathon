"""식당 태그(venue_type, ingredient_tags)를 만든다 (선택 기능, 기본 꺼짐).

일정 엔진이 부모님 프로필(식사 장소 `venues`, 피하는 식재료 `avoid_ingredients`)로 식당을 거를 때 쓴다.
태그가 없으면 엔진은 거르지 않는다.

- 규칙: 대표 타입이 해산물 전문점이면 seafood로 확정한다.
- Claude: 규칙으로 알 수 없는 것(돼지고기·유제품·견과류, 노점 여부)을 한국어 리뷰 원문과 식당 이름으로 판단한다.
  리뷰가 없는 식당은 Claude를 부르지 않고 venue_type=unknown, ingredient_tags=[]로 둔다.

결과 필드 (모두 새로 붙는 필드이고 기존 필드를 덮어쓰지 않는다):
- venue_type: restaurant / street_food / unknown
- ingredient_tags: pork / seafood / dairy / nuts 중 **확인된 것만**. 없으면 [].
  리뷰에 언급이 없다고 그 재료를 안 쓴다는 뜻은 아니다.
- tag_confidence: high / medium / low
- tag_evidence: 근거가 된 리뷰 원문 발췌(리뷰에 실제로 있는 문장만 남김) 또는 "대표 타입: ..."

저장 규칙: 태그를 만들어 돌려주기만 하고 파일·DB에 쓰지 않는다 (원본). 로컬 데모 스크립트만 데모 JSON에 저장한다.
리뷰 원문은 고치지 않는다.

비용 최소화: Claude Haiku 5.5, effort low, 웹 검색 없음, 관광지당 1회 묶음 호출,
같은 식당은 다시 묻지 않음(place_id 캐시), 추정 비용이 예산(기본 1달러)을 넘으면 BudgetExceeded.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

import anthropic
from pydantic import BaseModel

from .korean_check import DEFAULT_BUDGET_USD, EFFORT, MODEL, Budget, _client

MAX_TOKENS = 4000
BATCH_SIZE = 5  # 한 번에 묻는 식당 수. 크면 응답이 잘려 일부 식당이 빠진다
MAX_REVIEWS_PER_RESTAURANT = 5
MAX_EVIDENCE_PER_RESTAURANT = 4

VenueType = Literal["restaurant", "street_food", "unknown"]
Confidence = Literal["high", "medium", "low"]
INGREDIENTS = ("pork", "seafood", "dairy", "nuts")

# 대표 타입이 이거면 해산물을 다루는 곳으로 확정
SEAFOOD_TYPES = frozenset(
    {"seafood_restaurant", "oyster_bar_restaurant", "sushi_restaurant", "fish_and_chips_restaurant"}
)


class RestaurantTags(BaseModel):
    venue_type: VenueType = "unknown"
    ingredient_tags: list[str] = []
    tag_confidence: Confidence = "low"
    tag_evidence: list[str] = []


@dataclass
class TagInput:
    """태그 판단에 쓰는 식당 정보. 리뷰는 한국어 원문 그대로."""

    place_id: str
    name: str
    primary_type: Optional[str]
    reviews: list[str] = field(default_factory=list)


def rule_tags(primary_type: Optional[str]) -> RestaurantTags:
    """대표 타입으로 확정할 수 있는 것만 채운다."""
    if primary_type in SEAFOOD_TYPES:
        return RestaurantTags(
            ingredient_tags=["seafood"], tag_confidence="high", tag_evidence=[f"대표 타입: {primary_type}"]
        )
    return RestaurantTags()


RECORD_TOOL = {
    "name": "record_restaurant_tags",
    "description": "식당마다 식사 장소 유형과 확인된 식재료를 기록한다. 모든 식당을 한 번에 담아 정확히 한 번 호출한다.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "place_id": {"type": "string"},
                        "venue_type": {"type": "string", "enum": ["restaurant", "street_food", "unknown"]},
                        "ingredient_tags": {
                            "type": "array",
                            "items": {"type": "string", "enum": list(INGREDIENTS)},
                        },
                        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                        "evidence": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["place_id", "venue_type", "ingredient_tags", "confidence", "evidence"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["tags"],
        "additionalProperties": False,
    },
}

SYSTEM = """너는 여행지 식당의 한국어 리뷰를 읽고 두 가지를 기록하는 분류기다.

1. venue_type
   - street_food: 노점, 길거리 음식, 야외 간이 좌석, 시장 안 가판처럼 길거리 분위기가 리뷰에 드러남
   - restaurant: 실내 좌석이 있는 일반 식당·레스토랑·카페 분위기가 드러남
   - unknown: 리뷰로 알 수 없음
2. ingredient_tags: 이 식당에서 pork(돼지고기), seafood(해산물), dairy(유제품), nuts(견과류)를
   **주요 메뉴나 재료로 파는 것이 리뷰나 이름에서 확인될 때만** 넣는다.
   언급이 없으면 넣지 마라. 확인된 것이 없으면 빈 배열이다.

- evidence에는 판단 근거가 된 **리뷰 원문 문장을 글자 그대로 복사**해서 넣는다 (요약·번역·수정 금지). 짧게 한 문장 이내.
  식당 이름이 근거면 이름을 그대로 넣는다.
- confidence: 근거가 분명하면 high, 정황이면 medium, 추측에 가까우면 low.
- 확신이 없으면 unknown 또는 빈 배열로 답하라. 추측하지 마라.
- 판단이 끝나면 모든 식당을 담아 record_restaurant_tags를 정확히 한 번 호출하라."""


def _prompt(items: list[TagInput], area: str) -> str:
    rows = [
        {
            "place_id": i.place_id,
            "name": i.name,
            "google_primary_type": i.primary_type,
            "reviews": i.reviews[:MAX_REVIEWS_PER_RESTAURANT],
        }
        for i in items
    ]
    return f"지역: {area}\n식당 {len(rows)}곳:\n" + json.dumps(rows, ensure_ascii=False, indent=1)


def _merge(llm: RestaurantTags, rule: RestaurantTags) -> RestaurantTags:
    """규칙 결과를 Claude 결과에 합친다 (규칙으로 확정된 재료는 항상 포함)."""
    tags = list(dict.fromkeys(llm.ingredient_tags + rule.ingredient_tags))
    evidence = list(dict.fromkeys(rule.tag_evidence + llm.tag_evidence))[:MAX_EVIDENCE_PER_RESTAURANT]
    confidence = llm.tag_confidence
    if rule.ingredient_tags and confidence == "low":
        confidence = "medium"
    return RestaurantTags(
        venue_type=llm.venue_type, ingredient_tags=tags, tag_confidence=confidence, tag_evidence=evidence
    )


def _returned_ids(content: list[Any]) -> set[str]:
    """응답의 record_restaurant_tags 호출에 실제로 들어 있는 place_id."""
    ids: set[str] = set()
    for block in content:
        if getattr(block, "type", None) == "tool_use" and block.name == RECORD_TOOL["name"]:
            ids.update(i.get("place_id") for i in (block.input or {}).get("tags", []))
    return ids


def parse_tags(content: list[Any], items: list[TagInput]) -> dict[str, RestaurantTags]:
    """응답의 record_restaurant_tags 호출을 읽는다.

    - 식재료는 허용 목록(pork/seafood/dairy/nuts)만 남긴다.
    - 근거(evidence)는 리뷰 원문이나 식당 이름에 실제로 있는 문장만 남긴다. 근거가 하나도 안 남았는데
      태그가 있으면 신뢰도를 low로 낮춘다.
    - 응답에 빠진 식당은 unknown / [] / low.
    """
    by_id = {i.place_id: i for i in items}
    found: dict[str, RestaurantTags] = {}
    for block in content:
        if getattr(block, "type", None) == "tool_use" and block.name == RECORD_TOOL["name"]:
            for item in (block.input or {}).get("tags", []):
                src = by_id.get(item.get("place_id"))
                if src is None:
                    continue
                corpus = [src.name, *src.reviews]
                evidence = [
                    e.strip()
                    for e in item.get("evidence", [])
                    if e.strip() and any(e.strip() in text for text in corpus)
                ][:MAX_EVIDENCE_PER_RESTAURANT]
                tags = [t for t in dict.fromkeys(item.get("ingredient_tags", [])) if t in INGREDIENTS]
                confidence = item.get("confidence", "low")
                if (tags or item.get("venue_type") == "street_food") and not evidence:
                    confidence = "low"
                found[src.place_id] = RestaurantTags(
                    venue_type=item.get("venue_type", "unknown"),
                    ingredient_tags=tags,
                    tag_confidence=confidence,
                    tag_evidence=evidence,
                )
    for i in items:
        found.setdefault(i.place_id, RestaurantTags())
    return found


class TagJudge:
    def __init__(
        self,
        budget_usd: float = DEFAULT_BUDGET_USD,
        client: Optional[anthropic.Anthropic] = None,
    ):
        self.budget = Budget(budget_usd)
        self._client = client
        # 이번 실행 동안만 쓰는 메모리. 파일·DB에 쓰지 않는다.
        self.cache: dict[str, RestaurantTags] = {}

    @property
    def client(self) -> anthropic.Anthropic:
        return self._client or _client()

    def judge(self, items: list[TagInput], area: str) -> dict[str, RestaurantTags]:
        """아직 판단하지 않은 식당만 1회 묶음 호출로 판단하고, 요청한 식당 전부의 결과를 돌려준다.

        리뷰가 없는 식당은 Claude를 부르지 않는다 (규칙 결과만).
        """
        todo = [i for i in items if i.place_id not in self.cache]
        with_reviews = [i for i in todo if i.reviews]
        for i in todo:
            if not i.reviews:
                self.cache[i.place_id] = rule_tags(i.primary_type)
        for start in range(0, len(with_reviews), BATCH_SIZE):
            chunk = with_reviews[start : start + BATCH_SIZE]
            asked = self._ask(chunk, area)
            for i in chunk:
                self.cache[i.place_id] = _merge(asked[i.place_id], rule_tags(i.primary_type))
        return {i.place_id: self.cache[i.place_id] for i in items}

    def _ask(self, items: list[TagInput], area: str) -> dict[str, RestaurantTags]:
        """응답이 잘렸거나 일부 식당이 빠졌으면 나눠서 다시 묻는다 (식당 1곳이면 포기하고 기본값)."""
        response = self._call(items, area)
        returned = _returned_ids(response.content)
        missing = [i for i in items if i.place_id not in returned]
        if missing and len(items) > 1:
            retry = self._ask(missing[: max(1, len(missing) // 2)], area)
            rest = missing[len(missing) // 2 or 1 :]
            if rest:
                retry.update(self._ask(rest, area))
            found = parse_tags(response.content, items)
            found.update(retry)
            return found
        return parse_tags(response.content, items)

    def _call(self, items: list[TagInput], area: str):
        self.budget.check()
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM,
            messages=[{"role": "user", "content": _prompt(items, area)}],
            tools=[RECORD_TOOL],
            output_config={"effort": EFFORT},
        )
        self.budget.add(response.usage)
        return response
