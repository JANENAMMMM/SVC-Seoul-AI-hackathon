"""ScoringAI 설명용 워크플로우 그림 2장 생성 (1920x1080 SVG).
usage: python gen_workflow.py [out_dir]
"""
import os, re, sys
W, H = 1920, 1080
FONT = "Pretendard, 'Noto Sans KR', 'Malgun Gothic', sans-serif"
MONO = "Consolas, 'D2Coding', 'Courier New', monospace"
C = {'gray': ('#F1F3F5', '#868E96'), 'blue': ('#E8F0FE', '#3B6FD8'),
     'purple': ('#F3EDFF', '#7B4FD6'), 'green': ('#E9F7EE', '#2F9E54'),
     'orange': ('#FFF1E3', '#E07B1A'), 'red': ('#FDECEC', '#D63B3B')}
COLS = {k: v[1] for k, v in C.items()}
COLS['dark'] = '#495057'
TXT = '#212529'
SUB = '#5C636A'


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


class Fig:
    def __init__(self):
        self.o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">', '<defs>']
        for k, c in COLS.items():
            self.o.append(f'<marker id="m-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>')
        self.o += ['</defs>', f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>']

    def a(self, s):
        self.o.append(s)

    def spans(self, line):
        r = []
        for t in re.findall(r'`[^`]+`|\*\*[^*]+\*\*|[^`*]+', line):
            if t.startswith('`'):
                r.append(f'<tspan font-family="{MONO}" fill="#1B3A7A">{esc(t[1:-1])}</tspan>')
            elif t.startswith('**'):
                r.append(f'<tspan font-weight="700">{esc(t[2:-2])}</tspan>')
            else:
                r.append(esc(t))
        return ''.join(r)

    def text(self, x, y, lines, size=22, color=TXT, weight=400, anchor='start', lh=None):
        lh = lh or size * 1.45
        for i, ln in enumerate(lines):
            self.a(f'<text x="{x}" y="{y + i * lh:.1f}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{self.spans(ln)}</text>')

    def box(self, x, y, w, h, col, rx=16, dash=None, sw=2.5):
        f, s = C[col]
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{f}" stroke="{s}" stroke-width="{sw}"{d}/>')

    def cyl(self, x, y, w, h, ry=18):
        f, s = C['blue']
        self.a(f'<path d="M{x},{y + ry} A{w / 2},{ry} 0 0 1 {x + w},{y + ry} V{y + h - ry} A{w / 2},{ry} 0 0 1 {x},{y + h - ry} Z" fill="{f}" stroke="{s}" stroke-width="2.5"/>')
        self.a(f'<ellipse cx="{x + w / 2}" cy="{y + ry}" rx="{w / 2}" ry="{ry}" fill="#D4E3FC" stroke="{s}" stroke-width="2.5"/>')

    def cloud(self, x, y, w, h):
        f, s = C['gray']
        self.a(f'<path d="M{x+.15*w},{y+h} C{x-.05*w},{y+h} {x-.05*w},{y+.45*h} {x+.15*w},{y+.45*h} C{x+.15*w},{y+.05*h} {x+.45*w},{y-.05*h} {x+.55*w},{y+.2*h} C{x+.65*w},{y} {x+.92*w},{y+.08*h} {x+.86*w},{y+.42*h} C{x+1.05*w},{y+.45*h} {x+1.05*w},{y+h} {x+.85*w},{y+h} Z" fill="{f}" stroke="{s}" stroke-width="2.5"/>')

    def arrow(self, d, col='dark', dash=None, both=False, sw=3):
        ds = f' stroke-dasharray="{dash}"' if dash else ''
        ms = f' marker-start="url(#m-{col})"' if both else ''
        self.a(f'<path d="{d}" fill="none" stroke="{COLS[col]}" stroke-width="{sw}"{ds} marker-end="url(#m-{col})"{ms}/>')

    def title(self, t):
        self.text(80, 100, [f'**{t}**'], size=44)

    def save(self, p):
        self.o.append('</svg>')
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(self.o))


def fig1(p):
    f = Fig()
    f.title('근거는 어디서 와서 DB에 어떻게 쌓이나')
    R = [
        (['**GPS 궤적**'], ['OpenStreetMap 공개 GPS 궤적', '+ Open-Meteo 고도'],
         ['관광지 구역만 잘라 거리·시간·오르막 중앙값', '· 궤적 5개 미만은 C등급'],
         ['`scoring_evidence` `gps` **36** (3곳)']),
        (['**지도 (OSM)**'], ['Overpass로 반경 300m 질의'],
         ['보행로 길이·계단·벤치·화장실 수', '· "경계 아님" 메모'],
         ['`scoring_evidence` `osm` **35**']),
        (['**Tripadvisor 리뷰**'], ['Apify로 13곳 × 약 150건'],
         ['원문 저장 + 정규식으로 계단·더위·혼잡', '언급 비율(95% 신뢰구간)'],
         ['`scoring_reviews` **1,854**', '`scoring_evidence` `rev` **104**']),
        (['**Google 지도**'], ['SerpApi로 장소·리뷰 주제·', '리뷰(장소당 5건)'],
         ['장소 식별 · 주제 키워드를 차원에 배정', "(온천 'hot' 같은 오탐 표시)"],
         ['`scoring_places` **15**', '`scoring_evidence` `topic` **250**', '`scoring_reviews` **140**']),
        (['**기후**'], ['Open-Meteo 과거 기상'],
         ['다낭 월별 최고 체감온도 평균', '· A등급'],
         ['`scoring_evidence` `climate` **12**']),
    ]
    X = [(60, 270, 'gray'), (380, 400, 'gray'), (830, 520, 'green'), (1400, 460, 'blue')]
    HD = ['출처', '어떻게 수집', '어떻게 정제', '저장 (테이블 · 건수)']
    for (x, w, _), t in zip(X, HD):
        f.text(x + w / 2, 162, [f'**{t}**'], size=24, anchor='middle', color=SUB)
    y0, h, gap, lh = 182, 126, 12, 28
    for i, row in enumerate(R):
        y = y0 + i * (h + gap)
        for j, ((x, w, col), lines) in enumerate(zip(X, row)):
            if j == 1:
                f.a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="#F8F9FA" stroke="#ADB5BD" stroke-width="2"/>')
            else:
                f.box(x, y, w, h, col, rx=14, sw=2)
            n = len(lines)
            ty = y + h / 2 - (n - 1) * lh / 2 + 7
            sz = 24 if j == 0 else 20
            f.text(x + 18, ty, lines, size=sz, lh=lh)
            if j < 3:
                nx = X[j + 1][0]
                f.arrow(f'M{x + w + 4},{y + h / 2} H{nx - 6}', 'dark', sw=2.5)
    # 공통 정제 band
    by = y0 + 5 * (h + gap) + 6
    f.box(60, by, 1800, 82, 'green', rx=14, sw=2)
    f.text(84, by + 50, ['**공통 정제** (`load_evidence.py`)'], size=22)
    chips = ['고정 ID (`출처:관광지:항목`)', '차원 배정 (`climb·walking·heat·crowd·general`)', '근거 등급 **A/B/C**', '한계 메모(`caveat`) 첨부']
    cw = [300, 520, 200, 260]
    cx = 470
    for c, w in zip(chips, cw):
        f.a(f'<rect x="{cx}" y="{by + 18}" width="{w}" height="46" rx="23" fill="#FFFFFF" stroke="{COLS["green"]}" stroke-width="2"/>')
        f.text(cx + w / 2, by + 49, [c], size=20, anchor='middle')
        cx += w + 18
    f.a('<rect x="0" y="980" width="1920" height="100" fill="#F1F3F5"/>')
    f.text(960, 1022, ['합계  `scoring_places` **15** · `scoring_evidence` **523** (초기 조사 사실 86 포함) · `scoring_reviews` **1,994**'], size=26, anchor='middle')
    f.text(960, 1060, ['관광지별 사실(계단 수·엘리베이터 운행 등)은 시기마다 달라 DB에 고정하지 않고, 채점 때 Claude가 웹 검색으로 확인'], size=22, anchor='middle', color=SUB)
    f.save(p)


def fig2(p):
    f = Fig()
    f.title('LLM이 근거를 읽고 채점하면, 코드가 검증한다')
    jy, jh = 330, 300
    # 1 재료
    f.text(185, jy - 30, ['**1** 재료'], size=28, anchor='middle')
    f.cyl(60, jy + 10, 250, 140)
    f.text(185, jy + 80, ['**근거 DB**'], size=28, anchor='middle')
    f.text(185, jy + 115, ['GPS·지도·리뷰·기후'], size=20, anchor='middle', color=SUB)
    f.cloud(80, jy + 190, 210, 110)
    f.text(185, jy + 280, ['**웹**'], size=28, anchor='middle')
    f.text(185, jy + 345, ['계단 수·엘리베이터 운행 등', '시기마다 바뀌는 사실'], size=20, anchor='middle', color=SUB, lh=26)
    f.text(185, jy + 415, ['인용한 페이지는 DB에 기록', '(`scoring_web_cache` 242개)'], size=19, anchor='middle', color=COLS['purple'], lh=26)
    # 2 Claude
    jx, jw = 400, 360
    f.box(jx, jy, jw, jh, 'purple')
    f.text(jx + 30, jy + 60, ['**2** Claude 채점'], size=30)
    f.text(jx + 30, jy + 125, ['DB는 도구로 조회,', '없는 사실은 웹 검색'], size=23)
    f.text(jx + 30, jy + 220, ['차원 4개를 1~10점', '+ 하한·상한, 근거 ID 첨부'], size=23)
    f.arrow(f'M316,{jy + 80} H{jx - 6}', 'purple', dash='8 6', both=True)
    f.arrow(f'M300,{jy + 250} C350,{jy + 250} 350,{jy + 220} {jx - 6},{jy + 220}', 'purple', dash='8 6', both=True)
    f.text(355, jy + 160, ['도구', '호출'], size=19, color=COLS['purple'], anchor='middle')
    # 3 검증
    vx, vw = 830, 310
    f.box(vx, jy, vw, jh, 'green')
    f.text(vx + 30, jy + 60, ['**3** 검증 (코드)'], size=30)
    f.text(vx + 30, jy + 125, ['인용한 근거·웹 페이지가', '기록에 실제로 있나', '· 수치가 맞나'], size=23)
    f.arrow(f'M{jx + jw},{jy + jh / 2} H{vx - 6}', 'dark')
    f.box(vx, 760, vw, 90, 'red', dash='8 6')
    f.text(vx + vw / 2, 815, ['틀리면 그 점수 무효'], size=24, anchor='middle', color=COLS['red'], weight=700)
    f.arrow(f'M{vx + vw / 2},{jy + jh} V754', 'red', dash='8 6')
    # 4 집계
    ax, aw = 1210, 300
    f.box(ax, jy, aw, jh, 'green')
    f.text(ax + 30, jy + 60, ['**4** 집계 (코드)'], size=30)
    f.text(ax + 30, jy + 125, ['최대 3번 → 중앙값'], size=23)
    f.text(ax + 30, jy + 200, ['종합 점수는', '코드가 가중평균'], size=23)
    f.arrow(f'M{vx + vw},{jy + jh / 2} H{ax - 6}', 'dark')
    f.box(ax, 760, aw, 90, 'red', dash='8 6')
    f.text(ax + aw / 2, 815, ['흔들리면 사람 검수'], size=24, anchor='middle', color=COLS['red'], weight=700)
    f.arrow(f'M{ax + aw / 2},{jy + jh} V754', 'red', dash='8 6')
    f.text(ax + aw / 2, 905, ['실행 기록·최종 점수도 DB에 저장'], size=21, color=SUB, anchor='middle')
    f.text(ax + aw / 2, 940, ['`scoring_judgments` · `scoring_scores`'], size=19, color=SUB, anchor='middle')
    # 5 결과 사용
    ux, uw = 1580, 300
    f.box(ux, 260, uw, 440, 'orange')
    f.text(ux + uw / 2, 315, ['**5** 결과 사용'], size=28, anchor='middle')
    f.text(ux + uw / 2, 385, ['관람 방식별 점수'], size=22, anchor='middle')
    f.text(ux + uw / 2, 425, ['↓'], size=26, anchor='middle', color=COLS['orange'])
    f.text(ux + uw / 2, 475, ['**패키지 난이도 · API**'], size=23, anchor='middle')
    f.text(ux + uw / 2, 535, ['↓'], size=26, anchor='middle', color=COLS['orange'])
    f.text(ux + uw / 2, 595, ['동선 짜기 · 챗봇 · 화면'], size=23, anchor='middle')
    f.arrow(f'M{ax + aw},{jy + jh / 2} H{ux - 6}', 'dark')
    f.save(p)


EDGE = [r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe']


def render(svg):
    """SVG -> PNG (1920x1080) via Edge headless. Paths with Korean/spaces go through a file URI."""
    import pathlib
    import subprocess
    svg = pathlib.Path(svg).resolve()
    exe = next((e for e in EDGE if os.path.exists(e)), None)
    if not exe:
        print('Edge not found; PNG skipped')
        return
    subprocess.run([exe, '--headless', '--disable-gpu', '--hide-scrollbars',
                    f'--screenshot={svg.with_suffix(".png")}', '--window-size=1920,1080', svg.as_uri()],
                   timeout=60, check=False)


if __name__ == '__main__':
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    fig1(os.path.join(d, 'workflow_1_evidence.svg'))
    fig2(os.path.join(d, 'workflow_2_judging.svg'))
    for n in ('workflow_1_evidence.svg', 'workflow_2_judging.svg'):
        render(os.path.join(d, n))
