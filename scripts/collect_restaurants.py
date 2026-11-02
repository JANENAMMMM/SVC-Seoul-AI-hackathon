"""관광지 주변 추천 식당 수집 실행.

예시 (루트에서):
    uv run python scripts/collect_restaurants.py \
        --attractions scripts/examples/attractions_danang.json \
        --prefs scripts/examples/food_prefs_example.json \
        --city 다낭 --country VN

필요한 환경변수: GOOGLE_API_KEY
결과: data/restaurants/result_<city>.json, API 응답 캐시: data/restaurants/google|google_reviews/
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.restaurants.collect import DEFAULT_CACHE_DIR, Attraction, collect, save_result  # noqa: E402
from src.restaurants.preferences import FoodPreference  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="관광지 주변 추천 식당 수집")
    parser.add_argument("--attractions", type=Path, required=True, help="관광지 목록 JSON")
    parser.add_argument("--prefs", type=Path, required=True, help="부모님 음식 취향 JSON")
    parser.add_argument("--city", required=True, help="도시명 (예: 다낭). 결과 파일 이름에 사용")
    parser.add_argument("--country", help="ISO 국가 코드 (예: VN). 현지 음식 판단에 사용")
    parser.add_argument("--radius", type=float, default=1000, help="반경 m (기본 1000)")
    parser.add_argument(
        "--no-reviews", action="store_true", help="리뷰 단계 건너뛰기 (Atmosphere 등급 호출 안 함)"
    )
    parser.add_argument("--refresh", action="store_true", help="캐시를 무시하고 API 다시 호출")
    parser.add_argument("--out", type=Path, help="결과 파일 경로")
    args = parser.parse_args()

    attractions = [
        Attraction.model_validate(a)
        for a in json.loads(args.attractions.read_text(encoding="utf-8"))
    ]
    pref = FoodPreference.model_validate_json(args.prefs.read_text(encoding="utf-8"))

    result = collect(
        attractions,
        pref,
        city=args.city,
        country=args.country,
        radius_m=args.radius,
        with_reviews=not args.no_reviews,
        refresh=args.refresh,
    )
    out = args.out or DEFAULT_CACHE_DIR / f"result_{args.city}.json"
    save_result(result, out)

    for a in result.attractions:
        print(f"\n[{a.attraction.name}] 후보 {a.candidates_total}곳, 제외 {len(a.excluded)}곳")
        for i, r in enumerate(a.restaurants, 1):
            info = r.reviews
            warn = f"  ⚠ {'; '.join(info.signals.warnings)}" if info and info.signals.warnings else ""
            rev = (
                f" · 리뷰 {info.returned_count}개 중 한국어 {len(info.korean_reviews)}개"
                f"{' · 요약 있음' if info.summary else ''}"
                if info
                else ""
            )
            print(
                f"  {i}. {r.name} ({r.cuisine_tag}) ★{r.rating} ({r.rating_count}) "
                f"{r.distance_m}m{rev}{warn}"
            )
    print(f"\n저장: {out}")


if __name__ == "__main__":
    main()
