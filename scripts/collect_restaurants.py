"""관광지 주변 추천 식당 수집 실행 (테스트용, 결과는 화면에만 출력하고 저장하지 않음).

예시 (루트에서):
    uv run python scripts/collect_restaurants.py \
        --attractions scripts/examples/attractions_danang.json \
        --city 다낭 --country VN --limit 1

필요한 환경변수: GOOGLE_API_KEY
호출 수(관광지 1곳): 반경 검색 1~2회 + 리뷰 조회 최대 5회. 실행할 때마다 다시 호출한다.

저장 규칙: 결과는 화면에만 출력하고 저장하지 않는다. 일정에 남기는 건 place_id뿐이다.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.restaurants.collect import Attraction, collect  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="관광지 주변 추천 식당 수집 (저장 없음)")
    parser.add_argument("--attractions", type=Path, required=True, help="관광지 목록 JSON")
    parser.add_argument("--city", required=True, help="도시명 (예: 다낭)")
    parser.add_argument("--country", help="ISO 국가 코드 (예: VN). 현지 음식 판단에 사용")
    parser.add_argument("--radius", type=float, default=1000, help="반경 m (기본 1000)")
    parser.add_argument("--limit", type=int, default=1, help="앞에서부터 관광지 몇 곳만 (기본 1)")
    parser.add_argument(
        "--no-reviews", action="store_true", help="리뷰 단계 건너뛰기 (Atmosphere 등급 호출 안 함)"
    )
    args = parser.parse_args()

    attractions = [
        Attraction.model_validate(a)
        for a in json.loads(args.attractions.read_text(encoding="utf-8"))
    ][: args.limit]

    result = collect(
        attractions,
        city=args.city,
        country=args.country,
        radius_m=args.radius,
        with_reviews=not args.no_reviews,
    )

    for a in result.attractions:
        print(f"\n[{a.attraction.name}] 후보 {a.candidates_total}곳, 제외 {len(a.excluded)}곳")
        for i, r in enumerate(a.restaurants, 1):
            info = r.reviews
            rev = (
                f" · 리뷰 {info.returned_count}개 중 한국어 {len(info.korean_reviews)}개"
                f"{' · 요약 있음' if info.summary else ''}"
                if info
                else ""
            )
            print(
                f"  {i}. {r.name} ({r.cuisine_tag}) ★{r.rating} ({r.rating_count}) "
                f"{r.distance_m}m{rev}"
            )
            print(f"     place_id: {r.place_id}")


if __name__ == "__main__":
    main()
