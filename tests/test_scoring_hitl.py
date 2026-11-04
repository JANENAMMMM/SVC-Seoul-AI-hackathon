"""HITL 피드백 루프 단위 테스트 (DB·Claude 호출 없음)."""
from types import SimpleNamespace

from src.scoring import hitl
from src.scoring.visit_modes import load_modes


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


def test_itinerary_is_only_proposed_until_approved(make_profile, monkeypatch):
    from src.planner.engine import build_itinerary
    from src.planner.schema import LightenDay, PlanRequest

    store = {}
    monkeypatch.setattr(hitl, "_save", lambda conn, row: store.__setitem__(row["id"], dict(row)))
    monkeypatch.setattr(hitl, "get_feedback", lambda conn, fid: store[fid])
    monkeypatch.setattr(hitl, "_decide", lambda conn, fid, status, who: store[fid].update(status=status))
    it = build_itinerary(PlanRequest(travelers=[make_profile(age=70)],
                                     place_ids=["dad-03", "dad-06", "dad-08", "dad-02"], days=2))
    day = it.state.pins["dad-02"]
    out = hitl.propose_itinerary(None, it, [LightenDay(op="lighten_day", day=day)], "엄마가 힘들대", "parent")
    fid = out["feedback_id"]
    assert store[fid]["status"] == "proposed" and store[fid]["actor_role"] == "parent"
    assert it.state.mode_overrides == {}  # 원래 일정은 그대로
    approved = hitl.approve_itinerary(None, fid, "child")
    assert store[fid]["status"] == "applied"
    assert approved.state.mode_overrides.get("dad-02") == "short"
