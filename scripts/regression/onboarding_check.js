// Walk the dashboard's onboarding wizard to the end in a real (headless) Chrome
// against a throwaway copy (tracker issue 32). Types a nickname with the
// keyboard, goes through every step, and on "Your Day" opens Life Setup from
// inside onboarding, saves a day template the way the Day Builder does, closes
// Life Setup and checks that onboarding noticed. Prints every step's text and,
// at the end, what is really on disk (through the server's API), because the
// dashboard can report success for a command that failed (issue 23).
// Usage: NODE_PATH=<scratch>/node_modules node onboarding_check.js <base url> <screenshot dir>
const { chromium } = require('playwright-core');
const BASE = process.argv[2];
const SHOTS = process.argv[3];
const NICK = 'Rosa';

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
  await page.evaluate(() => document.querySelectorAll('.alpha-launch-overlay, .ycheck-overlay, [class*="popup"][class*="overlay"]').forEach(el => el.remove()));
  await page.evaluate(async () => {
    const m = await import('/wizards/onboarding/index.js');
    await m.launch({ bus: window.ChronosBus }, {});
  });
  await page.waitForTimeout(800);

  const ob = page.locator('.onboarding-overlay');
  const stepText = async () => (await ob.locator('.onboarding-body').innerText()).replace(/\s+\n/g, '\n').trim();
  const progress = async () => (await ob.locator('.onboarding-progress').innerText()).trim();
  const statusLine = async () => (await ob.locator('.wizard-status-line').innerText()).trim();
  const next = async () => { await ob.locator('.onboarding-bottom-nav button.primary').click(); await page.waitForTimeout(900); };
  const shot = async (name) => { if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}.png` }); };

  // 1. Welcome: type the nickname for real (select all, then type).
  console.log('==', await progress());
  const nick = ob.locator('.onboarding-body input').first();
  await nick.click();
  await page.keyboard.press('Control+A');
  await page.keyboard.type(NICK, { delay: 30 });
  await shot('1_welcome');
  await next();
  console.log('   status line:', await statusLine());

  for (let guard = 0; guard < 10; guard++) {
    const p = await progress();
    console.log('\n==', p);
    console.log(await stepText());
    await shot(p.replace(/[^A-Za-z0-9]+/g, '_'));
    if (/Your Day/i.test(p)) {
      const open = ob.locator('button', { hasText: /Life Setup/ }).first();
      if (await open.count()) {
        const before = await page.locator('.chronos-wizard-overlay').count();
        await open.click();
        await page.waitForTimeout(1500);
        const after = await page.locator('.chronos-wizard-overlay').count();
        console.log(`   pressed "${(await open.innerText()).trim()}": wizard overlays ${before} -> ${after}`);
        // Save a day template the way the Day Builder does, then close Life Setup.
        await page.evaluate(async () => {
          const post = (p, b) => fetch(p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) });
          await post('/api/template', { type: 'day', name: 'Test Day', children: [{ type: 'timeblock', name: 'Core Sleep', ideal_start_time: '23:30', duration: 480, anchored: true, reschedule: 'never' }] });
        });
        await page.evaluate(() => {
          const all = [...document.querySelectorAll('.chronos-wizard-overlay')];
          all.filter(el => !el.classList.contains('onboarding-overlay')).forEach(el => el.remove());
        });
        await page.waitForTimeout(1500);
        console.log('   after closing Life Setup, the step says:\n' + (await stepText()));
      } else {
        console.log('   (no Life Setup button on this step)');
      }
    }
    if (/Goals/i.test(p)) {
      const gp = ob.locator('button', { hasText: /Goal Planning/ }).first();
      console.log('   Goal Planning button:', (await gp.count()) ? 'yes' : 'no');
    }
    if (/All set/i.test(p)) break;
    await next();
    const sl = await statusLine();
    if (sl) console.log('   status line after Next:', sl);
  }
  await next(); // Finish
  console.log('\nonboarding closed:', (await ob.count()) === 0);

  const api = async (p) => page.evaluate(async (path) => (await fetch(path)).json(), p);
  const prof = await api('/api/profile');
  console.log('ON DISK nickname:', prof?.profile?.nickname);
  console.log('ON DISK day templates:', JSON.stringify((await api('/api/template/list?type=day')).templates));
  for (const t of ['routine', 'habit', 'goal', 'commitment', 'reward', 'achievement']) {
    const items = ((await api(`/api/items?type=${t}`)).items || []).map(i => i.name);
    if (items.length) console.log(`ON DISK ${t}s:`, JSON.stringify(items));
  }
  console.log('page errors:', errors.length ? '\n  ' + errors.join('\n  ') : 'none');
  await browser.close();
})().catch(e => { console.error('CHECK FAILED:', e); process.exit(1); });
