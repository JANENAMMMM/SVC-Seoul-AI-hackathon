"""식당 태그 테스트. Claude·Google API는 호출하지 않는다."""

from types import SimpleNamespace

import pytest

from src.restaurants.collect import Attraction, collect
from src.restaurants.google_places import OpeningPeriod, Restaurant
from src.restaurants.google_reviews import PlaceReviews, Review
from src.restaurants.korean_check import BudgetExceeded
from src.restaurants.tags import (
    RECORD_TOOL,
    RestaurantTags,
    TagInput,
    TagJudge,
    parse_tags,
    rule_tags,
)

HOURS = [OpeningPeriod(open_day=d, open_time="10:00", close_day=d, close_time="22:00") for d in range(7)]


def make(pid, primary_type="restaurant", rating=4.5):
    return Restaurant(
        place_id=pid, name=pid, lat=16.07, lng=108.22, primary_type=primary_type,
        rating=rating, rating_count=500, opening_periods=HOURS,
    )


def tool_use(tags):
    return SimpleNamespace(type="tool_use", name=RECORD_TOOL["name"], input={"tags": tags})


def item(pid, **kw):
    base = {"place_id": pid, "venue_type": "restaurant", "ingredient_tags": [], "confidence": "high", "evidence": []}
    return {**base, **kw}


# ── 규칙 ──────────────────────────────────────────────────


def test_rule_marks_seafood_types():
    t = rule_tags("seafood_restaurant")
    assert t.ingredient_tags == ["seafood"] and t.tag_confidence == "high"
    assert t.tag_evidence == ["대표 타입: seafood_restaurant"]
    assert rule_tags("vietnamese_restaurant") == RestaurantTags()
    assert rule_tags(None) == RestaurantTags()


# ── Claude 응답 읽기 ──────────────────────────────────────


def test_parse_keeps_only_allowed_ingredients_and_real_quotes():
    items = [TagInput("a", "삼겹살집", "restaurant", ["삼겹살이 정말 맛있어요", "분위기 좋음"])]
    out = parse_tags(
        [tool_use([item("a", ingredient_tags=["pork", "gluten", "pork"], evidence=["삼겹살이 정말 맛있어요", "지어낸 문장"])])],
        items,
    )["a"]
    assert out.ingredient_tags == ["pork"]  # 허용 목록 밖(gluten)과 중복 제거
    assert out.tag_evidence == ["삼겹살이 정말 맛있어요"]  # 리뷰에 없는 문장은 버림
    assert out.tag_confidence == "high"


def test_parse_downgrades_confidence_when_no_evidence_survives():
    items = [TagInput("a", "식당", "restaurant", ["맛있어요"])]
    out = parse_tags([tool_use([item("a", ingredient_tags=["dairy"], evidence=["치즈가 가득"])])], items)["a"]
    assert out.ingredient_tags == ["dairy"] and out.tag_evidence == [] and out.tag_confidence == "low"


def test_parse_missing_restaurant_is_unknown():
    items = [TagInput("a", "식당", "restaurant", ["맛있어요"]), TagInput("b", "식당2", "restaurant", ["좋아요"])]
    out = parse_tags([tool_use([item("a")])], items)
    assert out["b"] == RestaurantTags()  # unknown / [] / low


def test_parse_name_counts_as_evidence():
    items = [TagInput("a", "Sushi Bar 초밥", "restaurant", ["좋아요"])]
    out = parse_tags([tool_use([item("a", ingredient_tags=["seafood"], evidence=["Sushi Bar 초밥"])])], items)["a"]
    assert out.tag_evidence == ["Sushi Bar 초밥"] and out.tag_confidence == "high"


# ── TagJudge ──────────────────────────────────────────────


class FakeClient:
    def __init__(self, tags_by_call):
        self.calls = []
        self._tags = tags_by_call
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(
            content=[tool_use(self._tags)],
            usage=SimpleNamespace(input_tokens=1000, output_tokens=100, server_tool_use=None),
            stop_reason="end_turn",
        )


def test_no_reviews_skips_claude_and_uses_rule_only():
    client = FakeClient([])
    judge = TagJudge(client=client)
    out = judge.judge(
        [TagInput("a", "A", "restaurant", []), TagInput("s", "S", "seafood_restaurant", [])], "한 시장"
    )
    assert client.calls == []
    assert out["a"] == RestaurantTags()  # unknown, [], low
    assert out["s"].ingredient_tags == ["seafood"]


def test_judge_merges_rule_and_claude_and_caches():
    client = FakeClient([item("s", venue_type="street_food", ingredient_tags=["pork"], confidence="low",
                              evidence=["돼지 꼬치"])])
    judge = TagJudge(client=client)
    items = [TagInput("s", "S", "seafood_restaurant", ["돼지 꼬치 노점"])]
    out = judge.judge(items, "한 시장")["s"]
    assert out.venue_type == "street_food"
    assert out.ingredient_tags == ["pork", "seafood"]  # Claude 판단 + 규칙 확정
    assert out.tag_confidence == "medium"  # 규칙 확정 재료가 있으면 low는 medium으로 올림
    assert out.tag_evidence == ["대표 타입: seafood_restaurant", "돼지 꼬치"]
    assert client.calls[0]["model"] == "claude-haiku-5-5" and "web_search" not in str(client.calls[0]["tools"])

    judge.judge(items, "한 시장")
    assert len(client.calls) == 1  # 같은 식당은 다시 묻지 않음


