import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { trimDemo } from "./trim-demo.mjs";

const folder = resolve("artifacts");
await mkdir(folder, { recursive: true });
const browser = await chromium.launch({ channel: "msedge", headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  recordVideo: { dir: folder, size: { width: 1440, height: 1000 } },
});
const page = await context.newPage();
try {
  await page.goto(process.env.UI_URL || "http://127.0.0.1:8131/");
  await page.locator(".source-footprint").waitFor();
  await page.evaluate(() => document.fonts.ready);
  const start = Date.now();
  async function until(ms) {
    await new Promise((r) =>
      setTimeout(r, Math.max(0, start + ms - Date.now())),
    );
  }
  async function caption(text) {
    await page.evaluate((t) => {
      let e = document.getElementById("recording-caption");
      if (!e) {
        e = document.createElement("div");
        e.id = "recording-caption";
        Object.assign(e.style, {
          position: "fixed",
          bottom: "14px",
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: "5000",
          padding: "12px 23px",
          background: "#173f32ed",
          color: "#fffef3",
          borderRadius: "8px",
          fontSize: "18px",
          fontFamily: "sans-serif",
          whiteSpace: "nowrap",
          boxShadow: "0 5px 20px #183d3030",
        });
        document.body.appendChild(e);
      }
      e.textContent = t;
    }, text);
  }
  await caption("15개 관광지 · 4개 평가 축 · 저장된 평가 28회");
  await page.screenshot({
    path: resolve(folder, "01-operator.png"),
    fullPage: false,
  });
  await until(6000);
  await page.locator(".environment-summary").scrollIntoViewIfNeeded();
  await page.locator(".dim-heat").scrollIntoViewIfNeeded();
  await caption("월별 체감온도에 그늘·실외 노출까지, 근거를 연결합니다");
  await page.screenshot({
    path: resolve(folder, "02-climate-evidence.png"),
    fullPage: false,
  });
  await until(14000);
  await page.locator(".verification-card").scrollIntoViewIfNeeded();
  await caption("인용·수치 검증과 반복 결과 집계, 마지막 결정은 사람에게");
  await until(20000);
  await page.getByRole("button", { name: "고객 화면", exact: true }).click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await caption("같은 근거가 부모님 조건에 맞춘 동선과 주의 태그로 이어집니다");
  await until(27000);
  await page
    .getByRole("button", { name: /이곳은 짧게 관람할래/ })
    .first()
    .click();
  const dismiss = page.getByRole("button", { name: "알림 닫기" });
  if (await dismiss.count()) await dismiss.click();
  await page
    .locator(".customer-layout")
    .evaluate((e) =>
      window.scrollTo(0, e.getBoundingClientRect().top + window.scrollY - 20),
    );
  await caption("오행산은 남기고 관람 방식을 변경 · 부담 상 → 중");
  await page.screenshot({
    path: resolve(folder, "03-customer-comparison.png"),
    fullPage: false,
  });
  await until(40000);
  await page.getByRole("button", { name: "이 변경 승인", exact: true }).click();
  if (await dismiss.count()) await dismiss.click();
  await caption("승인해야 일정에 반영됩니다. 공개 장소 점수는 바꾸지 않습니다");
  await until(47000);
  await page.getByRole("button", { name: "부모님께 공유" }).click();
  await caption("부모님께는 큰 글씨의 하루 요약과 의견 버튼으로");
  await page.screenshot({
    path: resolve(folder, "04-parent.png"),
    fullPage: false,
  });
  await until(55000);
  const video = page.video();
  await context.close();
  await trimDemo(
    await video.path(),
    resolve(folder, "bangeoreum-demo-55s.webm"),
  );
  console.log(
    "55-second demo rehearsal recorded. No paid model calls or DB writes.",
  );
} finally {
  await browser.close();
}
