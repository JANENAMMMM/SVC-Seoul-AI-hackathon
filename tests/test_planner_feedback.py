"""자연어 피드백 -> 수정 명령 변환 테스트. Claude API는 호출하지 않는다 (가짜 클라이언트)."""

import datetime
from types import SimpleNamespace

from pydantic import TypeAdapter

from src.planner.edit import NO_LLM_MESSAGE, refine
from src.planner.engine import build_itinerary
from src.planner.feedback import (
    FeedbackInterpreter,
    command_schema,
    parse_response,
    record_tool,
    summarize,
)
from src.planner.schema import EditCommand, PlanRequest
from src.planner.sources import Restaurants

IDS = [f"dad-{i:02d}" for i in (1, 2, 3, 5, 6, 7, 8, 14)]


def base_plan(profile):
    req = PlanRequest(travelers=[profile], place_ids=IDS, days=4, start_date=datetime.date(2026, 12, 7))
    return build_itinerary(req, Restaurants())


def tool_block(commands=(), unsupported=(), question=None):
    return SimpleNamespace(
        type="tool_use", name="record_commands",
        input={"commands": list(commands), "unsupported": list(unsupported), "question": question},
    )


class FakeClient:
    def __init__(self, *blocks):
        self.calls = []
        self._blocks = list(blocks)
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(
            content=self._blocks,
            usage=SimpleNamespace(input_tokens=800, output_tokens=60, server_tool_use=None),
            stop_reason="end_turn",
        )


# ── 도구 스키마 ───────────────────────────────────────────


def test_tool_schema_covers_all_commands_and_is_strict_friendly():
    ops = sorted(s["properties"]["op"]["enum"][0] for s in command_schema()["anyOf"])
    assert ops == ["add_place", "adjust_walk_limit", "lighten_day", "more_korean_meals", "move_place",
                   "remove_place", "set_mode", "set_pace", "swap_restaurant"]
    text = str(record_tool())
    assert "$ref" not in text and "oneOf" not in text and "const" not in text
    for s in command_schema()["anyOf"]:  # strict: 모든 필드 required, 추가 필드 금지
        assert s["additionalProperties"] is False and set(s["required"]) == set(s["properties"])


# ── 응답 읽기 ─────────────────────────────────────────────


def test_parse_valid_commands():
    out = parse_response([tool_block([
        {"op": "lighten_day", "day": 2},
        {"op": "add_place", "place_id": "dad-09", "day": None},
        {"op": "swap_restaurant", "day": 1, "meal": "lunch"},
    ])])
    assert [c.op for c in out.commands] == ["lighten_day", "add_place", "swap_restaurant"]
    assert out.commands[1].day is None and not out.notes()


def test_parse_moves_invalid_commands_to_unsupported():
    out = parse_response([tool_block([{"op": "fly_away"}, {"op": "lighten_day", "day": "둘째 날"}])])
    assert out.commands == [] and len(out.unsupported) == 2


def test_parse_keeps_unsupported_and_question():
    out = parse_response([tool_block(unsupported=["해산물은 빼 주세요"], question="어느 날짜인가요?")])
    assert out.commands == []
    assert "해산물은 빼 주세요" in out.notes() and "어느 날짜인가요?" in out.notes()


def test_parse_without_tool_call_is_error():
    assert parse_response([SimpleNamespace(type="text", text="안녕")]).error


# ── 변환기 ────────────────────────────────────────────────


def test_interpreter_sends_summary_without_reviews_and_uses_cheapest_model(make_profile):
    plan = base_plan(make_profile())
    client = FakeClient(tool_block([{"op": "lighten_day", "day": 2}]))
    out = FeedbackInterpreter(client=client).interpret(plan, "2일차는 좀 가볍게 해주세요")
    assert [c.op for c in out.commands] == ["lighten_day"]
    call = client.calls[0]
    assert call["model"] == "claude-haiku-5-5" and call["tools"][0]["name"] == "record_commands"
    sent = call["messages"][0]["content"]
    assert "2일차는 좀 가볍게 해주세요" in sent and "1일차:" in sent and "dad-01" in sent
    assert "korean_reviews" not in sent


def test_empty_feedback_does_not_call_claude(make_profile):
    client = FakeClient()
    out = FeedbackInterpreter(client=client).interpret(base_plan(make_profile()), "   ")
    assert client.calls == [] and out.question


def test_budget_exceeded_returns_error_not_exception(make_profile):
    interp = FeedbackInterpreter(budget_usd=0.0, client=FakeClient())
    out = interp.interpret(base_plan(make_profile()), "가볍게")
    assert out.error and out.commands == []


def test_summary_lists_plan_and_missing_places(make_profile):
    text = summarize(base_plan(make_profile()))
    assert "여행 4일" in text and "일정에 없는 관광지:" in text and "(dad-09)" in text


# ── refine 연결 ───────────────────────────────────────────


def test_refine_applies_interpreted_commands(make_profile):
    plan = base_plan(make_profile())
    interp = FeedbackInterpreter(client=FakeClient(tool_block([{"op": "set_pace", "pace": "slower"}])))
    res = refine(plan, [], "너무 빡빡해요", rest=Restaurants(), interpreter=interp)
    assert [c.op for c in res.applied_commands] == ["set_pace"]
    assert res.itinerary.state.pace == "slower" and not res.clarification


def test_refine_applies_supported_part_and_reports_the_rest(make_profile):
    plan = base_plan(make_profile())
    interp = FeedbackInterpreter(client=FakeClient(
        tool_block([{"op": "set_pace", "pace": "slower"}], unsupported=["해산물은 빼 주세요"])))
    res = refine(plan, [], "천천히, 그리고 해산물은 빼 주세요", rest=Restaurants(), interpreter=interp)
    assert res.itinerary.state.pace == "slower"
    assert "해산물은 빼 주세요" in res.clarification


def test_refine_nothing_to_apply_returns_current_plan(make_profile):
    plan = base_plan(make_profile())
    interp = FeedbackInterpreter(client=FakeClient(tool_block(question="어느 날짜인가요?")))
    res = refine(plan, [], "좀 바꿔줘", rest=Restaurants(), interpreter=interp)
    assert res.itinerary is plan and res.clarification == "어느 날짜인가요?" and not res.applied_commands


def test_refine_bad_day_from_llm_keeps_plan_unchanged(make_profile):
    plan = base_plan(make_profile())
    interp = FeedbackInterpreter(client=FakeClient(tool_block([{"op": "lighten_day", "day": 9}])))
    res = refine(plan, [], "9일차를 가볍게", rest=Restaurants(), interpreter=interp)
    assert res.itinerary is plan and "여행 일수" in res.clarification


def test_explicit_commands_skip_the_llm(make_profile):
    client = FakeClient(tool_block([{"op": "set_pace", "pace": "faster"}]))
    plan = base_plan(make_profile())
    cmds = [TypeAdapter(EditCommand).validate_python({"op": "set_pace", "pace": "slower"})]
    res = refine(plan, cmds, "무시되는 문장", rest=Restaurants(), interpreter=FeedbackInterpreter(client=client))
    assert client.calls == [] and res.itinerary.state.pace == "slower"


def test_without_interpreter_feedback_only_still_explains(make_profile):
    res = refine(base_plan(make_profile()), [], feedback="너무 힘들어요", rest=Restaurants())
    assert res.clarification == NO_LLM_MESSAGE
