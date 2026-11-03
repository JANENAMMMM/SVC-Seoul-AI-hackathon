import re, sys
W, H = 2560, 1440
FONT = "Pretendard, 'Noto Sans KR', 'Malgun Gothic', sans-serif"
MONO = "Consolas, 'D2Coding', 'Courier New', monospace"
C = {
 'gray': ('#F1F3F5', '#868E96'), 'blue': ('#E8F0FE', '#3B6FD8'),
 'purple': ('#F3EDFF', '#7B4FD6'), 'green': ('#E9F7EE', '#2F9E54'),
 'orange': ('#FFF1E3', '#E07B1A'), 'red': ('#FDECEC', '#D63B3B'),
}
TXT = '#212529'; SUB = '#5C636A'
out = []
def a(s): out.append(s)
def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def spans(line):
    res = []
    for tok in re.findall(r'`[^`]+`|\*\*[^*]+\*\*|[^`*]+', line):
        if tok.startswith('`'):
            res.append(f'<tspan font-family="{MONO}" fill="#1B3A7A">{esc(tok[1:-1])}</tspan>')
        elif tok.startswith('**'):
            res.append(f'<tspan font-weight="700">{esc(tok[2:-2])}</tspan>')
        else:
            res.append(esc(tok))
    return ''.join(res)

def text(x, y, lines, size=13, color=TXT, weight=400, anchor='start', lh=None, extra=''):
    lh = lh or size * 1.42
    for i, ln in enumerate(lines):
        a(f'<text x="{x}" y="{y + i*lh:.1f}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}" {extra}>{spans(ln)}</text>')
    return y + len(lines) * lh

def box(x, y, w, h, col, rx=10, dash=None, sw=1.6):
    f, s = C[col]
    d = f' stroke-dasharray="{dash}"' if dash else ''
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{f}" stroke="{s}" stroke-width="{sw}"{d}/>')

def cyl(x, y, w, h):
    f, s = C['blue']; ry = 11
    a(f'<path d="M{x},{y+ry} A{w/2},{ry} 0 0 1 {x+w},{y+ry} V{y+h-ry} A{w/2},{ry} 0 0 1 {x},{y+h-ry} Z" fill="{f}" stroke="{s}" stroke-width="1.6"/>')
    a(f'<ellipse cx="{x+w/2}" cy="{y+ry}" rx="{w/2}" ry="{ry}" fill="#D4E3FC" stroke="{s}" stroke-width="1.6"/>')

def cloud(x, y, w, h):
    f, s = C['gray']
    a(f'<path d="M{x+.15*w},{y+h} C{x-.05*w},{y+h} {x-.05*w},{y+.45*h} {x+.15*w},{y+.45*h} C{x+.15*w},{y+.05*h} {x+.45*w},{y-.05*h} {x+.55*w},{y+.2*h} C{x+.65*w},{y} {x+.92*w},{y+.08*h} {x+.86*w},{y+.42*h} C{x+1.05*w},{y+.45*h} {x+1.05*w},{y+h} {x+.85*w},{y+h} Z" fill="{f}" stroke="{s}" stroke-width="1.6"/>')

