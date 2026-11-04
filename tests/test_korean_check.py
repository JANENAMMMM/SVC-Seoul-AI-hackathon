"""Claude 한식 판단 테스트. Claude·Google API는 호출하지 않는다."""

from types import SimpleNamespace

import pytest

from src.restaurants.collect import Attraction, collect
from src.restaurants.google_places import OpeningPeriod, Restaurant
from src.restaurants.korean_check import (
    MODEL,
    RECORD_TOOL,
    Budget,
    BudgetExceeded,
    KoreanJudge,
    apply_judgments,
    parse_judgments,
)
from src.restaurants.ranking import build_candidates

HOURS = [OpeningPeriod(open_day=d, open_time="10:00", close_day=d, close_time="22:00") for d in range(7)]


def make(pid, primary_type="restaurant", rating=4.5):
    return Restaurant(
        place_id=pid, name=pid, lat=16.07, lng=108.22, primary_type=primary_type,
        rating=rating, rating_count=500, opening_periods=HOURS,
    )


# ── Claude 응답 읽기·반영 ───────────────────────────────────

def tool_block(judgments):
    return SimpleNamespace(type="tool_use", name=RECORD_TOOL["name"], input={"judgments": judgments})


def test_parse_judgments_missing_becomes_uncertain():
    content = [
        SimpleNamespace(type="text", text="..."),
        tool_block([{"place_id": "a", "verdict": "korean", "reason": "한글 상호"}]),
    ]
    js = parse_judgments(content, ["a", "b"])
    assert js["a"].verdict == "korean"
    assert js["b"].verdict == "uncertain"


def test_apply_judgments_keeps_original_and_attaches_check():
    """Claude 판단은 원본 분류(cuisine_tag, is_korean)를 덮어쓰지 않고 korean_check로 옆에 붙는다."""
    cands = build_candidates(
        [make("ga", "korean_restaurant"), make("bulgogi", "restaurant"), make("x", "korean_restaurant")],
    )
    js = parse_judgments(
        [tool_block([
            {"place_id": "ga", "verdict": "not_korean", "reason": "베트남 닭밥집"},
            {"place_id": "bulgogi", "verdict": "korean", "reason": "불고기 전문"},
            {"place_id": "x", "verdict": "uncertain", "reason": "정보 없음"},
        ])],
        ["ga", "bulgogi", "x"],
    )
    apply_judgments(cands, js)
    by = {c.restaurant.place_id: c for c in cands}

    # 원본 분류는 그대로 (Google이 korean_restaurant로 등록했으면 계속 korean)
    assert by["ga"].cuisine.tag == "korean" and by["ga"].cuisine.is_korean
    assert by["bulgogi"].cuisine.tag == "other" and not by["bulgogi"].cuisine.is_korean
    assert by["x"].cuisine.tag == "korean" and by["x"].cuisine.is_korean

    # 판단은 따로 붙고, 최종 한식 여부만 판단을 따른다 (uncertain은 한식 아님)
    assert by["ga"].korean_check.verdict == "not_korean" and "닭밥" in by["ga"].korean_check.reason
    assert by["ga"].korean_check.checked_by == "claude"
    assert not by["ga"].is_korean_final
    assert by["bulgogi"].is_korean_final
    assert not by["x"].is_korean_final and by["x"].korean_check.verdict == "uncertain"


def test_is_korean_final_without_judgment_uses_original():
    cands = build_candidates([make("k", "korean_restaurant"), make("v", "vietnamese_restaurant")])
    by = {c.restaurant.place_id: c for c in cands}
    assert by["k"].korean_check is None and by["k"].is_korean_final is True
    assert by["v"].is_korean_final is False


# ── KoreanJudge: 호출 설정·캐시·예산 ─────────────────────────

class FakeMessages:
    def __init__(self, verdict="korean", input_tokens=2000, output_tokens=500, searches=0):
        self.calls = []
        self.verdict, self.usage = verdict, SimpleNamespace(
            input_tokens=input_tokens, output_tokens=output_tokens,
            server_tool_use=SimpleNamespace(web_search_requests=searches),
        )

    def create(self, **kwargs):
        self.calls.append(kwargs)
        ids = [line.split('"place_id": "')[1].split('"')[0]
               for line in kwargs["messages"][0]["content"].splitlines() if '"place_id"' in line]
        return SimpleNamespace(
            stop_reason="tool_use", usage=self.usage,
            content=[tool_block([{"place_id": i, "verdict": self.verdict, "reason": "r"} for i in ids])],
        )


def fake_client(**kw):
    return SimpleNamespace(messages=FakeMessages(**kw))


