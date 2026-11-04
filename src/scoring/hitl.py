"""HITL(해커톤 단순화 버전): 사람이 고치고, AI가 근거로 다시 판단한다. 설계: docs/scoring-ai/hitl_design.md

- 점수(MD): 자연어 → Haiku가 조정안으로 구조화 → MD 주장을 human: 근거로 넣고 그 장소만 Sonnet 재채점
  (결과는 스테이징, 게시 안 함) → MD 승인 시 게시(scores_v2.json·scoring_scores·카탈로그)
- 일정(자녀·부모님): 기존 planner.refine으로 "제안"만 만들고 기록 → 승인 시 확정

원칙: 개인 피드백은 전체 점수를 바꾸지 않는다(MD를 거친다). LLM은 구조화·근거 판정만 하고 계산은 코드가 한다.
상용화 고도화안(임시 점수, 반복 조정 신호, 승인 맥락 기억 등): docs/scoring-ai/hitl_roadmap.md
"""
import json
import shutil
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from . import db
from .verify import DIMS
from .visit_modes import build_modes, load_modes

ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ROOT / "data/scoring/judge/v2"
STAGING = ROOT / "data/scoring/judge/hitl"
SCORES = ROOT / "data/scoring/scores_v2.json"
CATALOG = ROOT / "data/scoring/visit_modes_v2_2.json"

PARSE_MODEL = "claude-haiku-5-5"
PARSE_EFFORT = "low"
MAX_TEXT = 1000
MODES = ("standard", "short", "full")
REJUDGE_EFFORT = "medium"  # 2026-11-04 오행산 실험(high/medium/low) 후 결정. hitl_design.md 참고


def _now():
    return datetime.now(timezone.utc)


def new_id(prefix):
    return f"{prefix}-{_now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6]}"


class RateLimiter:
    """LLM을 쓰는 엔드포인트의 호출 제한(팀 크레딧 보호)."""

    def __init__(self, max_calls=20, window_s=3600, clock=time.monotonic):
        self.max_calls, self.window_s, self.clock = max_calls, window_s, clock
        self.calls: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = self.clock()
        recent = [t for t in self.calls[key] if now - t < self.window_s]
        self.calls[key] = recent
        if len(recent) >= self.max_calls:
            return False
        recent.append(now)
        return True


# ── 점수: MD 자연어 해석 (Haiku 1회) ─────────────────────────────

SCORE_SYSTEM = """너는 여행사 상품 담당자(MD)의 관광지 난이도 의견을 정해진 형식으로 바꾸는 변환기다.

- 점수를 새로 판단하지 마라. MD가 말한 내용을 구조화만 한다. 판정은 나중에 별도 채점기가 근거로 한다.
- place_id는 입력 목록에 있는 값만 쓴다. dimension은 climb(계단·오르막), walking(보행 거리·시간), heat(더위 노출), crowd(혼잡) 중 하나.
- mode는 MD가 특정 관람 방식을 말했을 때만 standard/short/full, 아니면 all.
- score는 MD가 숫자를 말하면 그 값, 방향만 말하면("더 힘들다", "과대평가") 현재 점수에서 1점 올리거나 내린 값(1~10).
- claim은 MD가 말한 사실을 한국어 한 문장으로(근거로 저장된다). 추측을 덧붙이지 마라.
- 어느 장소·차원인지 분명하지 않으면 adjustments를 비우고 question에 한국어 한 문장으로 되묻는다.
- 판단이 끝나면 record_score_feedback을 정확히 한 번 호출한다."""


def score_tool():
    adj = {"type": "object", "additionalProperties": False,
           "required": ["place_id", "dimension", "mode", "score", "claim"],
           "properties": {"place_id": {"type": "string"},
                          "dimension": {"type": "string", "enum": list(DIMS)},
                          "mode": {"type": "string", "enum": [*MODES, "all"]},
                          "score": {"type": "integer"},
                          "claim": {"type": "string"}}}
    return {"name": "record_score_feedback", "strict": True,
            "description": "MD 의견을 점수 조정 제안으로 기록한다. 정확히 한 번 호출한다.",
            "input_schema": {"type": "object", "additionalProperties": False,
                             "required": ["adjustments", "question"],
                             "properties": {"adjustments": {"type": "array", "items": adj},
                                            "question": {"anyOf": [{"type": "string"}, {"type": "null"}]}}}}


