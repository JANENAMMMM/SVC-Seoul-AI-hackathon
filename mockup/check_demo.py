"""로컬 시연 E2E. 먼저 uv run python mockup/serve.py 실행.
검사: uv run --with playwright python mockup/check_demo.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8129/mockup/"
SHOTS = Path(__file__).resolve().parent / "screenshots"
SHOTS.mkdir(exist_ok=True)


def no_overflow(page, label):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), label


def create(page, case):
    page.goto(BASE, wait_until="domcontentloaded")
    page.locator(f'.case-card[data-start="{case}"]').click()
    page.locator("#form-submit").click()
    page.locator("#form-submit").click()
    page.locator("#agenda").wait_for()


with sync_playwright() as p:
    browser = p.chromium.launch()
    for width, height in [(1440, 1000), (390, 844), (320, 740)]:
        for case in range(3):
            page = browser.new_page(viewport={"width": width, "height": height})
            errors, profile_requests = [], []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("request", lambda r: profile_requests.append(r.post_data_json) if r.url.endswith("/api/profile") else None)
            page.goto(BASE, wait_until="domcontentloaded")
            no_overflow(page, "landing")
            if case == 0:
                page.screenshot(path=str(SHOTS / f"landing-{width}.png"), full_page=True)
            page.locator(f'.case-card[data-start="{case}"]').click()
            no_overflow(page, "booking")
            expected_nights = 4 if case == 1 else 3
            assert page.locator("#nights").input_value() == str(expected_nights)
            assert page.evaluate("total()") == [2, 5, 4][case]
            page.locator("#form-submit").click()
            no_overflow(page, "profiles")
            assert page.locator(".person-profile").count() == (0 if case == 2 else 2)
            page.locator("#form-submit").click()
            page.locator("#agenda").wait_for()
            assert page.evaluate("state.profileMode") == ("not-needed" if case == 2 else "api")
            assert len(profile_requests) == (0 if case == 2 else 2)
            if profile_requests:
                assert "walking_duration" in profile_requests[0]
                assert "korean_need" in profile_requests[0]
                assert page.evaluate("state.profiles[0].walking_speed.base_speed_mps") > 0
            assert page.locator("[data-day]").count() == expected_nights + 1
            no_overflow(page, "planner")
            # Independent fixes: rests do not lower total walking; shorter routes do.
            before = page.evaluate("evaluateDay(selectedDay).totalWalk")
            page.locator('[data-fix="rest"]').click()
            assert page.evaluate("evaluateDay(selectedDay).totalWalk") == before
            if page.locator('[data-fix="short"]').count():
                page.locator('[data-fix="short"]').click()
                assert page.evaluate("evaluateDay(selectedDay).totalWalk") < before
            assert page.evaluate("rawDays().some(d=>d.ids.includes(state.must))")
            fixed = page.evaluate("Array.from(state.fixes)")
            page.locator('[data-day="0"]').click()
            page.locator('[data-day="1"]').click()
            assert page.evaluate("Array.from(state.fixes)") == fixed
            # Day selection changes map markers and schedule.
            for day in range(expected_nights + 1):
                page.locator(f'[data-day="{day}"]').click()
                assert page.evaluate("selectedDay") == day
                assert page.evaluate("markers.length") == page.evaluate("evaluateDay(selectedDay).items.filter(i=>i.id&&i.kind!=='break').length")
                no_overflow(page, f"day {day}")
            page.locator('[data-day="1"]').click()
            if width < 900:
                page.locator("#show-map").click()
                assert page.locator(".map-panel.mobile-open").is_visible()
                page.locator("#close-map").click()
            else:
                page.locator(".stop-card").first.click()
                assert page.locator(".stop-card.selected").count() == 1
                assert page.locator("#map-selection").inner_text().find("내부 보행") >= 0
                page.locator('.number-marker').nth(1).click()
                assert page.evaluate('selectedStop') == page.evaluate('markers[1].index')
                page.locator("[data-detail]").click()
                assert page.locator("#detail").is_visible()
                page.locator('[data-close="detail"]').click()
            page.locator("#compare").click()
            assert page.locator(".compare-table").is_visible()
            assert page.locator(".compare-table").inner_text().find("유지") >= 0
            page.locator('[data-close="detail"]').click()
            page.locator('[data-view="overview"]').click()
            assert page.locator(".overview-day").count() == expected_nights + 1
            no_overflow(page, "overview")
            page.locator('[data-overview-day="2"]').click()
            page.locator("#share-trip").click()
            page.locator('[data-card-day="0"]').click()
            with page.expect_download() as download:
                page.locator('[data-download="0"]').click()
            assert "<svg" in Path(download.value.path()).read_text()
            with page.expect_download() as download:
                page.locator("#download-all").click()
            guide = Path(download.value.path()).read_text()
            assert f"{expected_nights}박 {expected_nights + 1}일" in guide
            assert f"DAY {expected_nights + 1}" in guide
            page.locator('[data-close="share"]').click()
            if case == 1:
                page.screenshot(path=str(SHOTS / f"planner-{width}.png"), full_page=True)
            assert not errors, errors
            print(f"PASS {width}px case {case+1}: counts, {expected_nights+1} days, API, independent fixes, map, comparison, downloads; no JS errors/overflow", flush=True)
            page.close()

    # User edits: senior count is a subset of adults, child ages and nights update.
    page = browser.new_page()
    page.goto(BASE, wait_until="domcontentloaded")
    page.locator('.case-card[data-start="2"]').click()
    page.locator('#departure').fill('2027-01-09')
    page.locator('#departure').press('Tab')
    page.locator('#nights').select_option('5')
    page.locator('[data-count="seniors"][data-delta="1"]').click()
    assert page.evaluate('total()') == 4
    assert page.evaluate('state.seniors.length') == 1
    page.locator('[data-child="0"]').fill('10')
    page.locator('#form-submit').click()
    assert page.evaluate('state.children[0]') == 10
    page.locator('[data-profile="0"][data-key="age"]').fill('76')
    page.locator('[data-choice="must"][data-value="hoian"]').click()
    page.locator('[data-choice="venues"][data-value="street_food"]').click()
    page.locator('#avoid_other').fill('고수, 매운 음식')
    page.locator('[data-choice="ingredients"][data-value="nuts"]').click()
    page.locator('#form-submit').click()
    page.locator('#agenda').wait_for()
    assert page.evaluate('state.profiles[0].age') == 76
    assert page.evaluate('state.profiles[0].venues') == ['restaurant', 'street_food']
    assert page.evaluate('state.profiles[0].avoid_other') == ['고수', '매운 음식']
    assert page.evaluate('state.profiles[0].avoid_ingredients') == ['nuts']
    assert page.evaluate('dateAt(state.nights).getDate()') == 14
    assert page.locator('[data-day]').count() == 6
    assert page.evaluate('rawDays().some(d=>d.ids.includes("hoian"))')
    print('PASS: edited nights, senior subset, child age, API age and required experience', flush=True)
    page.close()

    # API and map provider failures remain explicit and do not break the demo.
    page = browser.new_page(viewport={"width":390,"height":844})
    page.route('**/api/profile', lambda route: route.abort())
    page.route('**/tile.openstreetmap.org/**', lambda route: route.abort())
    create(page, 0)
    assert page.evaluate('state.profileMode') == 'demo'
    assert page.locator('.ribbon-status').inner_text().find('API 미연결') >= 0
    page.locator('#show-map').click()
    page.locator('#map-fallback').wait_for(state='visible')
    assert page.evaluate('markers.length') > 0
    page.locator('#close-map').click()
    print('PASS: API and map-tile failure fallback retains location markers and explicit data status', flush=True)
    page.close()
    # Invalid successful responses must not cause zero/negative/infinite walk calculations.
    for invalid_speed in [0, -1, None, "1.0"]:
        page = browser.new_page()
        page.route(
            "**/api/profile",
            lambda route, request, value=invalid_speed: route.fulfill(
                json={"walking_speed": {"base_speed_mps": value}}
            ),
        )
        create(page, 0)
        assert page.evaluate("state.profileMode") == "demo"
        assert page.evaluate("Number.isFinite(evaluateDay(selectedDay).totalWalk)")
        assert page.evaluate("state.profiles.every(p=>p.walking_speed===null)")
        page.close()
    print("PASS: invalid profile speeds use explicit demo fallback with finite walk times", flush=True)
    browser.close()
