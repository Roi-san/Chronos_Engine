// Click through Brain Dump in a real (headless) Chrome against a throwaway copy,
// give one task a length, and check Home's "no length" tag.
const { chromium } = require('playwright-core');
const BASE = process.argv[2];
const SHOTS = process.argv[3];
(async () => {
  for (let i = 0; i < 60; i++) {
    try { const r = await fetch(BASE + '/health'); if (r.ok) break; } catch (e) {}
    await new Promise(res => setTimeout(res, 500));
  }
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  await page.goto(BASE + '/dashboard.html', { waitUntil: 'domcontentloaded' });
  const enter = page.locator('button', { hasText: /^\s*Enter\s*$/i }).first();
  if (await enter.count()) { await enter.click().catch(() => {}); }
  await page.waitForTimeout(2500);

  // Home: the task planned with the default length carries the "no length" tag.
  const homeText = await page.locator('body').innerText();
  const tagShown = /Call the bank e2e[\s\S]{0,80}no length/.test(homeText);
  console.log('Home shows "Call the bank e2e" with the "no length" tag:', tagShown);
  await page.screenshot({ path: SHOTS + '/home.png', fullPage: false });

  // Brain Dump: capture two tasks, give the first a length of 20 minutes.
  // Startup popups sit on top of everything; close them before the wizard.
  await page.evaluate(() => document.querySelectorAll('.alpha-launch-overlay, .ycheck-overlay, [class*="popup"][class*="overlay"]').forEach(el => el.remove()));
  await page.evaluate(async () => {
    const m = await import('/wizards/brain_dump/index.js');
    await m.launch({ bus: window.ChronosBus }, {});
  });
  await page.locator('[data-field="captureText"]').fill('Water the plants e2e\nCall mum e2e');
  for (let step = 0; step < 4 && !(await page.locator('[data-field="duration"]').count()); step++) {
    await page.locator('[data-action="next"]').click({ timeout: 5000 });
    await page.waitForTimeout(400);
  }
  const lengthFields = page.locator('[data-field="duration"]');
  console.log('Length fields on the Refine step:', await lengthFields.count());
  await lengthFields.first().fill('20');
  await page.screenshot({ path: SHOTS + '/refine.png', fullPage: false });
  await page.locator('[data-action="create"]').click({ timeout: 5000 });
  await page.waitForTimeout(3000);
  const status = await page.locator('body').innerText();
  console.log('Status line:', (status.match(/Created [^\n]*/) || ['(none)'])[0]);
  console.log('Errors:', errors.length ? errors : 'none');
  await browser.close();
})().catch(e => { console.error('SCRIPT FAILED:', e.message); process.exit(1); });
