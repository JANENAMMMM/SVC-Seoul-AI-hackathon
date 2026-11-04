"""관광지 주변 식당 수집. Google Places로 후보를 받고, 규칙으로 분류·선별한다.

데이터 저장 규칙: 식당 데이터(이름·평점·영업시간·리뷰 등)는 저장하지 않고 메모리에서만 쓴다.
일정에 남기는 건 place_id뿐이고, 다시 보여줄 때는 place_id로 재조회한다.
리뷰는 가공하지 않고 원문 그대로 담는다. 자세한 내용은 docs/restaurants/restaurant-collector.md.
"""