COLS = {'gray': '#868E96', 'blue': '#3B6FD8', 'purple': '#7B4FD6', 'green': '#2F9E54', 'orange': '#E07B1A', 'red': '#D63B3B', 'dark': '#495057'}
def arrow(d, col='dark', dash=None, both=False, sw=2):
    c = COLS[col]
    ds = f' stroke-dasharray="{dash}"' if dash else ''
    ms = f' marker-start="url(#m-{col})"' if both else ''
    a(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{sw}"{ds} marker-end="url(#m-{col})"{ms}/>')

a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">')
a('<defs>')
for k, c in COLS.items():
    a(f'<marker id="m-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>')
a('</defs>')
a(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')

# title
text(30, 40, ['**ScoringAI 워크플로우 (v2.1)**'], size=26)
text(370, 40, ['수집 → DB 저장 → LLM 채점 → 검증 → 집계 → 활용'], size=17, color=SUB)

# lanes
LANES = [(0, 420, '① 데이터 수집', 'gray'), (420, 820, '② 근거 DB — Supabase', 'blue'),
         (820, 1420, '③ LLM judge', 'purple'), (1420, 1820, '④ 검증', 'green'),
         (1820, 2180, '⑤ 집계·저장', 'green'), (2180, 2560, '⑥ 활용', 'orange')]
for i, (x0, x1, name, col) in enumerate(LANES):
    a(f'<rect x="{x0}" y="60" width="{x1-x0}" height="1250" fill="{"#FAFBFC" if i%2==0 else "#FFFFFF"}"/>')
    f, s = C[col]
    a(f'<rect x="{x0+8}" y="64" width="{x1-x0-16}" height="36" rx="18" fill="{s}"/>')
    text((x0+x1)/2, 89, [f'**{name}**'], size=18, color='#FFFFFF', anchor='middle')
    if i: a(f'<line x1="{x0}" y1="60" x2="{x0}" y2="1310" stroke="#DEE2E6" stroke-width="1.5"/>')

# ---------------- lane 1
S = [
 ('S1 GPS 궤적', ['OpenStreetMap 공개 GPS 궤적 +', 'Open-Meteo 고도 /', '실제 걸은 거리·시간·오르막'], ['관광지 구역으로 궤적 자르기'], ['→ `scoring_evidence` (`gps:` 36)']),
 ('S2 지도 데이터', ['OpenStreetMap Overpass /', '300m 반경 보행로·계단·벤치·화장실'], ['자동 질의'], ['→ `scoring_evidence` (`osm:` 35)']),
 ('S3 Tripadvisor 리뷰', ['Tripadvisor 리뷰 13곳 × 약 150건 (Apify)'], ['원문 저장 + 정규식으로 주제 언급 비율 계산'], ['원문 → `scoring_reviews` (1,854)', '비율 → `scoring_evidence` (`rev:` 104)']),
 ('S4 Google 지도', ['Google 지도 장소 정보·리뷰 주제·', '리뷰 5건 (SerpApi)'], ['장소 식별 + 자동 추출 주제'], ['장소 → `scoring_places` (15)', '주제 → `scoring_evidence` (`topic:` 250)', '리뷰 → `scoring_reviews` (140)']),
 ('S5 기후', ['Open-Meteo 과거 기상 /', '다낭 월별 최고 체감온도'], ['자동'], ['→ `scoring_evidence` (`climate:` 12)']),
]
y = 115; sx, sw_ = 15, 305
for t, body, meth, dest in S:
    h = 14 + 20 + len(body)*18 + len(meth)*16 + len(dest)*17 + 14
    box(sx, y, sw_, h, 'gray')
    yy = text(sx+12, y+26, [f'**{t}**'], size=15)
    yy = text(sx+12, yy+2, body, size=13, lh=18)
    yy = text(sx+12, yy, meth, size=11.5, color=SUB, lh=16)
    text(sx+12, yy+2, dest, size=12, lh=17, color='#1B3A7A')
    arrow(f'M{sx+sw_},{y+h/2} H343', 'gray')
    y += h + 30
bar_y0, bar_y1 = 115, y - 30
box(345, bar_y0, 55, bar_y1-bar_y0, 'gray', rx=8, sw=2)
cx, cy = 372.5, (bar_y0+bar_y1)/2
a(f'<g transform="rotate(-90 {cx} {cy})">')
text(cx, cy-4, ['`load_evidence.py`'], size=16, anchor='middle', weight=700)
text(cx, cy+16, ['수집 파일을 DB로 옮김 (같은 사실은 같은 ID)'], size=13, anchor='middle', color=SUB)
a('</g>')
text(15, bar_y1+30, ['Google 리뷰 대량 수집은 불가(장소당 5건 한계) ·', '리뷰 원문은 git에 올리지 않음'], size=11.5, color=SUB, lh=16)

# ---------------- lane 2
DX, DW = 445, 330
text(620, 124, ['모든 테이블은 `scoring_` 접두어 · 다른 팀 테이블 접근 안 함'], size=11.5, color=SUB, anchor='middle')
text(DX, 152, ['**채점 전에 채워지는 근거**'], size=13, color=COLS['blue'])
def dtable(y, h, title, lines, ex=None):
    cyl(DX, y, DW, h)
    yy = text(DX+14, y+44, [title], size=14, weight=700)
    yy = text(DX+14, yy, lines, size=12.5, lh=17.5)
    if ex: text(DX+14, yy+1, ex, size=11.5, color=SUB, lh=16)
dtable(165, 120, 'D1 `scoring_places`', ['관광지 15곳 / 이름·좌표·Google 정보'], ['예: `dad-02` 오행산'])
dtable(300, 140, 'D2 `scoring_evidence`', ['근거 523건 (초기 조사 사실 86 포함) /', '차원·등급·값·단위·출처·**한계 메모**'], ['예: `gps:dad-03:median_km`'])
box(DX+20, 448, DW-40, 76, 'blue', rx=6, sw=1)
text(DX+32, 467, ['**근거 등급**', 'A 측정 기후 · B GPS(궤적 5개 이상)·초기 조사 사실', 'C 지도 반경·리뷰 통계·GPS 표본 부족'], size=11.5, lh=17)
dtable(540, 140, 'D3 `scoring_reviews`', ['리뷰 원문 1,994건 /', '출처·언어·여행 유형·평점'], ['예: `rev:dad-02:<번호>` 리뷰 원문 한 건'])
text(DX, 728, ['**채점하면서 쌓이는 기록**'], size=13, color=COLS['blue'])
dtable(740, 120, 'D4 `scoring_web_cache`', ['judge가 웹에서 찾아 인용한 페이지 103개', '/ URL·검색어·인용 문장'])
dtable(905, 115, 'D5 `scoring_judgments`', ['채점 실행 원본 67회 /', '출력·인용 통과 여부·토큰'])
dtable(1045, 115, 'D6 `scoring_scores`', ['최종 점수 17행(v2.1 15곳) /', '차원 점수·종합·상태·조건'])
# load_evidence -> D1 D2 D3
for ty in (230, 360, 600):
    arrow(f'M400,{ty} H{DX-3}', 'gray')

# ---------------- lane 3
box(840, 110, 560, 760, 'purple', rx=16, sw=2.5)
text(1120, 142, ['**Claude Sonnet judge (rubric v2.1)**'], size=21, anchor='middle', color='#4B2A9E')
# step 2 tools (left column)
LX, LW = 860, 230
text(LX, 172, ['**2. 도구로 근거 찾기** (최대 12회)'], size=13.5, color='#4B2A9E')
def chip(x, y, w, label):
    box(x, y, w, 34, 'purple', rx=17, sw=1.5)
    text(x+w/2, y+22, [f'`{label}`'], size=12.5, anchor='middle')
chip(LX, 213, LW, 'get_place')          # -> D1 (230)
chip(LX, 343, LW, 'list_evidence')      # -> D2 (360)
chip(LX, 393, LW, 'get_climate')        # -> D2 climate (410)
text(LX+LW-4, 440, ['↔ D2 `climate:`'], size=11, color=SUB, anchor='end')
chip(LX, 583, LW, 'search_reviews')     # -> D3 (600)
arrow(f'M{LX-3},230 H{DX+DW+3}', 'purple', dash='5 4', both=True, sw=1.8)
arrow(f'M{LX-3},360 H{DX+DW+3}', 'purple', dash='5 4', both=True, sw=1.8)
arrow(f'M{LX-3},410 H{DX+DW+3}', 'purple', dash='5 4', both=True, sw=1.8)
arrow(f'M{LX-3},600 H{DX+DW+3}', 'purple', dash='5 4', both=True, sw=1.8)
# web tools
text(LX, 652, ['Anthropic 서버 검색,', '최대 4회'], size=11, color=SUB, lh=14)
text(LX+LW, 652, ['SerpApi', 'Google 결과'], size=11, color=SUB, lh=14, anchor='end')
chip(LX, 680, 100, 'web_search')
chip(LX+106, 680, 124, 'google_web_search')
cloud(LX+30, 748, 170, 62)
text(LX+115, 790, ['**웹**'], size=16, anchor='middle')
arrow(f'M{LX+50},717 V752', 'purple', dash='5 4', both=True, sw=1.8)
arrow(f'M{LX+168},717 V752', 'purple', dash='5 4', both=True, sw=1.8)
arrow(f'M{LX+30},790 H{DX+DW+3}', 'dark')
text(LX, 830, ['실제 검색 결과로 받은 URL 중', '인용된 것만 저장 → D4'], size=11, color=SUB, lh=14)
# right column
RX, RW = 1110, 275
box(RX, 160, RW, 170, 'purple', rx=10, sw=1.3)
text(RX+12, 184, ['**1. 입력**', '`place_id` 하나 + 규칙', '(차원 4개 정의, 차원별 앵커,', '절차, "도구가 준 ID만 인용")'], size=13, lh=19)
text(RX+12, 268, ['근거는 프롬프트에 넣지 않고', '도구로 직접 찾게 함'], size=11.5, color=SUB, lh=16)
arrow(f'M{RX},300 H{LX+LW+4}', 'purple', sw=1.5)
a(f'<rect x="{RX}" y="360" width="{RW}" height="300" rx="10" fill="#FFFFFF" stroke="{COLS["purple"]}" stroke-width="2"/>')
text(RX+12, 384, ['**3.** `submit_scores`**로 제출**'], size=14)
text(RX+12, 408, ['• 대표 관람 경로', '  예: "오행산 투이선 — 엘리베이터', '  또는 계단, 동굴 2곳"',
                   '• 차원 4개 × `typical` / `lower` /', '  `upper` (1~10)',
                   '• 조건: lower "엘리베이터 이용"', '  [웹 인용 URL]', '  upper "계단으로 정상"', '  [웹 인용 URL]',
                   '• 근거 ID 목록 · 근거로 쓴 수치 ·', '  확신도(high/medium/low)'], size=12.5, lh=19.5)
arrow(f'M{LX+LW+4},480 H{RX-3}', 'purple', sw=1.5)
# resubmit loop
arrow(f'M{RX+200},660 C{RX+200},715 {RX+90},715 {RX+90},664', 'red', dash='6 4', sw=2)
text(RX+145, 735, ['형식 틀리면 1회 재제출 요청'], size=12, color=COLS['red'], anchor='middle')
text(RX+12, 775, ['**계단 수·엘리베이터 운행 등** 시기마다', '바뀌는 사실은 채점 때 **웹 검색**', '(v2.1: 31회, 인용 103개)'], size=12, color='#4B2A9E', lh=17)
arrow(f'M{RX-4},780 H{LX+212}', 'purple', dash='2 3', sw=1.2)

# ---------------- lane 4
KX, KW, KY, KH = 1440, 310, 360, 290
box(KX, KY, KW, KH, 'green', rx=10, sw=2)
text(KX+14, KY+28, ['**검증** `verify.py`'], size=15)
items = [['점수 1~10 정수,', '`lower ≤ typical ≤ upper`'],
         ['lower·upper가 typical과 다르면', '조건이 있고, 조건마다 근거 ID'],
         ['인용 ID가 D2·D3·D4에 **실제로 있음**', '(URL은 `www.`·https 차이 무시)'],
         ['인용 수치가 DB 원본 값과', '5% 안에서 일치']]
iy = KY + 58
for it in items:
    a(f'<circle cx="{KX+22}" cy="{iy-4}" r="9" fill="{COLS["green"]}"/>')
    a(f'<path d="M{KX+17},{iy-4} l4,4 l7,-8" stroke="#fff" stroke-width="2.2" fill="none"/>')
    text(KX+38, iy, it, size=12.5, lh=18)
    iy += 56
arrow(f'M{RX+RW},480 H{KX-3}', 'dark')
# exits
arrow(f'M{KX+KW},420 H1832', 'green', sw=2.5)
text(1792, 385, ['통과 →', '이 차원 유효'], size=12, color=COLS['green'], anchor='middle', weight=700, lh=15)
arrow(f'M{KX+200},{KY+KH} V717', 'red', dash='6 4')
box(KX+110, 720, 200, 60, 'red', rx=8, dash='6 4')
text(KX+210, 744, ['하나라도 어김 →', '이 차원은 이번 실행 무효'], size=12, color=COLS['red'], anchor='middle', lh=17)
text(KX+KW, 810, ['v2.1 실행 65회 중 56회 전 차원 통과'], size=12, color=SUB, anchor='end')
# 대조 bus D2/D3/D4 -> item 3
BX = 798
for ty in (390, 650, 830):
    a(f'<path d="M{DX+DW},{ty} H{BX}" stroke="{COLS["gray"]}" stroke-width="1.4" stroke-dasharray="2 4" fill="none"/>')
arrow(f'M{BX},390 V895 H{KX+20} V{KY+KH+3}', 'gray', dash='2 4', sw=1.4)
text(1130, 888, ['대조 (D2·D3·D4의 ID·수치) → 검증 3·4번'], size=11.5, color=SUB, anchor='middle')

# ---------------- lane 5
AX, AW, AY, AH = 1835, 330, 360, 250
box(AX, AY, AW, AH, 'green', rx=10, sw=2)
yy = text(AX+14, AY+28, ['**같은 관광지를 3회 실행 →**', '**유효한 실행만 차원별 중앙값**'], size=14.5, lh=21)
text(AX+14, yy+8, ['• 종합 점수 = `climb`×3 + `walking`×3', '  + `heat`×2 + `crowd`×1 의 가중평균', '  (코드 계산, LLM이 내지 않음)',
                   '• 등급 표시: 1~3 하 · 4~6 중 · 7~10 상', '• 확신도: 3회 중 가장 낮은 값'], size=12.5, lh=19)
# ok -> scores_v2.json
arrow(f'M{AX+AW-40},{AY} V162 H2197', 'green', sw=2.5)
text(AX+AW-50, 200, ['**ok** → 공개 점수'], size=13, color=COLS['green'], anchor='end')
text(AX+AW-50, 218, ['최종 → `scores_v2.json`'], size=11.5, color=SUB, anchor='end')
# needs_review
arrow(f'M{AX+210},{AY+AH} V687', 'red', dash='6 4')
box(1905, 690, 260, 92, 'red', rx=8, dash='6 4')
text(2035, 714, ['실행 간 차이 >2점 · 유효 실행 없음 ·', '무효 실행 있음 →', '`needs_review`(검수 대기)'], size=12, color=COLS['red'], anchor='middle', lh=18)
arrow('M2035,782 V817', 'red', dash='6 4')
box(1905, 820, 260, 80, 'gray', rx=8)
a('<circle cx="1932" cy="846" r="8" fill="#868E96"/><path d="M1918,872 q14,-20 28,0 z" fill="#868E96"/>')
text(1956, 846, ['**사람 검수**', '현재 껌탄 코코넛 마을,', '참 조각 박물관'], size=12, lh=17)
# storage -> D5, D6
arrow(f'M{AX+30},{AY+AH} V962 H{DX+DW+3}', 'dark')
arrow(f'M{AX+30},962 V1102 H{DX+DW+3}', 'dark')
text(880, 952, ['실행마다 → D5 `scoring_judgments` + 파일 `judge/v2/<곳>_run<k>.json`'], size=12.5)
text(880, 1092, ['최종 → D6 `scoring_scores` + 파일 `scores_v2.json`'], size=12.5)

# ---------------- lane 6
OX, OW = 2200, 345
def obox(y, h, lines, size=12.5, lh=18.5):
    box(OX, y, OW, h, 'orange', rx=10, sw=1.8)
    text(OX+14, y+24, lines, size=size, lh=lh)
obox(140, 44, ['`scores_v2.json`'], size=14)
obox(215, 190, ['**관람 방식 카탈로그**', '`visit_modes_v2_1.json`', '15곳 × 3방식:', '  `standard` 일반', '  `short` 이동 보조·짧은 관람', '  `full` 전체 관람', '예: 오행산 short 5점 · standard 7점 ·', '  full 7점'])
obox(440, 180, ['**패키지 난이도** (`package_difficulty.py`)', '입력: 일정표(관광지·방식·일정표 출처·', '  경로 메모)', '규칙: 하루 최고 점수 + 6점 이상 연속', '  방문마다 +1 (하루 최대 +2)', '예: 바나힐(6) → 오행산 전체(7) = 8점', '  / 오행산을 short로 바꾸면 6점'])
obox(655, 120, ['**API** (`api/scoring.py`)', '저장 파일만 읽음, DB·Claude 호출 없음', '`GET /api/scoring/places`', '`GET /places/{id}`', '`POST /packages/evaluate`'])
arrow(f'M{OX+OW/2},184 V212', 'orange', sw=2.2)
arrow(f'M{OX+OW/2},405 V437', 'orange', sw=2.2)
arrow(f'M{OX+OW/2},620 V652', 'orange', sw=2.2)
arrow(f'M{OX+OW},310 H2554 V715 H{OX+OW+3}', 'orange', sw=2.2)
# usage
UY = 830; uw = 108
uses = [('동선 짜기', []), ('챗봇', ['("왜 힘든지"', '근거 설명)']), ('화면', ['(점수·이유·', '출처 링크)'])]
for i, (t, sub) in enumerate(uses):
    ux = OX + i*(uw+10.5)
    box(ux, UY, uw, 120, 'orange', rx=10, sw=1.8)
    ic = ux + uw/2; s = COLS['orange']
    if i == 0:
        a(f'<path d="M{ic},{UY+44} l-10,-14 a12,12 0 1 1 20,0 z" fill="{s}"/><circle cx="{ic}" cy="{UY+24}" r="4" fill="#fff"/>')
    elif i == 1:
        a(f'<rect x="{ic-15}" y="{UY+14}" width="30" height="20" rx="5" fill="{s}"/><path d="M{ic-6},{UY+34} l-5,8 l11,-8 z" fill="{s}"/>')
    else:
        a(f'<rect x="{ic-16}" y="{UY+14}" width="32" height="22" rx="3" fill="{s}"/><rect x="{ic-6}" y="{UY+37}" width="12" height="4" fill="{s}"/>')
    text(ic, UY+66, [f'**{t}**'] + sub, size=12.5, anchor='middle', lh=17)
    arrow(f'M{OX+OW/2},775 L{ic},{UY-3}', 'orange', sw=1.8)

# ---------------- bottom strip
a('<rect x="0" y="1310" width="2560" height="130" fill="#F1F3F5"/>')
text(30, 1342, ['**검증 계획(진행 전)**: 채점에 쓰지 않은 후기와 대조 · 사람 기준셋 ±1점 일치율'], size=14, color=SUB)
text(1100, 1342, ['**한계**: "50세 이상 보통 체력" 가정의 설계 점수, 실제 고객 체감 검증 전'], size=14, color=SUB)
lx = 30; ly = 1395
text(lx, ly+5, ['**범례**'], size=14, color=SUB); lx += 60
for col, lab in [('gray', '외부 데이터 출처'), ('blue', 'DB 테이블'), ('purple', 'LLM(Claude)'), ('green', '코드가 판정(검증·집계)'), ('orange', '결과물·사용처')]:
    if col == 'blue': cyl(lx, ly-14, 26, 26)
    else: box(lx, ly-12, 26, 22, col, rx=4)
    text(lx+34, ly+5, [lab], size=13, color=SUB); lx += 60 + len(lab)*12
box(lx, ly-12, 26, 22, 'red', rx=4, dash='4 3'); text(lx+34, ly+5, ['무효·검수 대기'], size=13, color=SUB); lx += 170
lx += 30
arrow(f'M{lx},{ly} h50', 'dark'); text(lx+60, ly+5, ['데이터 흐름'], size=13, color=SUB); lx += 160
arrow(f'M{lx+4},{ly} h46', 'purple', dash='5 4', both=True); text(lx+60, ly+5, ['도구 호출(질문 ↔ 결과)'], size=13, color=SUB); lx += 230
arrow(f'M{lx},{ly} h50', 'red', dash='6 4'); text(lx+60, ly+5, ['실패·되돌림(재제출, 무효, 검수 대기)'], size=13, color=SUB); lx += 330
a(f'<path d="M{lx},{ly} h50" stroke="{COLS["gray"]}" stroke-width="1.4" stroke-dasharray="2 4"/>'); text(lx+60, ly+5, ['대조'], size=13, color=SUB)
a('</svg>')

import os, pathlib, subprocess
EDGE = [r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe']


def render(svg):
    """SVG -> PNG (2560x1440) via Edge headless. Paths with Korean/spaces go through a file URI."""
    svg = pathlib.Path(svg).resolve()
    exe = next((e for e in EDGE if os.path.exists(e)), None)
    if not exe:
        print('Edge not found; PNG skipped')
        return
    subprocess.run([exe, '--headless', '--disable-gpu', '--hide-scrollbars',
                    f'--screenshot={svg.with_suffix(".png")}', f'--window-size={W},{H}', svg.as_uri()],
                   timeout=60, check=False)


d = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
svg_path = os.path.join(d, 'workflow.svg')
open(svg_path, 'w', encoding='utf-8').write('\n'.join(out))
render(svg_path)
