"""Derive named visit modes from the already verified v2.2 score snapshot."""
import json
from pathlib import Path

from src.scoring.provenance import explanations, snapshot_runs
from src.scoring.verify import DIMS, WEIGHTS, round_half_up


MODE_NAMES = {
    "dad-01": ("이동수단 이용·핵심 구역", "계단·전 구역 관람"),
    "dad-02": ("엘리베이터·사원 일부", "계단·동굴·정상 전체"),
    "dad-03": ("핵심 구간·시클로", "골목·시장 전체 도보"),
    "dad-04": ("상단 주차장·본당", "하부 주차장·정원 전체"),
    "dad-05": ("포장 산책로 짧게", "모래 해변 길게"),
    "dad-06": ("하차 지점 인근 관람", "강변·야시장 연계 도보"),
    "dad-07": ("1층만 짧게", "1·2층 전체 관람"),
    "dad-08": ("외관만 짧게", "내부·주변 도보 연계"),
    "dad-09": ("핵심 갤러리만", "전 갤러리·마당 관람"),
    "dad-10": ("썬휠 중심", "테마존 전체 도보"),
    "dad-11": ("셔틀·온천 중심", "셔틀 없이 전 구역 도보"),
    "dad-12": ("전동차·주요 유적", "전동차 없이 전체 순환"),
    "dad-13": ("주차장 인근 전망", "관문·벙커 전체 관람"),
    "dad-14": ("입구 주변 짧게", "구시가지·강변 연계"),
    "dad-15": ("바구니배만", "자전거·쿠킹클래스 결합"),
}


def build_modes(scores, run_dir):
    """Build three route modes per place; heat/crowd stay at typical conditions."""
    result = {}
    for place_id, place in scores.items():
        source = explanations(place, snapshot_runs(place_id, run_dir))
        modes = {}
        for mode_id, name in zip(("short", "full"), MODE_NAMES[place_id]):
            levels = {d: ("lower" if mode_id == "short" else "upper")
                      if d in ("climb", "walking") else "typical" for d in DIMS}
            modes[mode_id] = _mode(place_id, name, levels, place, source)
        modes = {"standard": _mode(place_id, "표준 관람", {d: "typical" for d in DIMS},
                                   place, source), **modes}
        assert modes["standard"]["score"] == place["composite"]["typical"]
        result[place_id] = {"name_ko": place["name_ko"], "status": place["status"], "modes": modes}
    return result


def _mode(place_id, name, levels, place, source):
    dimensions = {}
    for d, level in levels.items():
        conditions = source[d].get(f"{level}_conditions", [])
        if level != "typical" and not conditions:
            level = "typical"
        if level != "typical" and place["dimensions"][d][level] != place["dimensions"][d]["typical"]:
            ids = list(dict.fromkeys(i for c in conditions for i in c["evidence_ids"]))
        else:
            ids = source[d]["evidence_ids"]
        if not ids:
            raise ValueError(f"Missing verified evidence: {place_id}.{d}.{level}")
        dimensions[d] = {"score": place["dimensions"][d][level], "level": level,
                         "evidence_ids": ids, "conditions": [c["condition"] for c in conditions],
                         "source_run_id": source[d]["run_id"], "source_run_index": source[d]["run_index"]}
    score = round_half_up(sum(WEIGHTS[d] * dimensions[d]["score"] for d in DIMS) / 9)
    return {"name": name, "score": score, "dimensions": dimensions}


def load_modes(path=None):
    path = Path(path) if path else Path(__file__).resolve().parents[2] / "data/scoring/visit_modes_v2_2.json"
    return json.loads(path.read_text(encoding="utf-8"))
