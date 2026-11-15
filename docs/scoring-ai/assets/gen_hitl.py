"""HITL 피드백 루프 그림 2장 (1920x1080 SVG + PNG): hitl_loop(해커톤 단순화 버전), hitl_loop_full(상용화 고도화안). gen_workflow.py의 그림 도구를 그대로 쓴다.
usage: python gen_hitl.py [out_dir]
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_workflow import SUB, Fig, render  # noqa: E402


def fig_full(p):
    f = Fig()
    f.title('상용화 고도화안 — 임시 점수·반복 조정 신호·승인 맥락까지')
    f.text(80, 140, ['개인 의견은 그 여행만 바꾸고, 전체 점수는 MD를 거쳐 근거로만 바뀐다. LLM은 구조화·근거 판정만 하고 계산은 코드가 한다.'],
           size=21, color=SUB)

    # ── 1행: 현재 데이터 흐름 ─────────────────────────────
    y, h = 185, 130
    f.cyl(80, y, 230, h)
    f.text(195, y + 62, ['**근거 DB**', '`scoring_evidence`'], size=20, anchor='middle')
    f.box(370, y, 300, h, 'purple')
    f.text(520, y + 45, ['**AI 채점 (배치)**', 'Sonnet judge 1~3회', '+ 인용 검증(verify)'], size=20, anchor='middle', lh=29)
    f.box(730, y, 290, h, 'blue')
    f.text(875, y + 45, ['**난이도 카탈로그**', '검증 점수 × 관람 방식 3', '+ MD 임시 점수'], size=20, anchor='middle', lh=29)
    f.box(1080, y, 290, h, 'gray')
    f.text(1225, y + 45, ['**일정 엔진**', '일차 배정·시간표·식당', '하루·패키지 난이도'], size=20, anchor='middle', lh=29)
    f.box(1430, y, 410, h, 'gray', dash='8 6')
    f.text(1635, y + 45, ['**프론트**', '고객 여행 화면 · MD 작업실', '(연결은 프론트 담당)'], size=20, anchor='middle', lh=29)
    for x0, x1 in ((310, 370), (670, 730), (1020, 1080), (1370, 1430)):
        f.arrow(f'M{x0},{y + h / 2} H{x1 - 4}')

    # ── 2행: 점수 조정 (MD) — 카탈로그·채점 바로 아래라 수직선이 곧게 올라간다 ──
    y3, h3 = 395, 140
    f.box(1430, y3, 410, h3, 'orange')
    f.text(1455, y3 + 38, ['**② MD 의견 (하나투어)**', '"오행산 엘리베이터 점검 잦아', '계단 부담 높게 봐야"'], size=20, lh=31)
    f.box(1080, y3, 290, h3, 'orange')
    f.text(1225, y3 + 38, ['**자연어 → 조정안**', 'Haiku 1회 (~$0.0004)', '장소·차원·점수·주장'], size=20, anchor='middle', lh=31)
    f.box(730, y3, 290, h3, 'orange')
    f.text(875, y3 + 38, ['**임시 점수 즉시 표시**', '`scoring_overrides`', '"MD 조정(재채점 대기)"'], size=20, anchor='middle', lh=31)
    f.box(370, y3, 300, h3, 'purple')
    f.text(520, y3 + 38, ['**재채점 (버튼)**', 'MD 주장 = `human:` 근거', 'Sonnet medium (1회 ~$0.065)'], size=20, anchor='middle', lh=31)
    for x0, x1 in ((1430, 1374), (1080, 1024), (730, 674)):
        f.arrow(f'M{x0},{y3 + 70} H{x1}', 'orange')
    f.arrow(f'M960,{y3} V319', 'orange', dash='7 6')
    f.text(970, 368, ['즉시 반영'], size=18, color='#E07B1A')
    f.arrow(f'M450,{y3} V319', 'purple', dash='7 6')
    f.text(462, 368, ['근거 추가'], size=18, color='#7B4FD6')
    f.arrow(f'M640,{y3} L762,319', 'purple')
    f.text(716, 372, ['MD 승인 시 게시'], size=18, color='#7B4FD6')

    # ── 3행: 일정 조정 (자녀·부모님) ───────────────────────
    y2, h2 = 640, 140
    f.box(1430, y2, 410, h2, 'green')
    f.text(1455, y2 + 38, ['**① 자녀·부모님 의견**', '"엄마가 2일차 힘들대"', '또는 버튼(가볍게·빼기·식당 교체)'], size=20, lh=31)
    f.box(1080, y2, 290, h2, 'green')
    f.text(1225, y2 + 38, ['**자연어 → 수정 명령**', 'Haiku 1회 (~$0.0004)', '명령 9종 · 모호하면 되묻기'], size=20, anchor='middle', lh=31)
    f.box(730, y2, 290, h2, 'green')
    f.text(875, y2 + 38, ['**제안 → 자녀 승인**', 'refine 미리보기·변경 요약', '승인 시에만 적용'], size=20, anchor='middle', lh=31)
    f.arrow(f'M1430,{y2 + 70} H1374', 'green')
    f.arrow(f'M1080,{y2 + 70} H1024', 'green')
    f.arrow(f'M1000,{y2} V588 H1050 V360 H1120 V319', 'green')
    f.text(1062, 580, ['승인된 일정으로 다시 짜기'], size=18, color='#2F9E54')
    f.arrow(f'M800,{y2 + h2} C800,{y2 + h2 + 38} 1150,{y2 + h2 + 38} 1150,{y2 + h2 + 4}', 'green', dash='7 6')
    f.text(785, y2 + h2 + 32, ['`feedback_log` → 다음 해석의 맥락'], size=18, color='#2F9E54', anchor='end')

    # ── 기록 DB와 신호 루프 ───────────────────────────────
    f.cyl(80, 395, 230, 385)
    f.text(195, 520, ['**조정 기록**', '`scoring_feedback`', '', '누가·무엇을·', '제안→승인·', '전후 값·비용'], size=19, anchor='middle', lh=30)
    f.arrow(f'M370,{y3 + 110} H314', 'dark', dash='4 6', sw=2)
    f.arrow(f'M730,{y2 + 110} H314', 'dark', dash='4 6', sw=2)
    f.arrow(f'M195,780 V868 H1872 V{y3 + 70} H1844', 'red')
    f.text(1030, 858, ['③ 신호: 여러 가족이 반복해서 가볍게 바꾼 곳 → MD 재채점 검토 (`/api/hitl/signals`)'],
           size=19, color='#D63B3B', anchor='middle')

    # ── 하단: 비용·심사 연결 ─────────────────────────────
    yb = 900
    f.box(80, yb, 860, 150, 'gray', sw=1.5)
    f.text(105, yb + 40, ['**조정 1회당 LLM 호출 (팀 크레딧 $50)**',
                          '일정 버튼 0회 $0 · 일정 자연어 Haiku 1회 ~$0.0004 (실측 2.3K/0.3K 토큰)',
                          'MD 의견 Haiku 1회 ~$0.0004 · 재채점은 버튼 누를 때만 Sonnet medium 1회 약 $0.065',
                          '호출 제한: 해석 30회/시간 · 재채점 5회/일 (사용자별)'], size=19, lh=30)
    f.box(980, yb, 860, 150, 'gray', sw=1.5)
    f.text(1005, yb + 40, ['**심사기준 연결**',
                           'AI 활용 구체성: 자연어 구조화(Haiku) → 근거 재채점(Sonnet) → 인용 검증',
                           '사람 의견이 `human:` 근거로 남아 다음 채점이 실제로 달라진다',
                           '실현가능성: 조정 1회 1원 미만, 재채점 1곳 약 90원 · 기존 엔진 재사용'], size=19, lh=30)
    f.save(p)


def fig_simple(p):
    f = Fig()
    f.title('사람이 고치고, AI가 근거로 다시 판단한다')
    f.text(80, 140, ['개인 의견은 그 여행만 바꾸고, 관광지 점수는 MD 의견을 근거로 AI가 다시 채점한 뒤 승인해야 바뀐다.'],
           size=22, color=SUB)
    # 장면 ① MD
    y = 210
    f.text(80, y, ['**① 하나투어 MD — 관광지 점수 조정**'], size=28, color='#E07B1A')
    xs = [(80, 'orange', ['**MD 의견**', '"오행산 엘리베이터', '점검이 잦아요"']),
          (520, 'orange', ['**AI가 정리**', 'Haiku 1회 · 약 $0.0005', '장소·항목·주장']),
          (960, 'purple', ['**AI가 다시 채점**', '의견 = 근거 1건, 웹으로 확인', 'Sonnet medium · 1회 약 $0.065']),
          (1400, 'blue', ['**MD 승인 → 반영**', '점수 전후·인용 근거 확인', '승인해야 공개 점수 변경'])]
    for x, col, lines in xs:
        f.box(x, y + 30, 380, 170, col)
        f.text(x + 190, y + 85, lines, size=22, anchor='middle', lh=34)
    for x in (460, 900, 1340):
        f.arrow(f'M{x},{y + 115} H{x + 56}', 'orange')
    # 장면 ② 고객
    y = 520
    f.text(80, y, ['**② 자녀·부모님 — 일정 조정**'], size=28, color='#2F9E54')
    xs = [(80, ['**부모님 의견**', '"2일차 힘들어"', '또는 버튼']),
          (520, ['**AI가 명령으로**', 'Haiku 1회 · 약 $0.0005', '버튼이면 $0']),
          (960, ['**바뀐 일정 미리보기**', '엔진이 다시 짬', '오행산 → 엘리베이터 코스']),
          (1400, ['**자녀 승인 → 확정**', '승인 전엔 안 바뀜', '난이도 전후 비교'])]
    for x, lines in xs:
        f.box(x, y + 30, 380, 170, 'green')
        f.text(x + 190, y + 85, lines, size=22, anchor='middle', lh=34)
    for x in (460, 900, 1340):
        f.arrow(f'M{x},{y + 115} H{x + 56}', 'green')
    # 기록
    f.cyl(80, 790, 380, 150)
    f.text(270, 858, ['**조정 기록** `scoring_feedback`', '누가·무엇을·전후 값·비용'], size=20, anchor='middle', lh=32)
    f.box(520, 800, 1260, 150, 'gray', sw=1.5)
    f.text(545, 845, ['**왜 AI인가** 자연어 의견을 구조로 바꾸고, 사람 말을 그대로 믿지 않고 웹 근거로 교차 확인해 다시 판단',
                      '**얼마나 드나** 일정 조정 1회 1원 미만 · 점수 재채점 1곳 약 90원 (팀 크레딧 $50 대비 충분)',
                      '**상용화 시** 임시 점수 즉시 표시 · 여러 가족의 반복 조정 → MD 검토 신호 · 승인 맥락 기억 (고도화안 문서)'],
           size=20, lh=34)
    f.save(p)


if __name__ == '__main__':
    out = Path(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__)))
    for name, draw in (('hitl_loop.svg', fig_simple), ('hitl_loop_full.svg', fig_full)):
        draw(out / name)
        render(out / name)
        print('wrote', name)