def test_judge_request_settings_and_cache():
    client = fake_client()
    judge = KoreanJudge(client=client)
    judge.judge([make("a"), make("b")], "한시장, 다낭")
    judge.judge([make("a"), make("c")], "용다리, 다낭")  # a는 캐시, c만 새로 물어봄

    first, second = client.messages.calls
    assert first["model"] == MODEL == "claude-haiku-5-5"
    assert first["output_config"] == {"effort": "low"}
    tools = {t.get("name"): t for t in first["tools"]}
    assert tools["web_search"]["type"] == "web_search_20250305" and tools["web_search"]["max_uses"] == 2
    assert tools["record_korean_judgments"]["strict"] is True
    assert '"place_id": "c"' in second["messages"][0]["content"]
    assert '"place_id": "a"' not in second["messages"][0]["content"]


def test_uncertain_is_rechecked_with_forced_search():
    """첫 판단에서 uncertain이 나온 식당만 웹 검색을 요구하는 두 번째 호출로 다시 묻는다."""

    class Two:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            text = kwargs["messages"][0]["content"]
            ids = [l.split('"place_id": "')[1].split('"')[0] for l in text.splitlines() if '"place_id"' in l]
            recheck = "web_search로 직접 검색" in text
            out = [{"place_id": i, "verdict": ("korean" if recheck else ("uncertain" if i == "u" else "not_korean")),
                    "reason": "r"} for i in ids]
            usage = SimpleNamespace(input_tokens=100, output_tokens=50,
                                    server_tool_use=SimpleNamespace(web_search_requests=1 if recheck else 0))
            return SimpleNamespace(stop_reason="tool_use", usage=usage, content=[tool_block(out)])

    client = SimpleNamespace(messages=Two())
    judge = KoreanJudge(client=client)
    result = judge.judge([make("a"), make("u")], "x")
    assert len(client.messages.calls) == 2
    assert '"place_id": "u"' in client.messages.calls[1]["messages"][0]["content"]
    assert '"place_id": "a"' not in client.messages.calls[1]["messages"][0]["content"]
    assert result["u"].verdict == "korean" and result["a"].verdict == "not_korean"

    # 웹 검색을 끄면 재확인하지 않는다
    client2 = SimpleNamespace(messages=Two())
    KoreanJudge(web_search=False, client=client2).judge([make("u")], "x")
    assert len(client2.messages.calls) == 1


def test_budget_blocks_next_call():
    # 1회 호출 비용: 입력 2000×$0.1/1M + 출력 500×$0.5/1M + 검색 2×$0.01 = $0.02045
    judge = KoreanJudge(budget_usd=0.03, client=fake_client(searches=2))
    judge.judge([make("a")], "x")
    judge.judge([make("b")], "x")  # 호출 전 누적 $0.02045 < $0.03 → 통과
    assert judge.budget.calls == 2
    with pytest.raises(BudgetExceeded):
        judge.judge([make("c")], "x")  # 누적 $0.0409 ≥ $0.03 → 막힘


def test_budget_cost_estimate():
    b = Budget(1.0)
    b.add(SimpleNamespace(input_tokens=1_000_000, output_tokens=1_000_000,
                          server_tool_use=SimpleNamespace(web_search_requests=10)))
    assert round(b.spent_usd, 4) == round(0.10 + 0.50 + 0.10, 4)


# ── 원본 collect(): 기본 꺼짐, 넘기면 반영 ─────────────────────

def test_collect_korean_judge_optional():
    def search(lat, lng, radius_m, included_types):
        return [make("ga", "korean_restaurant", 4.9), make("v1", "vietnamese_restaurant"), make("bulgogi")]

    att = [Attraction(id="a", name="한시장", lat=16.07, lng=108.22)]
    off = collect(att, city="다낭", with_reviews=False, google_search=search)
    assert {r.place_id: r.is_korean for r in off.attractions[0].restaurants}["ga"] is True
    assert all(r.korean_check is None for r in off.attractions[0].restaurants)  # 기본 꺼짐: 판단 필드 없음

    class Judge:
        def judge(self, restaurants, area):
            from src.restaurants.korean_judgment import KoreanCheck
            return {r.place_id: KoreanCheck(verdict="korean" if r.place_id == "bulgogi" else "not_korean",
                                         reason="r") for r in restaurants}

    on = collect(att, city="다낭", with_reviews=False, google_search=search, korean_judge=Judge())
    rs = {r.place_id: r for r in on.attractions[0].restaurants}
    # 원본 필드(is_korean)는 그대로, 최종 값(is_korean_final)만 Claude 판단을 따른다
    assert {k: v.is_korean for k, v in rs.items()} == {"ga": True, "v1": False, "bulgogi": False}
    assert {k: v.is_korean_final for k, v in rs.items()} == {"ga": False, "v1": False, "bulgogi": True}
    assert rs["ga"].korean_check.verdict == "not_korean"
