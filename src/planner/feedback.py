"""자연어 피드백을 수정 명령(EditCommand)으로 바꾼다.

LLM은 일정을 직접 쓰지 않는다. "2일차는 좀 가볍게" 같은 문장을 정해진 명령 목록으로 바꾸기만 하고,
일정은 같은 엔진이 다시 짠다 (edit.refine). 명령이 하나라도 잘못되면 refine이 일정을 그대로 두고 되묻는다.

- 모델: Claude Haiku 5.5, effort low, 요청당 호출 1회
- 도구 스키마는 EditCommand 모델에서 만든다. 명령이 추가되면 자동으로 따라간다.
- 현재 명령으로 표현할 수 없는 요청은 억지로 끼워 맞추지 않고 unsupported로 돌려준다.
- 모호하면 question으로 되묻는다.
- Claude 호출이 실패하거나 예산을 넘으면 error로 돌려준다 (예외로 서버를 죽이지 않는다).
- 일정 요약(관광지 이름, 날짜, 식당 이름)만 보내고 식당 리뷰는 보내지 않는다. 결과는 저장하지 않는다.
"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from src.planner.schema import EditCommand, Itinerary
from src.planner.sources import load_places
from src.restaurants.korean_check import DEFAULT_BUDGET_USD, EFFORT, MODEL, Budget, BudgetExceeded

MAX_TOKENS = 2000
MAX_FEEDBACK_CHARS = 1000
DEFAULT_BUDGET = min(DEFAULT_BUDGET_USD, 0.5)
MEAL_LABEL = {"lunch": "점심", "dinner": "저녁"}

_ADAPTER = TypeAdapter(EditCommand)


class Interpretation(BaseModel):
    commands: list[Any] = Field(default_factory=list)  # 검증을 통과한 EditCommand
    unsupported: list[str] = Field(default_factory=list)  # 현재 명령으로 표현할 수 없는 요청
    question: Optional[str] = None  # 모호해서 되묻는 질문
    error: Optional[str] = None  # Claude 호출 실패·예산 초과

    def notes(self) -> str:
        """화면에 보여줄 안내 문장 (명령으로 못 바꾼 요청, 질문, 오류)."""
        parts = []
        if self.error:
            parts.append(self.error)
        if self.unsupported:
            parts.append("아직 반영할 수 없는 요청입니다: " + "; ".join(self.unsupported))
        if self.question:
            parts.append(self.question)
        return " ".join(parts)


def _inline(node: Any, defs: dict[str, Any]) -> Any:
    """$ref를 풀고 strict 도구 스키마에 맞게 정리한다 (oneOf -> anyOf, 모든 필드 required)."""
    if isinstance(node, list):
        return [_inline(x, defs) for x in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return _inline(defs[node["$ref"].split("/")[-1]], defs)
    out: dict[str, Any] = {}
    for key, value in node.items():
        if key in ("title", "default", "discriminator", "$defs"):
            continue
        if key == "const":
            out["type"], out["enum"] = "string", [value]
        elif key == "oneOf":
            out["anyOf"] = _inline(value, defs)
        else:
            out[key] = _inline(value, defs)
    if out.get("type") == "object" and "properties" in out:
        out["required"] = list(out["properties"])
        out["additionalProperties"] = False
    return out


@lru_cache
def command_schema() -> dict[str, Any]:
    raw = TypeAdapter(EditCommand).json_schema()
    return _inline(raw, raw.get("$defs", {}))


@lru_cache
def record_tool() -> dict[str, Any]:
    return {
        "name": "record_commands",
        "description": "피드백을 수정 명령으로 바꾼 결과를 기록한다. 정확히 한 번 호출한다.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "commands": {"type": "array", "items": command_schema()},
                "unsupported": {"type": "array", "items": {"type": "string"}},
                "question": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            },
            "required": ["commands", "unsupported", "question"],
            "additionalProperties": False,
        },
    }


SYSTEM = """너는 부모님 여행 일정의 수정 요청을 정해진 수정 명령으로 바꾸는 변환기다.

- 일정을 직접 만들거나 바꾸지 마라. 사용자의 문장을 아래 도구의 명령 목록으로만 바꾼다.
- 명령에 쓰는 day는 1부터 시작하는 날짜 번호, place_id와 식당 끼니(meal)는 입력에 나온 값만 쓴다.
- 문장이 어느 날짜·장소·끼니인지 분명하지 않아 명령을 만들 수 없으면 commands를 비우고 question에 한국어 한 문장으로 되묻는다.
- 문장이 현재 명령으로 표현할 수 없는 요청이면 억지로 다른 명령에 끼워 맞추지 말고 unsupported에 요청 내용을 한국어로 짧게 적는다.
  (예: 특정 음식·재료를 피하고 싶다, 하루가 너무 비어 있으니 채워 달라, 식당 후보를 추천해 달라)