def test_budget_exceeded():
    judge = TagJudge(budget_usd=0.0, client=FakeClient([]))
    with pytest.raises(BudgetExceeded):
        judge.judge([TagInput("a", "A", "restaurant", ["좋아요"])], "한 시장")


# ── collect 연결 ──────────────────────────────────────────


def _run(tag_judge=None, with_reviews=True, tags=True):
    def search(lat, lng, radius_m, included_types):
        return [make("pork1", "korean_barbecue_restaurant"), make("sea1", "seafood_restaurant"), make("quiet")]

    def reviews(place_id):
        if place_id == "quiet":
            return PlaceReviews(reviews=[])
        return PlaceReviews(reviews=[Review(original_text=f"{place_id} 삼겹살 맛집", original_language="ko")])

    att = [Attraction(id="a", name="한시장", lat=16.07, lng=108.22)]
    return collect(att, city="다낭", with_reviews=with_reviews, google_search=search, review_fetch=reviews,
                   tags=tags, tag_judge=tag_judge).attractions[0].restaurants


def test_collect_tags_false_has_no_tags():
    for r in _run(tags=False):
        assert r.venue_type is None and r.ingredient_tags is None
        assert r.tag_confidence is None and r.tag_evidence is None


def test_collect_attaches_tags_without_touching_reviews():
    client = FakeClient([
        item("pork1", ingredient_tags=["pork"], evidence=["pork1 삼겹살 맛집"]),
        item("sea1"),
    ])
    rs = {r.place_id: r for r in _run(TagJudge(client=client))}
    assert rs["pork1"].ingredient_tags == ["pork"]
    assert rs["pork1"].tag_evidence == ["pork1 삼겹살 맛집"]
    assert rs["sea1"].ingredient_tags == ["seafood"]  # 규칙
    assert rs["quiet"].venue_type == "unknown" and rs["quiet"].ingredient_tags == []  # 리뷰 없음
    assert rs["pork1"].reviews.korean_reviews[0].original_text == "pork1 삼겹살 맛집"  # 원문 그대로
    assert len(client.calls) == 1  # 관광지당 묶음 1회


def test_collect_without_reviews_uses_rules_only():
    client = FakeClient([])
    rs = {r.place_id: r for r in _run(TagJudge(client=client), with_reviews=False)}
    assert client.calls == []
    assert rs["sea1"].ingredient_tags == ["seafood"] and rs["pork1"].ingredient_tags == []


# ── 응답에서 빠진 식당은 다시 묻는다 ───────────────────────


class SequenceClient:
    """호출마다 준비된 응답을 차례로 돌려준다."""

    def __init__(self, responses):
        self.calls = []
        self._responses = list(responses)
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(
            content=[tool_use(self._responses.pop(0))],
            usage=SimpleNamespace(input_tokens=1000, output_tokens=100, server_tool_use=None),
            stop_reason="end_turn",
        )


def test_missing_restaurants_are_asked_again():
    client = SequenceClient([
        [item("a", ingredient_tags=["pork"], evidence=["삼겹살"])],  # b가 빠진 응답
        [item("b", venue_type="street_food", evidence=["길거리 노점"])],  # 다시 물으면 b만 답함
    ])
    judge = TagJudge(client=client)
    out = judge.judge(
        [TagInput("a", "A", "restaurant", ["삼겹살 맛집"]), TagInput("b", "B", "restaurant", ["길거리 노점이에요"])],
        "한 시장",
    )
    assert out["a"].ingredient_tags == ["pork"]
    assert out["b"].venue_type == "street_food"
    assert len(client.calls) == 2 and '"b"' in client.calls[1]["messages"][0]["content"]
    assert '"a"' not in client.calls[1]["messages"][0]["content"]


def test_large_input_is_split_into_batches():
    client = SequenceClient([[item(f"r{i}") for i in range(5)], [item(f"r{i}") for i in range(5, 7)]])
    judge = TagJudge(client=client)
    items = [TagInput(f"r{i}", f"R{i}", "restaurant", ["좋아요"]) for i in range(7)]
    out = judge.judge(items, "한 시장")
    assert len(client.calls) == 2 and set(out) == {f"r{i}" for i in range(7)}


def test_still_missing_after_retry_falls_back_to_unknown():
    client = SequenceClient([[], []])
    out = TagJudge(client=client).judge([TagInput("a", "A", "restaurant", ["좋아요"])], "한 시장")
    assert out["a"] == RestaurantTags() and len(client.calls) == 1  # 식당 1곳이면 다시 묻지 않음
