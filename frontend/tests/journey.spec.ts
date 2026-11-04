import { test, expect } from "@playwright/test";

test("운영자 근거 → 고객 변경 취소·승인 → 부모님 의견", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "관광지 난이도 관리",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "더위 평가에 사용한 기후 자료" }),
  ).toBeVisible();
  await expect(
    page.getByText("최종 점수와 근거 연결", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/operator-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "고객 일정에서 확인" }).click();
  await page
    .getByRole("button", { name: /이곳은 짧게 관람할래/ })
    .first()
    .click();
  await expect(page.getByRole("region", { name: "변경안" })).toBeVisible();
  await expect(page.locator(".changed-place-views")).toContainText("오행산");
  await expect(page.locator(".changed-place-views")).toContainText("부담 상");
  await expect(page.locator(".changed-place-views")).toContainText("부담 중");
  await expect(page.getByText("승인 대기 · 현재 일정은 유지 중")).toBeVisible();
  await page.screenshot({
    path: "test-results/customer-comparison-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "되돌리기", exact: true }).click();
  await expect(page.getByRole("region", { name: "변경안" })).toHaveCount(0);
  await page
    .getByRole("button", { name: /이곳은 짧게 관람할래/ })
    .first()
    .click();
  await page.getByRole("button", { name: "이 변경 승인", exact: true }).click();
  await expect(
    page.getByText("승인했어요. 동선과 관람 방식에 반영했어요."),
  ).toBeVisible();
  await page.getByRole("button", { name: "부모님께 공유" }).click();
  await expect(page.getByRole("dialog", { name: "부모님 공유" })).toBeVisible();
  await page
    .getByRole("button", { name: "힘들 것 같아요", exact: true })
    .click();
  await expect(
    page.getByText("의견을 보냈어요. 자녀가 확인한 뒤 일정을 바꿔요."),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/parent-share.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "공유 닫기" }).click();
  await page.getByRole("button", { name: "부모님 의견 확인" }).click();
  await expect(page.locator(".opinion").first()).toContainText(
    "힘들 것 같아요",
  );
  expect(errors).toEqual([]);
});

test("390px 모바일은 하단 탭으로 조정·승인하고 가로 넘침이 없다", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "고객 화면", exact: true }).click();
  await expect(page.locator(".mobile-tabs")).toBeVisible();
  await expect(page.locator(".route-panel")).toBeVisible();
  await page
    .locator(".mobile-tabs")
    .getByRole("button", { name: "조정", exact: true })
    .click();
  await expect(page.locator(".adjust-panel")).toBeVisible();
  await page
    .getByRole("button", { name: /이곳은 짧게 관람할래/ })
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "이 변경 승인" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/customer-comparison-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "이 변경 승인" }).click();
  await expect(page.locator(".route-panel")).toBeVisible();
  await page.screenshot({
    path: "test-results/customer-route-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("실제 MD 미인증 검수는 차단하고 현재 UI는 유지한다", async ({ page }) => {
  await page.goto("/?live=1");
  await page.getByRole("button", { name: "승인 대기", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "운영자 인증" }),
  ).toBeVisible();
  const response = await page.request.get("/api/ui/md/feedback");
  expect(response.status()).toBe(403);
  const legacy = await page.request.get("/api/hitl/feedback");
  expect(legacy.status()).toBe(403);
});

test("부모님 두 분의 조건을 버튼·선택으로 각각 입력할 수 있다", async ({
  page,
}) => {
  await page.goto("/?live=1");
  await page.getByRole("button", { name: "고객 화면", exact: true }).click();
  await page.getByRole("button", { name: "부모님", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "두 번째 부모님 조건" }),
  ).toBeVisible();
  await page.getByLabel("두 번째 부모님 보행 시간").selectOption("under_15min");
  await expect(page.getByLabel("두 번째 부모님 보행 시간")).toHaveValue(
    "under_15min",
  );
});

test("MD 선택 승인은 재채점 완료만 허용하고 건별 실패를 남긴다", async ({
  page,
}) => {
  let loggedIn = false;
  const ready = [
    {
      id: "ui-test-ready-a",
      status: "rejudged",
      place_id: "dad-02",
      raw_text: "테스트 검수 A",
      created_at: "2026-11-04",
    },
    {
      id: "ui-test-ready-b",
      status: "rejudged",
      place_id: "dad-03",
      raw_text: "테스트 검수 B",
      created_at: "2026-11-04",
    },
  ];
  await page.route("**/api/ui/md/session", async (route) => {
    loggedIn = true;
    await route.fulfill({ json: { authenticated: true } });
  });
  await page.route("**/api/ui/md/evaluation", (route) =>
    route.fulfill({ json: { runs: 28, matched_dimensions: 60 } }),
  );
  await page.route("**/api/ui/md/feedback**", async (route) => {
    if (!loggedIn) {
      await route.fulfill({
        status: 403,
        json: { detail: "운영자 로그인이 필요합니다." },
      });
      return;
    }
    const url = route.request().url();
    if (url.endsWith("/ui-test-ready-a/approve"))
      await route.fulfill({ json: { status: "applied" } });
    else if (url.endsWith("/ui-test-ready-b/approve"))
      await route.fulfill({
        status: 409,
        json: { detail: "이미 처리된 조정입니다." },
      });
    else
      await route.fulfill({
        json: url.includes("status=rejudged") ? ready : [],
      });
  });
  await page.goto("/?live=1");
  await page.getByRole("button", { name: "승인 대기", exact: true }).click();
  await page.getByLabel("운영자 인증값").fill("test-only");
  await page.getByRole("button", { name: "로그인", exact: true }).click();
  await page.getByLabel("검수 상태").selectOption("rejudged");
  await page.getByLabel("ui-test-ready-a 선택").check();
  await page.getByLabel("ui-test-ready-b 선택").check();
  await page.getByRole("button", { name: "선택 승인 (2)" }).click();
  await expect(
    page.getByText("ui-test-ready-a · 승인", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("ui-test-ready-b · 실패: 이미 처리된 조정입니다.", {
      exact: true,
    }),
  ).toBeVisible();
});

test("운영자 목록의 상중하는 1100px에서도 숨겨지지 않는다", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1100, height: 900 });
  await page.goto("/");
  await expect(page.locator(".place-list .grade")).toHaveCount(15);
  await expect(page.locator(".place-list .grade").first()).toBeVisible();
  await expect(page.locator(".place-list .grade").first()).toHaveText("상");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("타일 요청 실패 때 정책 오류 이미지 대신 위치·순서를 유지한다", async ({
  page,
}) => {
  await page.route("https://tile.openstreetmap.org/**", (route) =>
    route.fulfill({ status: 403, body: "blocked" }),
  );
  await page.goto("/");
  await expect(page.locator(".map-wrap").first()).toHaveAttribute(
    "data-background",
    "unavailable",
  );
  await expect(page.locator(".map-failure")).toContainText(
    "위치와 방문 순서는 표시됩니다",
  );
  await expect(page.locator(".leaflet-marker-icon")).toHaveCount(1);
  await expect(page.locator(".leaflet-tile-pane img")).toHaveCount(0);
});

test("시연 검수는 원본 등급을 바꾸지 않고 완료 기록으로 이동한다", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "승인 대기", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "검수 대기 1건" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "검수 완료로 표시", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "검수 대기 0건" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "조정 기록", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "검수 완료 1건" }),
  ).toBeVisible();
  await expect(page.locator(".demo-review-row")).toContainText("한시장");
  await expect(page.locator(".demo-review-row")).toContainText("부담 하");
});
