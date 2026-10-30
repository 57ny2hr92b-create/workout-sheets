// Clicks through every slide of a built TV page at TV, phone and tablet sizes and fails on any
// text that spills out of its box. Usage: node scripts/check_tv.js docs/tv/index.html [screenshot-dir]
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
    const page = await browser.newPage({ viewport: { width, height } });
    // The container may block YouTube; the layout must hold without it.
    await page.route(/youtube/, r => r.abort());
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
        for (const el of document.querySelectorAll("header, main, nav, .media > *, .fit")) {
          const r = el.getBoundingClientRect();
          if (r.right > innerWidth + 1 || r.bottom > innerHeight + 1) out.push(`${el.className || el.tagName} off screen`);
        }
        const main = document.querySelector("main");
        if (main && main.scrollHeight > main.clientHeight + 1) out.push("main overflows");
        for (const el of document.querySelectorAll(".fit"))
          if (el.scrollHeight > el.clientHeight + 1) out.push(`text needs scrolling in .${el.className.split(" ")[0]}`);
        return out;
      });
      for (const b of bad) { problems++; console.log(`${tag} ${label}: ${b}`); }
    };
    await check("home");
    for (const d of days) {
      await page.click(`.day[data-day="${d}"]`);
      for (let n = 0; ; n++) {
        await check(`${d}-${n}`);
        const done = await page.$eval("nav .primary", b => b.textContent.includes("Done"));
        if (done) break;
        await page.click("nav .primary");
      }
      await page.click('nav [data-go="home"]');
    }
    await page.close();
  }
  await browser.close();
  console.log(problems ? `${problems} problem(s)` : "All slides fit.");
  process.exit(problems ? 1 : 0);
})();
