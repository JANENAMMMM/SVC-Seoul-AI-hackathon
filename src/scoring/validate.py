"""Produce the Korean validation report."""
from collections import Counter
from pathlib import Path

from .engine import grade_all
from .features import ROOT


def rank(values):
    return [sum(x > y for y in values) + (sum(x == y for y in values) + 1) / 2 for x in values]


def spearman(pairs):
    if len(pairs) < 2:
        return None
    x, y = rank([a for a, _ in pairs]), rank([b for _, b in pairs])
    mx, my = sum(x) / len(x), sum(y) / len(y)
    top = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sx = sum((a - mx) ** 2 for a in x) ** .5
    sy = sum((b - my) ** 2 for b in y) ** .5
    return top / (sx * sy) if sx and sy else None


def validate(features, grades, path=None):
    n = len(grades)
    lines = ["# ScoringAI 검증 보고서", "", "기준 버전 1.0 · 기본 방문 월 7월 · D5 혼잡은 표시만 함.",
             "", "## 차원별 결측과 채택 근거", "", "| 차원 | 결측 | A | B | C |", "|---|---:|---:|---:|---:|"]
    for dim in (f"D{i}" for i in range(1, 6)):
        counts = Counter(g["dimensions"][dim].get("basis") for g in grades)
        lines.append(f"| {dim} | {counts[None]}/{n} ({counts[None]/n:.0%}) | {counts['A']} | {counts['B']} | {counts['C']} |")
    pairs = []
    for g in grades:
        for dim in ("D1", "D2", "D3", "D4", "D5"):
            rec = g["dimensions"][dim]
            if rec.get("basis") in ("A", "B"):
                pairs.extend((rec["level"], c["level"]) for c in rec["checks"] if c["basis"] == "C")
    rho = spearman(pairs)
    lines += ["", "## A·B 대 C 비교", "", "C 근거와 비교 가능한 차원별 근거 쌍을 집계했습니다. 동일 관광지의 여러 C 출처는 각각 한 쌍입니다.", "",
              f"- 비교 쌍: {len(pairs)}", f"- 정확한 수준 일치율: {sum(a == b for a,b in pairs)/len(pairs):.1%}" if pairs else "- 정확한 수준 일치율: 계산 불가",
              f"- 스피어만 상관: {rho:.3f}" if rho is not None else "- 스피어만 상관: 계산 불가 (표본 또는 분산 부족)",
              "", "## 기준값 민감도", "", "| 기준 배율 | 등급 변경 관광지 수 |", "|---:|---:|"]
    for scale in (.8, 1.2):
        changed = sum(a["grade_score"] != b["grade_score"] for a, b in zip(grades, grade_all(features, scale=scale, write=False)))
        lines.append(f"| {scale:.1f} | {changed}/{n} |")
    lines += ["", "## 전체 관광지 등급", "", "| ID | 관광지 | 등급 | 핵심 근거 | 상태 |", "|---|---|---|---|---|"]
    for g in grades:
        evidence = []
        for dim in ("D1", "D2", "D4"):
            d = g["dimensions"][dim]
            if d.get("basis"):
                evidence.append(f"{dim} {d['basis']} {d['value']}{d['unit']}→{d['level']}")
        lines.append(f"| {g['id']} | {g['name_ko']} | {g['grade']} | {', '.join(evidence) or '근거 없음'} | {g['status']} |")
    lines += ["", "결측 차원과 근거 간 2단계 이상 차이는 `needs_review`로 남겼습니다. OSM 자료가 추가되면 다시 실행해야 합니다."]
    path = Path(path) if path else ROOT / "docs/scoring-ai/archive/v1-rule-engine/validation_report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines
