# ScoringAI 검증 보고서

기준 버전 1.0 · 기본 방문 월 7월 · D5 혼잡은 표시만 함.

## 차원별 결측과 채택 근거

| 차원 | 결측 | A | B | C |
|---|---:|---:|---:|---:|
| D1 | 2/15 (13%) | 3 | 2 | 8 |
| D2 | 2/15 (13%) | 3 | 4 | 6 |
| D3 | 3/15 (20%) | 0 | 4 | 8 |
| D4 | 0/15 (0%) | 0 | 15 | 0 |
| D5 | 3/15 (20%) | 0 | 0 | 12 |

## A·B 대 C 비교

C 근거와 비교 가능한 차원별 근거 쌍을 집계했습니다. 동일 관광지의 여러 C 출처는 각각 한 쌍입니다.

- 비교 쌍: 16
- 정확한 수준 일치율: 62.5%
- 스피어만 상관: 0.507

## 기준값 민감도

| 기준 배율 | 등급 변경 관광지 수 |
|---:|---:|
| 0.8 | 2/15 |
| 1.2 | 2/15 |

## 전체 관광지 등급

| ID | 관광지 | 등급 | 핵심 근거 | 상태 |
|---|---|---|---|---|
| dad-01 | 바나힐 썬월드 | 상 | D1 B 8.86km→2, D2 B 45.0m→1, D4 B Truebool→2 | needs_review |
| dad-02 | 오행산(마블마운틴) | 상 | D1 A 1.7km→1, D2 A 177.0m→2, D4 B Truebool→2 | needs_review |
| dad-03 | 호이안 구시가지 | 중 | D1 A 2.775km→1, D2 A 12.0m→0, D4 B Truebool→2 | draft |
| dad-04 | 영흥사(린응사, 손짜반도) | 하 | D1 C 0.067ratio→0, D2 C 0.047ratio→0, D4 B Truebool→2 | draft |
| dad-05 | 미케 해변 | 중 | D1 C 0.247ratio→1, D2 B 0steps→0, D4 B Truebool→2 | draft |
| dad-06 | 용다리 | 중 | D1 C 0.1ratio→1, D2 B 0steps→0, D4 B Truebool→2 | draft |
| dad-07 | 한시장 | 중 | D1 C 0.133ratio→1, D2 C 0.007ratio→0, D4 B Falsebool→0 | draft |
| dad-08 | 다낭 대성당(핑크성당) | 하 | D1 C 0.04ratio→0, D2 C 0.007ratio→0, D4 B Truebool→2 | draft |
| dad-09 | 참 조각 박물관 | 하 | D1 C 0.033ratio→0, D2 C 0.0ratio→0, D4 B Falsebool→0 | draft |
| dad-10 | 아시아파크(썬휠) | 하 | D1 C 0.02ratio→0, D2 C 0.0ratio→0, D4 B Truebool→2 | draft |
| dad-11 | 누이탄타이 온천공원 | 하 | D4 B Truebool→2 | needs_review |
| dad-12 | 미선 유적지 | 상 | D1 B 3.851km→2, D2 B 120.0m→2, D4 B Truebool→2 | needs_review |
| dad-13 | 하이반 고개 | 하 | D1 C 0.007ratio→0, D2 C 0.033ratio→0, D4 B Truebool→2 | draft |
| dad-14 | 호이안 야시장 | 중 | D1 A 1.143km→1, D2 A 6.0m→0, D4 B Truebool→2 | needs_review |
| dad-15 | 껌탄 코코넛 마을(바구니배) | 하 | D4 B Truebool→2 | needs_review |

결측 차원과 근거 간 2단계 이상 차이는 `needs_review`로 남겼습니다. OSM 자료가 추가되면 다시 실행해야 합니다.