def catalog_summary(catalog):
    lines = []
    for pid, place in catalog.items():
        std = place["modes"]["standard"]["dimensions"]
        dims = " ".join(f"{d}={std[d]['score']}" for d in DIMS)
        lines.append(f"{pid} {place['name_ko']}: 표준 {dims} (방식: " +
                     ", ".join(f"{m}={place['modes'][m]['name']}" for m in MODES) + ")")
    return "\n".join(lines)


def _client():
    import anthropic

    db.load_env()
    return anthropic.Anthropic()


def interpret_score(text, catalog, client=None):
    """MD 자연어 → {adjustments, question, usage}. 검증 실패 항목은 버리고 question으로 되묻는다."""
    text = (text or "").strip()[:MAX_TEXT]
    if not text:
        return {"adjustments": [], "question": "조정하려는 관광지와 내용을 알려주세요.", "usage": None}
    client = client or _client()
    resp = client.messages.create(
        model=PARSE_MODEL, max_tokens=2000, system=SCORE_SYSTEM,
        messages=[{"role": "user", "content": f"관광지 목록(현재 점수):\n{catalog_summary(catalog)}\n\nMD 의견:\n{text}"}],
        tools=[score_tool()], tool_choice={"type": "auto"}, output_config={"effort": PARSE_EFFORT})
    usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens,
             "model": PARSE_MODEL}
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "record_score_feedback":
            data = block.input or {}
            ok, bad = [], []
            for a in data.get("adjustments") or []:
                if a.get("place_id") in catalog and a.get("dimension") in DIMS and 1 <= int(a.get("score", 0)) <= 10:
                    ok.append({**a, "mode": None if a.get("mode") == "all" else a.get("mode")})
                else:
                    bad.append(a)
            question = data.get("question")
            if bad and not question:
                question = "일부 의견을 해석하지 못했습니다. 관광지 이름과 항목(계단·보행·더위·혼잡)을 함께 적어 주세요."
            return {"adjustments": ok, "question": question, "usage": usage}
    return {"adjustments": [], "question": "의견을 해석하지 못했습니다. 다시 적어 주세요.", "usage": usage}


# ── 저장소 ──────────────────────────────────────────────────────

def get_feedback(conn, fid):
    rows = db.query(conn, "select * from scoring_feedback where id=%s", (fid,))
    if not rows:
        raise KeyError(fid)
    return rows[0]


def _save(conn, row):
    db.upsert(conn, "scoring_feedback", [row])


def _decide(conn, fid, status, approver):
    conn.execute("update scoring_feedback set status=%s, approved_by=%s, decided_at=%s where id=%s",
                 (status, approver, _now(), fid))


def _jsonb(v):
    from psycopg.types.json import Jsonb

    return Jsonb(json.loads(db.dumps(v)))


def _mode_scores(catalog, pid):
    return {m: catalog[pid]["modes"][m]["score"] for m in MODES}


# ── 점수 조정: 의견 → 재채점 → 승인 ──────────────────────────────

def propose_score(conn, text, actor_id=None, interpreter=interpret_score):
    """MD 의견을 조정안으로 바꿔 기록한다(점수는 아직 안 바뀜). LLM: Haiku 1회."""
    catalog = load_modes(CATALOG)
    parsed = interpreter(text, catalog)
    if not parsed["adjustments"]:
        return {"feedback_id": None, "question": parsed["question"], "usage": parsed["usage"]}
    places = sorted({a["place_id"] for a in parsed["adjustments"]})
    fid = new_id("fb")
    before = {pid: _mode_scores(catalog, pid) for pid in places}
    _save(conn, dict(id=fid, created_at=_now(), actor_role="md", actor_id=actor_id, target="score",
                     place_id=places[0] if len(places) == 1 else None, plan_ref=None, raw_text=text,
                     parsed={"adjustments": parsed["adjustments"], "question": parsed["question"]},
                     status="proposed", approved_by=None, decided_at=None,
                     before_json=before, after_json=None, llm_usage={"parse": parsed["usage"]}))
    return {"feedback_id": fid, "status": "proposed", "adjustments": parsed["adjustments"],
            "question": parsed["question"], "before": before, "usage": parsed["usage"]}