- 한 문장에 여러 요청이 있으면 가능한 것은 명령으로, 불가능한 것은 unsupported로 나눈다.
- 일정과 상관없는 말이면 commands와 unsupported를 비우고 question에 일정 수정 요청을 다시 받는 문장을 적는다.
- 판단이 끝나면 record_commands를 정확히 한 번 호출한다. 사용하지 않는 칸은 빈 배열 또는 null로 둔다.

명령 의미:
- lighten_day: 그날 관광지를 가벼운 코스로 바꿔 덜 걷게 한다.
- add_place / remove_place / move_place: 관광지 추가·제외·다른 날로 이동.
- set_mode: 한 관광지의 코스 방식(standard 표준, short 짧게, full 길게).
- more_korean_meals: 한식을 더 자주 먹는다.
- set_pace: 전체 일정 속도(slower 느리게, normal 보통, faster 빠르게).
- swap_restaurant: 그 날 그 끼니의 식당만 다른 곳으로 바꾼다.
- adjust_walk_limit: 한 번에 걷는 시간 한도를 늘리거나(more) 줄인다(less)."""


def summarize(itinerary: Itinerary) -> str:
    """Claude에게 보여줄 현재 일정 요약. 식당 리뷰 같은 상세 정보는 넣지 않는다."""
    places = load_places()
    lines = [f"여행 {itinerary.request.days}일"]
    for day in itinerary.days:
        parts = []
        for stop in day.stops:
            if stop.type == "attraction":
                name = places[stop.place_id].name if stop.place_id in places else stop.name
                label = f"{name}({stop.place_id})"
                if label not in parts:
                    parts.append(label)
            elif stop.type == "meal" and stop.restaurant:
                parts.append(f"{MEAL_LABEL.get(stop.meal, stop.meal)}: {stop.restaurant.name}")
        lines.append(f"{day.day}일차: " + (" / ".join(parts) if parts else "일정 없음"))
    in_plan = set(itinerary.request.place_ids)
    others = [f"{p.name}({p.id})" for p in places.values() if p.id not in in_plan]
    lines.append("일정에 없는 관광지: " + (", ".join(others) if others else "없음"))
    return "\n".join(lines)


@lru_cache
def _client() -> anthropic.Anthropic:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
    return anthropic.Anthropic()


class FeedbackInterpreter:
    def __init__(self, budget_usd: float = DEFAULT_BUDGET, client: Optional[anthropic.Anthropic] = None):
        self.budget = Budget(budget_usd)
        self._client = client

    @staticmethod
    def available() -> bool:
        """ANTHROPIC_API_KEY가 있으면 True (루트 .env도 읽는다)."""
        load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
        return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())

    @property
    def client(self) -> anthropic.Anthropic:
        return self._client or _client()

    def interpret(self, itinerary: Itinerary, feedback: str) -> Interpretation:
        text = feedback.strip()[:MAX_FEEDBACK_CHARS]
        if not text:
            return Interpretation(question="수정하고 싶은 내용을 알려주세요.")
        try:
            self.budget.check()
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM,
                messages=[{"role": "user", "content": f"현재 일정:\n{summarize(itinerary)}\n\n사용자 피드백:\n{text}"}],
                tools=[record_tool()],
                output_config={"effort": EFFORT},
            )
            self.budget.add(response.usage)
        except (anthropic.APIError, BudgetExceeded, RuntimeError) as exc:
            return Interpretation(error=f"피드백을 해석하지 못했습니다({type(exc).__name__}). 수정 명령으로 다시 보내주세요.")
        return parse_response(response.content)


def parse_response(content: list[Any]) -> Interpretation:
    """도구 호출을 읽고 명령을 검증한다. 검증에 실패한 명령은 unsupported로 옮긴다."""
    for block in content:
        if getattr(block, "type", None) == "tool_use" and block.name == "record_commands":
            data = block.input or {}
            commands, unsupported = [], list(data.get("unsupported") or [])
            for raw in data.get("commands") or []:
                try:
                    commands.append(_ADAPTER.validate_python(raw))
                except ValidationError:
                    unsupported.append(f"해석하지 못한 명령: {json.dumps(raw, ensure_ascii=False)}")
            return Interpretation(commands=commands, unsupported=unsupported, question=data.get("question"))
    return Interpretation(error="피드백을 해석하지 못했습니다(응답에 명령이 없습니다). 수정 명령으로 다시 보내주세요.")
