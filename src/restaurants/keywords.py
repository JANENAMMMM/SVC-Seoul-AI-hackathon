"""5단계: 한국어 리뷰와 리뷰 요약에서 키워드로 태그를 세고, 부모님 취향과 맞지 않는 신호를 경고로 만든다.

키워드 사전은 음식 취향 질문 4문항 + 1단계 정리본(고수, 맵다, 부모님, 깔끔)을 기준으로 한다.
리뷰는 식당당 최대 5개라 언급이 없다고 재료가 없다는 뜻은 아니다. 그래서 제외하지 않고 경고와 근거만 붙인다.
"""

from pydantic import BaseModel

from .preferences import FoodPreference

KEYWORDS: dict[str, tuple[str, ...]] = {
    # 질문 1: 현지 음식
    "familiar_taste": ("한국인 입맛", "입맛에 맞", "무난", "호불호 없", "자극적이지 않", "부모님도 잘", "어르신"),
    "strong_flavor": ("향신료", "향이 강", "호불호", "현지 느낌", "로컬 맛"),
    "spicy": ("맵다", "매워", "매운", "매콤"),  # "맵"만 쓰면 "구글맵"도 걸림
    "cilantro": ("고수",),
    # 질문 2: 한식
    "korean_signal": ("한식", "한국 음식", "김치", "된장", "한국인 사장", "한국어 메뉴"),
    # 질문 3: 식재료
    "seafood": ("해산물", "새우", "조개", "오징어", "생선", "랍스터", "꽃게", "굴 "),
    "pork": ("돼지", "삼겹", "포크", "족발", "보쌈", "베이컨"),
    "dairy": ("치즈", "우유", "크림", "버터", "요거트"),
    "nuts": ("땅콩", "견과", "캐슈넛", "아몬드", "호두"),
    "customizable": ("빼달라", "빼고", "빼주", "요청하면", "빼 달라"),
    # 질문 4: 식사 장소
    "street": ("노점", "길거리", "포장마차", "야시장", "플라스틱 의자"),
    "clean": ("에어컨", "깔끔", "청결", "위생"),
    # 부모님 동반 후기
    "parents": ("부모님", "엄마", "아빠", "어머니", "아버지", "효도"),
}

INGREDIENT_LABEL = {"seafood": "해산물", "pork": "돼지고기", "dairy": "유제품", "nuts": "견과류"}
MAX_EVIDENCE = 2
EVIDENCE_CHARS = 120


class TagHit(BaseModel):
    count: int  # 해당 키워드가 나온 글 수
    evidence: list[str] = []  # 근거 문장 (최대 2개, 앞부분만)


class Signals(BaseModel):
    text_count: int  # 분석한 글 수 (한국어 리뷰 + 요약)
    tags: dict[str, TagHit] = {}
    warnings: list[str] = []


def tag_texts(texts: list[str], extra: dict[str, tuple[str, ...]] | None = None) -> dict[str, TagHit]:
    dictionary = {**KEYWORDS, **(extra or {})}
    hits: dict[str, TagHit] = {}
    for tag, words in dictionary.items():
        matched = [t for t in texts if any(w in t for w in words)]
        if matched:
            hits[tag] = TagHit(
                count=len(matched), evidence=[t[:EVIDENCE_CHARS] for t in matched[:MAX_EVIDENCE]]
            )
    return hits


def analyze(texts: list[str], pref: FoodPreference) -> Signals:
    """태그를 세고, 부모님 취향과 부딪히는 신호를 경고 문장으로 만든다."""
    texts = [t for t in texts if t and t.strip()]
    extra = {f"other:{w}": (w,) for w in pref.avoid_other if w.strip()}
    tags = tag_texts(texts, extra)
    warnings = []
    customizable = "customizable" in tags

    for ingredient in pref.avoid_ingredients:
        if ingredient in tags:
            note = " (빼달라고 요청 가능하다는 후기 있음)" if customizable else ""
            warnings.append(f"{INGREDIENT_LABEL[ingredient]} 언급 {tags[ingredient].count}건{note}")
    for word in pref.avoid_other:
        key = f"other:{word}"
        if key in tags:
            warnings.append(f"'{word}' 언급 {tags[key].count}건")

    if not pref.street_food_ok and "street" in tags:
        warnings.append(f"길거리·노점 분위기 언급 {tags['street'].count}건")
    if pref.local_food == "familiar" and "strong_flavor" in tags:
        warnings.append(f"향이 강하다는 언급 {tags['strong_flavor'].count}건")

    return Signals(text_count=len(texts), tags=tags, warnings=warnings)