def human_evidence(fid, adjustments):
    return [dict(id=f"human:{fid}:{i}", place_id=a["place_id"], dimension=a["dimension"], basis="B",
                 metric="md_field_report", value={"suggested_score": int(a["score"]), "mode": a["mode"] or "all"},
                 unit=None, text=a["claim"], source="hanatour_md", source_url=None,
                 caveat="여행사 MD 현장 보고(1인). 웹 검색으로 교차 확인 필요.", updated_at=_now())
            for i, a in enumerate(adjustments)]


def human_review(fid, runs):
    """AI가 MD 의견을 어떻게 다뤘는지: 근거로 인용(cited) / 검토했지만 인용 안 함(reviewed) / 언급 없음.

    차원별 rationale에서 의견 ID를 언급한 문장을 그대로 돌려준다(화면에 "AI가 이렇게 판단했다"로 표시).
    """
    tag = f"human:{fid}:"
    out = {}
    for r in runs:
        for dim, d in (r["output"].get("dimensions") or {}).items():
            if not isinstance(d, dict):
                continue
            cited = any(str(i).startswith(tag) for i in d.get("evidence_ids", []))
            note = d.get("rationale") or ""
            # judge가 ID 없이 "MD의 보고"처럼 쓰는 경우도 있다(effort medium 실험) → 'MD' 언급도 검토로 본다
            if cited or tag in note or "MD" in note:
                out[dim] = {"verdict": "cited" if cited else "reviewed", "run_index": r["run_index"],
                            "rationale": note}
    return out


def rejudge(conn, fid, max_runs=3, judge_fn=None, effort=REJUDGE_EFFORT):
    """MD 주장을 human: 근거로 넣고 해당 장소만 재채점(스테이징, 게시 안 함). LLM: Sonnet 1~3회."""
    from .run_judge import aggregate_site, judge_site

    fb = get_feedback(conn, fid)
    if fb["target"] != "score" or fb["status"] not in ("proposed", "rejudged"):
        raise ValueError(f"재채점할 수 없는 상태입니다: {fb['status']}")
    adjustments = fb["parsed"]["adjustments"]
    db.upsert(conn, "scoring_evidence", human_evidence(fid, adjustments))
    results, usage = {}, []
    for pid in sorted({a["place_id"] for a in adjustments}):
        if judge_fn is None:
            from .judge import judge as _judge
            judge_fn = lambda site, c, run_index=1: _judge(site, c, run_index=run_index, effort=effort)  # noqa: E731
        runs = judge_site(conn, pid, max_runs=max_runs, out_dir=STAGING / fid, judge_fn=judge_fn)
        agg = aggregate_site(conn, pid, runs)
        cited = sorted({i for r in runs for d in (r["output"].get("dimensions") or {}).values()
                        if isinstance(d, dict) for i in d.get("evidence_ids", []) if str(i).startswith("human:")})
        results[pid] = {"aggregate": json.loads(db.dumps(agg)), "run_ids": [r["run_id"] for r in runs],
                        "human_cited": cited, "human_review": human_review(fid, runs)}
        usage += [r.get("usage") for r in runs]
    after = {pid: {"composite": r["aggregate"]["composite"], "dimensions": r["aggregate"]["dimensions"],
                   "status": r["aggregate"]["status"], "human_cited": r["human_cited"],
                   "human_review": r["human_review"]}
             for pid, r in results.items()}
    conn.execute("update scoring_feedback set status='rejudged', after_json=%s, llm_usage=%s where id=%s",
                 (_jsonb({"results": results}), _jsonb({**(fb["llm_usage"] or {}), "rejudge": usage}), fid))
    return {"feedback_id": fid, "status": "rejudged", "before": fb["before_json"], "after": after}


