"""Interaction checks. Start mockup/serve.py, then uv run --with playwright python mockup/check_workspace.py."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8129/mockup/'
SHOTS = Path(__file__).parent / 'screenshots'
SHOTS.mkdir(exist_ok=True)


def fits(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'horizontal overflow'


with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in [1440, 1024, 768, 390, 320]:
        page = browser.new_page(viewport={'width': width, 'height': 1000})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(BASE, wait_until='domcontentloaded')
        fits(page)
        page.locator('#md-mode').click()
        fits(page)
        original = page.evaluate('structuredClone(workshop.days)')
        page.locator('[data-ws-add="cafe"]').click()
        assert page.evaluate('workshop.days[0].at(-1)') == 'cafe'
        assert '미확인' in page.locator('.studio-inspector').inner_text()
        # A rest adds its own illustrative distance; it does not subtract walking.
        assert page.evaluate('workshopMetrics(workshop.days[0]).meters') > page.evaluate('workshopMetrics(workshop.original[0]).meters')
        page.locator('#ws-undo').click()
        assert page.evaluate('workshop.days') == original
        page.locator('[data-ws-down="0"]').click()
        assert page.evaluate('workshop.days[0][1]') == original[0][0]
        page.locator('[data-ws-move="1"]').select_option('2')
        assert page.evaluate('workshop.days[2].at(-1)') == original[0][0]
        page.locator('#ws-undo').click()
        page.locator('#ws-undo').click()
        assert page.evaluate('workshop.days') == original
        page.locator('#ws-search').fill('없을장소')
        assert page.locator('.empty-shelf').count() == 1
        page.locator('#ws-search').fill('')
        page.locator('[data-ws-filter="rest"]').click()
        assert page.locator('[data-shelf]').count() == 2
        page.locator('[data-ws-filter="all"]').click()
        page.locator('[data-ws-day="1"]').click()
        page.locator('[data-ws-select="hoian"]').first.click()
        assert page.locator('.studio-evidence').inner_text().find('직접 확인') >= 0
        fits(page)
        page.locator('[data-ws-pane="map"]').click()
        page.locator('#ws-preview').click()
        assert page.locator('.preview-day').count() == 3
        fits(page)
        with page.expect_download() as download:
            page.locator('#ws-export').click()
        guide = Path(download.value.path()).read_text()
        assert '직접 확인' in guide and '미확인' in guide and '호이안' in guide
        page.locator('#ws-back').click()
        assert page.evaluate('workshop.days') == original
        page.locator('#customer-mode').click()
        assert page.locator('.landing-hero').count() == 1
        page.locator('[data-start="0"]').first.click()
        page.locator('#form-submit').click()
        fits(page)
        # Single selections remain exclusive and support keyboard activation.
        chip = page.locator('[data-choice="korean_need"][data-value="none"]')
        chip.focus()
        page.keyboard.press('Space')
        assert chip.get_attribute('aria-pressed') == 'true'
        assert page.locator('[data-choice="korean_need"][aria-pressed="true"]').count() == 1
        page.locator('[data-choice="must"][data-value="craft"]').click()
        page.locator('[data-choice="avoid_conditions"][data-value="stairs"]').click()
        page.locator('[data-choice="venues"][data-value="unknown"]').click()
        assert page.locator('[data-choice="venues"][aria-pressed="true"]').count() == 1
        page.locator('[data-choice="venues"][data-value="restaurant"]').click()
        assert page.locator('[data-choice="venues"][data-value="unknown"]').get_attribute('aria-pressed') == 'false'
        if width in [1440, 390]:
            page.screenshot(path=str(SHOTS / f'choices-{width}.png'), full_page=True)
        page.locator('#form-submit').click()
        page.locator('#agenda').wait_for()
        assert page.evaluate('state.musts.includes("craft") && state.musts.includes("temple")')
        assert page.evaluate('state.musts.every(id=>rawDays().some(d=>d.ids.includes(id)))')
        assert '계단·경사' in page.locator('#agenda .verification-note').inner_text()
        fits(page)
        page.locator('#compare').click()
        assert '공예' in page.locator('.compare-table').inner_text()
        page.locator('[data-close="detail"]').click()
        page.locator('#share-trip').click()
        with page.expect_download() as download:
            page.locator('#download-all').click()
        guide = Path(download.value.path()).read_text()
        assert '직접 확인' in guide and '공예' in guide
        page.locator('[data-close="share"]').click()
        # Returning to MD retains edited state; customer profiles are separate.
        page.locator('#md-mode').click()
        fits(page)
        if width in [1440, 390]:
            page.screenshot(path=str(SHOTS / f'workspace-{width}.png'), full_page=True)
        assert not errors, errors
        print(f'PASS {width}px: choices, MD edit/undo/move, preview, downloads, role switch, no overflow/errors', flush=True)
        page.close()

    # Native drag operations must run the same mutations as accessible buttons.
    page = browser.new_page(viewport={'width':1440,'height':1050})
    page.goto(BASE)
    page.locator('#md-mode').click()
    page.locator('[data-ws-filter="rest"]').click()
    page.locator('[data-shelf="cafe"]').drag_to(page.locator('.insert-slot').first, source_position={'x':12, 'y':12})
    assert page.evaluate('workshop.days[0][0]') == 'cafe'
    page.locator('#ws-undo').click()
    # Reorder adjacent visible cards; drag_to does not emulate edge auto-scroll.
    page.locator('[data-ws-card="1"]').drag_to(page.locator('.insert-slot').first, source_position={'x':12, 'y':12})
    assert page.evaluate('workshop.days[0].slice(0,2)') == ['temple', 'beach']
    page.locator('#ws-undo').click()
    assert page.evaluate('JSON.stringify(workshop.days) === JSON.stringify(workshop.original)')
    print('PASS native drag: shelf addition, reorder, undo', flush=True)
    # Empty day remains editable and removable; no false success status.
    while page.locator('[data-ws-remove]').count():
        page.locator('[data-ws-remove]').first.click()
    assert page.locator('.schedule-card').count() == 0
    assert '미확인' in page.locator('.studio-inspector').inner_text()
    page.locator('[data-ws-filter="all"]').click()
    page.locator('[data-ws-add="temple"]').click()
    assert page.locator('.schedule-card').count() == 1
    page.emulate_media(reduced_motion='reduce')
    assert page.locator('.schedule-card').evaluate("el => getComputedStyle(el).transitionDuration") == '0s'
    print('PASS empty day, reduced motion', flush=True)
    page.locator('#customer-mode').click()
    page.locator('[data-start="0"]').first.click()
    page.locator('#form-submit').click()
    page.locator('#avoid_other').fill('고수')
    page.locator('[data-choice="must"][data-value="craft"]').click()
    page.locator('#md-mode').click()
    page.locator('#customer-mode').click()
    assert page.locator('#avoid_other').input_value() == '고수'
    assert page.locator('[data-choice="must"][data-value="craft"]').get_attribute('aria-pressed') == 'true'
    print('PASS role switch retains unfinished customer choices', flush=True)
    browser.close()
