"""HITL 피드백 루프: 유저(자녀·부모님)와 MD가 AI 산출물을 조정하고, 그 조정이 다음 판단에 반영된다.

조정 두 갈래 (설계: docs/scoring-ai/hitl_design.md)
- 점수(MD): 자연어 → Haiku가 구조화(장소·차원·점수·주장) → 임시 점수(scoring_overrides)로 즉시 표시
  → [재채점 버튼] MD 주장을 human: 근거로 넣고 그 장소만 Sonnet judge 재채점(스테이징)
  → MD 승인 시 게시(scores_v2.json·scoring_scores·카탈로그), 임시 점수 해제
- 일정(자녀, 부모님 의견 포함): 자연어/명령 → 기존 planner.refine으로 "제안"만 만들고 기록
  → 승인 시 적용. 승인된 조정은 다음 자연어 해석의 맥락(state.feedback_log)과
    장소별 신호(signals: 여러 가족이 가볍게 바꾼 곳 → MD 재채점 검토)로 쓰인다.

원칙: 개인 피드백은 전체 점수를 직접 바꾸지 않는다(MD를 거친다). LLM은 수치를 계산하지 않고
구조화·근거 기반 판정만 한다. 모든 쓰기는 scoring_ 테이블과 data/scoring 파일에만 한다.
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
from .visit_modes import build_modes, load_catalog, load_modes, overrides_path

ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ROOT / "data/scoring/judge/v2"
STAGING = ROOT / "data/scoring/judge/hitl"
SCORES = ROOT / "data/scoring/scores_v2.json"
CATALOG = ROOT / "data/scoring/visit_modes_v2_2.json"

PARSE_MODEL = "claude-haiku-5-5"
PARSE_EFFORT = "low"
MAX_TEXT = 1000
SIGNAL_THRESHOLD = 3  # 서로 다른 일정에서 같은 장소를 가볍게 바꾼 횟수
MODES = ("standard", "short", "full")


def _now():
    return datetime.now(timezone.utc)


def new_id(prefix):
    return f"{prefix}-{_now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6]}"


# ── 호출 제한 (LLM을 쓰는 엔드포인트) ─────────────────────────────

class RateLimiter:
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


# ── 점수 피드백 해석 (Haiku 1회) ─────────────────────────────────

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

def active_overrides(conn):
    return db.query(conn, "select id, feedback_id, place_id, mode, dimension, score, reason "
                          "from scoring_overrides where active order by created_at")


def sync_overrides(conn):
    """DB의 활성 임시 점수를 런타임 카탈로그용 JSON으로 내보낸다(planner·API가 DB 없이 읽음)."""
    rows = active_overrides(conn)
    path = overrides_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(db.dumps(rows), encoding="utf-8")
    _clear_runtime_caches()
    return rows


def _clear_runtime_caches():
    try:
        from src.planner.sources import load_places
        load_places.cache_clear()
    except ImportError:
        pass


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


def _mode_scores(catalog, pid):
    return {m: catalog[pid]["modes"][m]["score"] for m in MODES}


# ── 점수 조정 흐름 ───────────────────────────────────────────────

def propose_score(conn, text, actor_id=None, interpreter=interpret_score):
    """MD 의견 → 제안 기록 + 임시 점수(즉시 표시). LLM: Haiku 1회."""
    verified = load_modes(CATALOG)
    parsed = interpreter(text, verified)
    if not parsed["adjustments"]:
        return {"feedback_id": None, "question": parsed["question"], "usage": parsed["usage"]}
    places = sorted({a["place_id"] for a in parsed["adjustments"]})
    fid = new_id("fb")
    before = {pid: _mode_scores(verified, pid) for pid in places}
    _save(conn, dict(id=fid, created_at=_now(), actor_role="md", actor_id=actor_id, target="score",
                     place_id=places[0] if len(places) == 1 else None, plan_ref=None, raw_text=text,
                     parsed={"adjustments": parsed["adjustments"], "question": parsed["question"]},
                     status="proposed", approved_by=None, decided_at=None,
                     before_json=before, after_json=None, llm_usage={"parse": parsed["usage"]}))
    db.upsert(conn, "scoring_overrides", [
        dict(id=f"{fid}:{i}", feedback_id=fid, place_id=a["place_id"], mode=a["mode"],
             dimension=a["dimension"], score=int(a["score"]), reason=a["claim"], active=True, created_at=_now())
        for i, a in enumerate(parsed["adjustments"])])
    sync_overrides(conn)
    provisional = load_catalog(CATALOG)
    return {"feedback_id": fid, "status": "proposed", "adjustments": parsed["adjustments"],
            "question": parsed["question"], "before": before,
            "provisional": {pid: _mode_scores(provisional, pid) for pid in places},
            "usage": parsed["usage"]}


def human_evidence(fid, adjustments):
    return [dict(id=f"human:{fid}:{i}", place_id=a["place_id"], dimension=a["dimension"], basis="B",
                 metric="md_field_report", value={"suggested_score": int(a["score"]), "mode": a["mode"] or "all"},
                 unit=None, text=a["claim"], source="hanatour_md", source_url=None,
                 caveat="여행사 MD 현장 보고(1인). 웹 검색으로 교차 확인 필요.", updated_at=_now())
            for i, a in enumerate(adjustments)]


def rejudge(conn, fid, max_runs=3, judge_fn=None):
    """MD 주장을 human: 근거로 넣고 해당 장소만 재채점(스테이징, 게시 안 함). LLM: Sonnet 1~3회."""
    from .run_judge import aggregate_site, judge_site

    fb = get_feedback(conn, fid)
    if fb["target"] != "score" or fb["status"] not in ("proposed", "rejudged"):
        raise ValueError(f"재채점할 수 없는 상태입니다: {fb['status']}")
    adjustments = fb["parsed"]["adjustments"]
    db.upsert(conn, "scoring_evidence", human_evidence(fid, adjustments))
    results, usage = {}, []
    for pid in sorted({a["place_id"] for a in adjustments}):
        stage = STAGING / fid
        runs = judge_site(conn, pid, max_runs=max_runs, out_dir=stage, judge_fn=judge_fn)
        agg = aggregate_site(conn, pid, runs)
        cited = sorted({i for r in runs for d in (r["output"].get("dimensions") or {}).values()
                        if isinstance(d, dict) for i in d.get("evidence_ids", []) if str(i).startswith("human:")})
        results[pid] = {"aggregate": json.loads(db.dumps(agg)), "run_ids": [r["run_id"] for r in runs],
                        "human_cited": cited}
        usage += [r.get("usage") for r in runs]
    after = {pid: {"composite": r["aggregate"]["composite"], "dimensions": r["aggregate"]["dimensions"],
                   "status": r["aggregate"]["status"], "human_cited": r["human_cited"]}
             for pid, r in results.items()}
    conn.execute("update scoring_feedback set status='rejudged', after_json=%s, llm_usage=%s where id=%s",
                 (_jsonb({"results": results}), _jsonb({**(fb["llm_usage"] or {}), "rejudge": usage}), fid))
    return {"feedback_id": fid, "status": "rejudged", "after": after}


def _jsonb(v):
    from psycopg.types.json import Jsonb

    return Jsonb(json.loads(db.dumps(v)))


def _deactivate(conn, fid):
    conn.execute("update scoring_overrides set active=false where feedback_id=%s", (fid,))
    sync_overrides(conn)


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
    _deactivate(conn, fid)
    return {"feedback_id": fid, "status": "applied"}


def reject(conn, fid, approver=None):
    fb = get_feedback(conn, fid)
    if fb["status"] in ("applied", "rejected"):
        raise ValueError(f"이미 처리된 조정입니다: {fb['status']}")
    _decide(conn, fid, "rejected", approver)
    if fb["target"] == "score":
        _deactivate(conn, fid)
        conn.execute("delete from scoring_evidence where id like %s", (f"human:{fid}:%",))
    return {"feedback_id": fid, "status": "rejected"}


# ── 일정 조정 흐름 ───────────────────────────────────────────────

def lighter_places(before, after):
    """조정으로 더 가벼워진 관광지: short로 바뀌었거나 일정에서 빠진 곳."""
    out = set(before.request.place_ids) - set(after.request.place_ids)
    bm, am = before.state.mode_overrides, after.state.mode_overrides
    out |= {p for p, m in am.items() if m == "short" and bm.get(p) != "short"}
    return sorted(out)


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
    lighter = lighter_places(itinerary, resp.itinerary)
    usage = getattr(interpreter, "budget", None)
    _save(conn, dict(id=fid, created_at=_now(), actor_role=actor_role, actor_id=actor_id, target="itinerary",
                     place_id=lighter[0] if len(lighter) == 1 else None, plan_ref=itinerary.plan_id,
                     raw_text=feedback, parsed={"commands": [c.model_dump() for c in resp.applied_commands],
                                                "lighter_places": lighter, "summary": resp.change_summary},
                     status="proposed", approved_by=None, decided_at=None,
                     before_json=_metrics(itinerary),
                     after_json={"metrics": _metrics(resp.itinerary),
                                 "itinerary": resp.itinerary.model_dump(mode="json")},
                     llm_usage={"parse_usd": round(usage.spent_usd, 6), "calls": usage.calls} if usage else None))
    return {"feedback_id": fid, "response": resp}


def approve_itinerary(conn, fid, approver=None):
    """제안된 일정을 확정한다. 승인된 요청은 feedback_log에 남아 다음 자연어 해석의 맥락이 된다."""
    from src.planner.schema import Itinerary

    fb = get_feedback(conn, fid)
    if fb["target"] != "itinerary" or fb["status"] != "proposed":
        raise ValueError(f"승인할 수 없는 상태입니다: {fb['status']}")
    it = Itinerary.model_validate(fb["after_json"]["itinerary"])
    note = (fb["raw_text"] or "") + (" → " if fb["raw_text"] else "") + (fb["parsed"].get("summary") or "").replace("\n", "; ")
    it.state.feedback_log = [*it.state.feedback_log, note.strip()][-10:]
    it.request.state.feedback_log = list(it.state.feedback_log)
    _decide(conn, fid, "applied", approver)
    return it


def signals(conn, threshold=SIGNAL_THRESHOLD):
    """여러 일정에서 반복해서 가볍게 바뀐 관광지 → MD 재채점 검토 후보."""
    rows = db.query(conn, "select plan_ref, parsed from scoring_feedback "
                          "where target='itinerary' and status='applied'")
    plans = defaultdict(set)
    for r in rows:
        for pid in (r["parsed"] or {}).get("lighter_places", []):
            plans[pid].add(r["plan_ref"])
    catalog = load_modes(CATALOG)
    return sorted(({"place_id": pid, "name_ko": catalog.get(pid, {}).get("name_ko", pid),
                    "plans": len(refs), "review_suggested": len(refs) >= threshold}
                   for pid, refs in plans.items()), key=lambda x: -x["plans"])


def history(conn, place_id: Optional[str] = None, limit=50) -> list[dict[str, Any]]:
    sql = ("select id, created_at, actor_role, target, place_id, plan_ref, raw_text, parsed, status, "
           "before_json, llm_usage from scoring_feedback")
    params: tuple = ()
    if place_id:
        sql += " where place_id=%s"
        params = (place_id,)
    return db.query(conn, sql + " order by created_at desc limit %s", (*params, limit))
