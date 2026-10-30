// Clicks through every slide of a built TV page at TV, phone and tablet sizes and fails on any
// text that spills out of its box. It also opens the rest timer, starts the warm-up and finisher
// timers, and switches to the drawing, so those screens are checked too.
// Usage: node scripts/check_tv.js docs/tv/index.html[?style=...] [screenshot-dir]
const { chromium } = require("playwright");
const path = require("path");

const SIZES = [["tv", 1920, 1080], ["phone", 844, 390], ["small-phone", 667, 375], ["ipad", 1180, 820], ["portrait", 390, 844]];

(async () => {
  const [target, query = ""] = process.argv[2].split("?");
  const file = "file://" + path.resolve(target) + (query ? "?" + query : "");
  const shots = process.argv[3];
  const browser = await chromium.launch();
  let problems = 0;
  for (const [tag, width, height] of SIZES) {
    const context = await browser.newContext({ viewport: { width, height } });
    const page = await context.newPage();
    // The container may block YouTube; the layout must hold without it.
    await page.route(/youtube|ytimg/, r => r.abort());
    page.on("pageerror", e => { problems++; console.log(`${tag}: script error: ${e.message}`); });
    await page.goto(file);
    await page.evaluate(() => document.fonts.ready);
    const days = await page.$$eval(".day", bs => bs.map(b => b.dataset.day));
    const check = async label => {
      if (shots) await page.screenshot({ path: `${shots}/${tag}-${label}.png` });
      if (tag === "portrait") return; // portrait scrolls by design
      const bad = await page.evaluate(() => {
        const out = [];
        if (document.documentElement.scrollWidth > innerWidth + 1) out.push("page scrolls sideways");
        const rest = document.querySelector("#rest.on .card");
        const boxes = rest ? [rest, ...rest.children] : document.querySelectorAll("header, main, nav, main section > *, .stage > *, .track > *, .fit");
        for (const el of boxes) {
          const r = el.getBoundingClientRect();
          if (r.right > innerWidth + 1 || r.bottom > innerHeight + 1 || r.left < -1 || r.top < -1) out.push(`${el.className || el.id || el.tagName} off screen`);
        }
        const main = document.querySelector("main");
        if (main && main.scrollHeight > main.clientHeight + 1) out.push("main overflows");
        for (const el of document.querySelectorAll(".fit"))
          if (el.scrollHeight > el.clientHeight + 1) out.push(`text needs scrolling in .${el.className.split(" ")[0]}`);
        const vid = document.querySelector(".video");
        // Very long coaching text may squeeze the video (the .tight layout); normal slides must not.
        if (vid && !document.querySelector(".ex.tight") && vid.getBoundingClientRect().height < innerHeight * .25) out.push("video squeezed under a quarter of the screen");
        return out;
      });
      for (const b of bad) { problems++; console.log(`${tag} ${label}: ${b}`); }
    };
    await check("home");
    for (const d of days) {
      await page.click(`.day[data-day="${d}"]`);
      for (let n = 0; ; n++) {
        const kind = await page.$eval("main section", s => s.className.split(" ")[0]);
        const finisher = await page.$("#c-go");
        if (kind === "timed" && n === 0) await page.click("[data-w]:last-child, [data-w]").catch(() => {});
        await check(`${d}-${n}`);
        if (kind === "ex" && (n === 1 || n === 2)) {
          // Drawing view, then one set done to bring up the rest timer (or the superset hand-off).
          const drawing = await page.$('[data-media]:last-child');
          if (drawing) { await drawing.click(); await check(`${d}-${n}-drawing`); }
          await page.click("[data-set]");
          if (await page.$("#rest.on")) { await check(`${d}-${n}-rest`); await page.click('[data-r="skip"]'); }
          await page.click(`[data-jump="${n}"]`);
        }
        if (finisher) { await finisher.click(); await page.waitForTimeout(300); await check(`${d}-${n}-running`); await finisher.click(); }
        const last = await page.$eval("nav .primary", b => b.dataset.go === "finish");
        if (last) { await page.click("nav .primary"); break; }
        await page.click("nav .primary");
      }
    }
    await check("home-after");
    await context.close();
  }
  await browser.close();
  console.log(problems ? `${problems} problem(s)` : "All slides fit.");
  process.exit(problems ? 1 : 0);
})();
