import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";

const baseUrl = process.env.STATIC_DEMO_URL || "http://127.0.0.1:8766/";
const browser = await chromium.launch({ headless: true });
const checks = {};

async function visibleText(page, selector) {
  return page.locator(selector).innerText();
}

async function mustContain(page, selector, value) {
  const text = await visibleText(page, selector);
  if (!text.includes(value)) {
    throw new Error(`${selector} does not contain ${JSON.stringify(value)}`);
  }
}

try {
  await mkdir("artifacts", { recursive: true });
  const desktop = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  await desktop.goto(baseUrl, { waitUntil: "networkidle" });
  await desktop.locator("#load-demo").click();
  await mustContain(desktop, "body", "产品判断");
  await mustContain(desktop, "body", "业务与岗位理解");
  await mustContain(desktop, "body", "60/100");
  checks.review = true;

  await desktop.locator('[data-view="research-view"]').click();
  await desktop.locator("#discover-platform").selectOption("xiaohongshu");
  await desktop.locator("#discover-company").fill("示例科技");
  await desktop.locator("#discover-topic").fill("指标与项目深挖");
  await desktop.locator("#discover-button").click();
  await desktop.locator("#search-meta").waitFor({ state: "visible" });
  await mustContain(desktop, "#search-meta", "site:xiaohongshu.com");
  await mustContain(desktop, "#discovery-results", "manual_check_required");
  checks.xiaohongshuPreview = true;

  await desktop.locator("#agent-button").click();
  await desktop.locator("#agent-trace").waitFor({ state: "visible" });
  await mustContain(desktop, "#agent-trace", "不联网");
  checks.agentTrace = true;

  await desktop.locator('[data-view="review-view"]').click();
  await desktop.locator("#note-questions").click();
  const questionCount = await desktop.locator("#note-questions-panel .note-question").count();
  if (questionCount < 1) throw new Error("JD-to-question handoff produced no questions");
  await mustContain(desktop, "#note-questions-panel", "公开线索");
  await desktop.locator("#review-button").click();
  await mustContain(desktop, "#toast", "静态 Demo");
  checks.jdQuestionHandoff = questionCount;
  checks.readOnlyWrite = true;
  await desktop.screenshot({ path: "artifacts/static-demo-desktop.png", fullPage: true });

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto(baseUrl, { waitUntil: "networkidle" });
  const layout = await mobile.evaluate(() => {
    const overflow = document.body.scrollWidth > window.innerWidth + 1;
    const overflowingText = [...document.querySelectorAll("button,h1,h2,h3,h4,p,strong,span")]
      .filter((element) => {
        const rect = element.getBoundingClientRect();
        return rect.width > 0 && rect.right > window.innerWidth + 1;
      }).length;
    return { viewport: window.innerWidth, bodyWidth: document.body.scrollWidth, overflow, overflowingText };
  });
  if (layout.overflow || layout.overflowingText) {
    throw new Error(`mobile overflow: ${JSON.stringify(layout)}`);
  }
  checks.mobile = layout;
  await mobile.screenshot({ path: "artifacts/static-demo-mobile.png", fullPage: true });

  console.log(JSON.stringify({ ok: true, checks }));
} finally {
  await browser.close();
}
