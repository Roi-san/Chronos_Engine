// Walk the Chore Setup wizard to the end in a real (headless) Chrome against a
// throwaway copy (roadmap step 1c, decision D2; tracker issues 22 and 29).
// Keeps six built-in chores (one per rhythm, two weekly), adds one custom weekly
// chore, picks days where the wizard offers a day picker, presses Create, and
// prints what the wizard says. Check the files it wrote afterwards:
//   python scripts/regression/chore_files.py <export>
// Usage: NODE_PATH=<scratch>/node_modules node chore_setup_check.js <base url> <screenshot dir>
const { chromium } = require('playwright-core');
const BASE = process.argv[2];
const SHOTS = process.argv[3];
const KEEP = ['Wash Dishes', 'Laundry', 'Vacuum Floors', 'Wash Windows', 'Replace HVAC Filter', 'Test Smoke and CO Alarms'];
const PICK = { 'Laundry': 'saturday', 'Wash Windows': '15' };

(async () => {
  for (let i = 0; i < 60; i++) {
    try { const r = await fetch(BASE + '/health'); if (r.ok) break; } catch (e) {}
    await new Promise(res => setTimeout(res, 500));
  }
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 950 } });
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  await page.goto(BASE + '/dashboard.html', { waitUntil: 'domcontentloaded' });
  const enter = page.locator('button', { hasText: /^\s*Enter\s*$/i }).first();
  if (await enter.count()) { await enter.click().catch(() => {}); }
  await page.waitForTimeout(2500);
  // Startup popups sit on top of everything; close them before the wizard.
  await page.evaluate(() => document.querySelectorAll('.alpha-launch-overlay, .ycheck-overlay, [class*="popup"][class*="overlay"]').forEach(el => el.remove()));
  await page.evaluate(async () => {
    const m = await import('/wizards/chore_setup/index.js');
    await m.launch({ bus: window.ChronosBus }, {});
  });
  await page.waitForTimeout(800);

  // Keep only KEEP among the built-in chores (each row: a checkbox and the name in <strong>).
  const kept = await page.evaluate((keep) => {
    const out = [];
    document.querySelectorAll('.chore-setup-overlay label.chore-item').forEach(row => {
      const name = (row.querySelector('strong')?.textContent || '').trim();
      const box = row.querySelector('input[type="checkbox"]');
      if (!box) return;
      const want = keep.includes(name);
      if (box.checked !== want) box.click();
      if (want) out.push(name);
    });
    return out;
  }, KEEP);
  console.log('Built-in chores kept:', kept.join(', '));

  // Day pickers (added in step 1c): pick a day where one is offered.
  const pickers = await page.locator('.chore-setup-overlay [data-field="day"]').count();
  console.log('Day pickers in the wizard:', pickers);
  for (const [name, value] of Object.entries(PICK)) {
    const select = page.locator(`.chore-setup-overlay [data-field="day"][data-chore="${name}"]`);
    if (await select.count()) { await select.selectOption(value); console.log(`Picked ${value} for ${name}`); }
  }

  // One custom chore: weekly, 20 minutes.
  await page.locator('.chore-custom-add-btn').click();
  const row = page.locator('.chore-custom-row').last();
  await row.locator('input.chore-custom-input').nth(0).fill('Clean the car e2e');
  await row.locator('input.chore-custom-input').nth(1).fill('Inside and out');
  await row.locator('select.chore-custom-select').first().selectOption('weekly');
  await row.locator('input[type="number"]').fill('20');
  await page.screenshot({ path: SHOTS + '/chore_setup_filled.png', fullPage: false });

  await page.locator('.chore-setup-actions button.primary').click();
  let status = '';
  for (let i = 0; i < 240; i++) {
    status = (await page.locator('.chore-setup-status').innerText()).trim();
    if (/^Created|failed|Failed|Could not/i.test(status) && !/^Creating/.test(status)) break;
    await page.waitForTimeout(500);
  }
  console.log('Wizard says:', status || '(nothing)');
  await page.screenshot({ path: SHOTS + '/chore_setup_done.png', fullPage: false });
  console.log('Errors:', errors.length ? errors : 'none');
  await browser.close();
})().catch(e => { console.error('SCRIPT FAILED:', e.message); process.exit(1); });
