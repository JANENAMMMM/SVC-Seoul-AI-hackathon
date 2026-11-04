"""HITL 발표용 슬라이드 그림 2장(MD 점수 재판단, 자녀·부모님 일정 승인) (1920x1080 SVG + PNG). 하나투어 보라(#5e2bb8, hanatour.com CSS 최다 사용색) 기준.

가독성 규칙(발표용 프로세스 그림 가이드 참고): 한 장에 한 메시지, 단계 3개, 단계당 제목 한 줄 + 설명 한 줄,
본문 26px 이상, 색은 보라 1색 + 회색. 사람 단계 = 흰 바탕 보라 테두리, AI 단계 = 보라로 채움.
usage: python gen_hitl_slides.py [out_dir]
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_workflow import esc, render  # noqa: E402

W, H = 1920, 1080
FONT = "Pretendard, 'Noto Sans KR', 'Malgun Gothic', sans-serif"
PURPLE, PURPLE_DARK, SOFT = "#5e2bb8", "#4b2293", "#f6f2fb"
INK, SUB, LINE = "#111111", "#5b6070", "#e5e5e5"


class S:
    def __init__(self):
        self.o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">',
                  f'<defs><marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{PURPLE}"/></marker></defs>',
                  f'<rect width="{W}" height="{H}" fill="#ffffff"/>']

    def t(self, x, y, s, size, color=INK, weight=400, anchor="start"):
        self.o.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{esc(s)}</text>')

    def header(self, kicker, title):
        self.t(120, 150, kicker, 30, PURPLE, 700)
        self.t(120, 232, title, 60, INK, 800)

    def step(self, x, y, n, title, sub, ai=False, w=480, h=300):
        fill, stroke, tc, sc = (PURPLE, PURPLE, "#ffffff", "#ffffff") if ai else ("#ffffff", PURPLE, INK, SUB)
        self.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="28" fill="{fill}" stroke="{stroke}" stroke-width="4"/>')
        cx, cy = x + 70, y + 70
        self.o.append(f'<circle cx="{cx}" cy="{cy}" r="34" fill="{"#ffffff" if ai else PURPLE}"/>')
        self.t(cx, cy + 12, str(n), 34, PURPLE if ai else "#ffffff", 800, "middle")
        self.t(x + 120, cy + 12, "AI" if ai else "사람", 26, "#ffffff" if ai else PURPLE, 700)
        self.t(x + 40, y + 185, title, 44, tc, 800)
        for i, line in enumerate(sub):
            self.t(x + 40, y + 240 + i * 40, line, 28, sc)

    def arrow(self, x1, x2, y):
        self.o.append(f'<path d="M{x1},{y} H{x2}" stroke="{PURPLE}" stroke-width="6" fill="none" marker-end="url(#ar)"/>')

    def callout(self, y, label, text, h=210):
        self.o.append(f'<rect x="120" y="{y}" width="{W - 240}" height="{h}" rx="24" fill="{SOFT}"/>')
        self.t(170, y + 70, label, 28, PURPLE, 700)
        for i, line in enumerate(text):
            self.t(170, y + 122 + i * 44, line, 32, INK, 500)

    def save(self, p):
        self.o.append("</svg>")
        Path(p).write_text("\n".join(self.o), encoding="utf-8")


def three(s, steps, y=330):
    xs = (120, 720, 1320)
    for x, (n, title, sub, ai) in zip(xs, steps):
        s.step(x, y, n, title, sub, ai)
    s.arrow(610, 708, y + 150)
    s.arrow(1210, 1308, y + 150)


def slide_md(p):
    s = S()
    s.header("하나투어 MD", "현장 의견을 AI가 확인하고 다시 판단합니다")
    three(s, [(1, "의견 입력", ["\"오행산 엘리베이터", "점검이 잦아요\""], False),
              (2, "웹으로 확인·재채점", ["의견은 근거 1건으로만", "최근 리뷰·웹과 비교"], True),
              (3, "MD 승인", ["전후 등급·근거 확인", "승인해야 점수 반영"], False)])
    s.callout(720, "실제 결과 (오행산)", ["AI: 2026년 7~9월 리뷰에서는 엘리베이터 정상 운행 → 보통 점수 유지,",
                                         "운휴 상황은 '최악 조건'에만 반영. 사람 말을 그대로 믿지 않습니다."])
    s.t(120, 1000, "재검증 1곳 약 90원 · 그 관광지가 들어간 모든 상품에 적용", 28, SUB)
    s.save(p)


def slide_family(p):
    s = S()
    s.header("자녀 · 부모님", "의견은 미리보기로, 승인해야 바뀝니다")
    three(s, [(1, "의견 또는 버튼", ["\"엄마가 2일차", "힘들대요\""], False),
              (2, "일정 다시 짜기", ["말을 수정 명령으로 바꾸고", "엔진이 새 일정 계산"], True),
              (3, "자녀 승인", ["바뀐 점 미리보기", "승인 전엔 그대로"], False)])
    s.callout(720, "예시", ["그날 오행산 '표준 관람' → '엘리베이터·사원 일부' 코스",
                           "용다리·대성당도 짧은 코스로 바뀌고, 하루 난이도를 전후로 비교합니다."])
    s.t(120, 1000, "조정 1회 1원 미만 (버튼은 0원) · 개인 의견은 그 여행만 바꿉니다", 28, SUB)
    s.save(p)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__)))
    for name, fn in (("hitl_slide_1_md.svg", slide_md), ("hitl_slide_2_family.svg", slide_family)):
        fn(out / name)
        render(out / name)
        print("wrote", name)
