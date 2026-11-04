"""HITL 피드백 루프 단위 테스트 (DB·Claude 호출 없음)."""
import json
from types import SimpleNamespace

from src.planner.edit import refine
from src.planner.engine import build_itinerary
from src.planner.feedback import summarize
from src.planner.schema import LightenDay, PlanRequest, RemovePlace
from src.scoring import hitl
from src.scoring.verify import round_half_up
from src.scoring.visit_modes import apply_overrides, load_catalog, load_modes


def test_override_changes_only_target_and_recomputes_mode_score():
    verified = load_modes()
    before = json.dumps(verified, sort_keys=True)
    std = verified["dad-02"]["modes"]["standard"]
    new_climb = 10 if std["dimensions"]["climb"]["score"] < 10 else 1
    out = apply_overrides(verified, [{"feedback_id": "fb-1", "place_id": "dad-02", "mode": "standard",
                                      "dimension": "climb", "score": new_climb, "reason": "엘리베이터 운휴"}])
    assert json.dumps(verified, sort_keys=True) == before  # verified catalog untouched
    dim = out["dad-02"]["modes"]["standard"]["dimensions"]["climb"]
    assert dim["score"] == new_climb and dim["verified_score"] == std["dimensions"]["climb"]["score"]
    assert dim["override"]["feedback_id"] == "fb-1"
    dims = out["dad-02"]["modes"]["standard"]["dimensions"]
    expected = round_half_up((3 * dims["climb"]["score"] + 3 * dims["walking"]["score"]
                      + 2 * dims["heat"]["score"] + dims["crowd"]["score"]) / 9)
    assert out["dad-02"]["modes"]["standard"]["score"] == expected
    assert out["dad-02"]["modes"]["short"] == verified["dad-02"]["modes"]["short"]  # other modes unchanged
    assert out["dad-02"]["hitl_pending"] == ["fb-1"]
    assert "hitl_pending" not in out["dad-03"]


def test_override_mode_none_applies_to_all_modes():
    out = apply_overrides(load_modes(), [{"feedback_id": "fb-2", "place_id": "dad-05", "mode": None,
                                          "dimension": "heat", "score": 9, "reason": None}])
    assert {m["dimensions"]["heat"]["score"] for m in out["dad-05"]["modes"].values()} == {9}


def test_runtime_catalog_without_override_file_equals_verified():
    assert load_catalog() == load_modes()


def test_rate_limiter_window():
    t = [0.0]
    lim = hitl.RateLimiter(max_calls=2, window_s=10, clock=lambda: t[0])
    assert lim.allow("a") and lim.allow("a") and not lim.allow("a")
    assert lim.allow("b")
    t[0] = 11
    assert lim.allow("a")


def _fake_client(tool_input):
    block = SimpleNamespace(type="tool_use", name="record_score_feedback", input=tool_input)
    resp = SimpleNamespace(content=[block], usage=SimpleNamespace(input_tokens=3000, output_tokens=200))
    return SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: resp))


def test_interpret_score_keeps_valid_and_asks_on_invalid():
    catalog = load_modes()
    out = hitl.interpret_score("오행산 엘리베이터 자주 멈춰서 계단 기준으로 봐야 해요", catalog, client=_fake_client({
        "adjustments": [
            {"place_id": "dad-02", "dimension": "climb", "mode": "all", "score": 8, "claim": "엘리베이터가 자주 운휴"},
            {"place_id": "dad-99", "dimension": "climb", "mode": "all", "score": 8, "claim": "없는 장소"},
            {"place_id": "dad-02", "dimension": "walking", "mode": "short", "score": 11, "claim": "범위 밖"}],
        "question": None}))
    assert out["adjustments"] == [{"place_id": "dad-02", "dimension": "climb", "mode": None, "score": 8,
                                   "claim": "엘리베이터가 자주 운휴"}]
    assert out["question"]
    assert out["usage"]["input_tokens"] == 3000


def test_interpret_score_empty_text_needs_no_call():
    out = hitl.interpret_score("  ", load_modes(), client=object())
    assert out["adjustments"] == [] and out["question"]


def test_score_tool_is_strict_schema():
    tool = hitl.score_tool()
    assert tool["strict"] is True
    item = tool["input_schema"]["properties"]["adjustments"]["items"]
    assert set(item["required"]) == set(item["properties"]) and item["additionalProperties"] is False


def test_human_evidence_rows():
    rows = hitl.human_evidence("fb-x", [{"place_id": "dad-02", "dimension": "climb", "mode": None,
                                         "score": 8, "claim": "엘리베이터 운휴"}])
    assert rows[0]["id"] == "human:fb-x:0" and rows[0]["source"] == "hanatour_md"
    assert rows[0]["value"] == {"suggested_score": 8, "mode": "all"}


def _plan(make_profile):
    req = PlanRequest(travelers=[make_profile(age=70)], place_ids=["dad-03", "dad-06", "dad-08", "dad-02"], days=2)
    return build_itinerary(req)


def test_lighter_places_from_refine(make_profile):
    it = _plan(make_profile)
    day = it.state.pins["dad-02"]
    resp = refine(it, [LightenDay(op="lighten_day", day=day)])
    lighter = hitl.lighter_places(it, resp.itinerary)
    assert "dad-02" in lighter
    resp2 = refine(it, [RemovePlace(op="remove_place", place_id="dad-06")])
    assert "dad-06" in hitl.lighter_places(it, resp2.itinerary)


def test_feedback_log_is_interpreter_context(make_profile):
    it = _plan(make_profile)
    assert "이전에 승인된 요청" not in summarize(it)
    it.state.feedback_log = ["2일차 가볍게 → 오행산 엘리베이터 코스"]
    assert "2일차 가볍게" in summarize(it)
