// Screenshot an HTML card to PNG. Usage: node assets/capture.js <html> <png> [width] [height]
const path = require('path');
const fs = require('fs');

(async () => {
  const [htmlPath, outputPath, w, h] = process.argv.slice(2);
  if (!htmlPath || !outputPath) {
    console.error('Usage: node capture.js <html> <png> [width] [height]');
    process.exit(1);
  }
  const width = parseInt(w || '1080', 10);
  const height = parseInt(h || '1440', 10);
  let chromium;
  try { chromium = require('playwright').chromium; }
  catch { console.error('Playwright missing. Run in skill dir: npm install'); process.exit(1); }
  // --disable-gpu: macOS code-signing policy can deny Playwright's libEGL,
  // and a dying GPU process sometimes takes the whole browser down.
  const browser = await chromium.launch({ args: ['--disable-gpu'] });
  const page = await browser.newPage();
  await page.setViewportSize({ width, height });
  await page.goto('file://' + path.resolve(htmlPath), { waitUntil: 'networkidle' });
  await page.waitForTimeout(300);
  await page.screenshot({ path: outputPath, clip: { x: 0, y: 0, width, height } });
  await browser.close();
  console.log('OK: ' + outputPath);
})();