def approve_score(conn, fid, approver=None, run_dir=RUN_DIR, scores_path=SCORES, catalog_path=CATALOG):
    """재채점 결과를 게시하고 카탈로그를 다시 만든다. 기존 실행 기록은 archive로 옮겨 되돌릴 수 있게 둔다."""
    from .run_judge import publish_site

    fb = get_feedback(conn, fid)
    if fb["status"] != "rejudged":
        raise ValueError("재채점 결과가 있어야 승인할 수 있습니다. 먼저 재채점을 실행하세요.")
    run_dir, stage = Path(run_dir), STAGING / fid
    for pid, r in fb["after_json"]["results"].items():
        backup = run_dir / "archive_hitl" / fid
        backup.mkdir(parents=True, exist_ok=True)
        for old in run_dir.glob(f"{pid}_run*.json"):
            shutil.move(str(old), backup / old.name)
        for new in stage.glob(f"{pid}_run*.json"):
            shutil.copy2(new, run_dir / new.name)
        publish_site(conn, pid, r["aggregate"], scores_path)
    scores = json.loads(Path(scores_path).read_text(encoding="utf-8"))
    Path(catalog_path).write_text(db.dumps(build_modes(scores, run_dir)), encoding="utf-8")
    _decide(conn, fid, "applied", approver)
    try:  # 일정 엔진이 새 점수를 읽도록
        from src.planner.sources import load_places
        load_places.cache_clear()
    except ImportError:
        pass
    return {"feedback_id": fid, "status": "applied"}


def reject(conn, fid, approver=None):
    fb = get_feedback(conn, fid)
    if fb["status"] in ("applied", "rejected"):
        raise ValueError(f"이미 처리된 조정입니다: {fb['status']}")
    _decide(conn, fid, "rejected", approver)
    if fb["target"] == "score":
        conn.execute("delete from scoring_evidence where id like %s", (f"human:{fid}:%",))
    return {"feedback_id": fid, "status": "rejected"}


# ── 일정 조정: 제안 → 승인 ───────────────────────────────────────

def _metrics(it):
    return {"peak": it.package.peak if it.package else None, "mean": it.package.mean if it.package else None,
            "days": [d.difficulty for d in it.days], "place_ids": list(it.request.place_ids)}


def propose_itinerary(conn, itinerary, commands, feedback, actor_role, actor_id=None, interpreter=None):
    """기존 refine으로 제안만 만들고 기록한다. 적용은 approve_itinerary에서. LLM: 자연어면 Haiku 1회."""
    from src.planner.edit import refine

    resp = refine(itinerary, commands, feedback, interpreter=interpreter)
    if not resp.applied_commands:  # 되묻기·오류: 기록하지 않고 그대로 돌려준다
        return {"feedback_id": None, "response": resp}
    fid = new_id("fb")
    budget = getattr(interpreter, "budget", None)
    _save(conn, dict(id=fid, created_at=_now(), actor_role=actor_role, actor_id=actor_id, target="itinerary",
                     place_id=None, plan_ref=itinerary.plan_id, raw_text=feedback,
                     parsed={"commands": [c.model_dump() for c in resp.applied_commands],
                             "summary": resp.change_summary},
                     status="proposed", approved_by=None, decided_at=None,
                     before_json=_metrics(itinerary),
                     after_json={"metrics": _metrics(resp.itinerary),
                                 "itinerary": resp.itinerary.model_dump(mode="json")},
                     llm_usage={"parse_usd": round(budget.spent_usd, 6), "calls": budget.calls} if budget else None))
    return {"feedback_id": fid, "response": resp}


def approve_itinerary(conn, fid, approver=None):
    """제안된 일정을 확정해 돌려준다."""
    from src.planner.schema import Itinerary

    fb = get_feedback(conn, fid)
    if fb["target"] != "itinerary" or fb["status"] != "proposed":
        raise ValueError(f"승인할 수 없는 상태입니다: {fb['status']}")
    _decide(conn, fid, "applied", approver)
    return Itinerary.model_validate(fb["after_json"]["itinerary"])


def history(conn, place_id: Optional[str] = None, limit=50) -> list[dict[str, Any]]:
    sql = ("select id, created_at, actor_role, target, place_id, plan_ref, raw_text, parsed, status, "
           "before_json, llm_usage from scoring_feedback")
    params: tuple = ()
    if place_id:
        sql += " where place_id=%s"
        params = (place_id,)
    return db.query(conn, sql + " order by created_at desc limit %s", (*params, limit))
