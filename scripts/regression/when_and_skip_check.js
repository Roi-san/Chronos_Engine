// Decisions D8 and D9 (2026-11-19) in a real (headless) Chrome against a
// throwaway copy: Home's capture box writes How often and When; the Routine
// Builder saves, reloads and clears How often and When; a plan places "before
// bed" items last; "Skip this week" on a weekly item records `skip: period` and
// the next plan leaves the item out and says so. Every step prints what is on
// disk (through the server's API), not only what the page says (issue 23).
// Needs a day template in the export (the plan runs at the real clock).
// Usage: NODE_PATH=<scratch>/node_modules node when_and_skip_check.js <base url> <screenshot dir>
const { chromium } = require('playwright-core');
const BASE = process.argv[2];
const SHOTS = process.argv[3];

(async () => {
  for (let i = 0; i < 60; i++) {
    try { const r = await fetch(BASE + '/health'); if (r.ok) break; } catch (e) {}
    await new Promise(res => setTimeout(res, 500));
  }
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' && !/404/.test(m.text())) errors.push('console: ' + m.text().slice(0, 200)); });
  page.on('dialog', d => d.accept().catch(() => {}));
  const home = async () => {
    await page.goto(BASE + '/dashboard.html', { waitUntil: 'domcontentloaded' });
    const enter = page.locator('button', { hasText: /^\s*Enter\s*$/i }).first();
    if (await enter.count()) await enter.click().catch(() => {});
    await page.waitForTimeout(2500);
    await page.evaluate(() => document.querySelectorAll('.alpha-launch-overlay, .ycheck-overlay, [class*="popup"][class*="overlay"]').forEach(el => el.remove()));
  };
  const api = (path, body) => page.evaluate(async ([p, b]) => {
    const r = await fetch(p, b ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) } : {});
    const text = await r.text();
    try { return JSON.parse(text); } catch { return text; }
  }, [path, body]);
  const onDisk = async (type, name, keys) => {
    const r = await api(`/api/item?type=${type}&name=${encodeURIComponent(name)}`);
    const item = (r && r.item) || {};
    return keys.map(k => `${k}=${JSON.stringify(item[k] === undefined ? '(absent)' : item[k])}`).join(' ');
  };

  await home();
  // ---------------------------------------------------------------- capture
  const capture = async (name, type, o) => {
    const form = page.locator('form.home-capture');
    await form.locator('[name=type]').selectOption(type);
    await form.locator('[name=name]').fill(name);
    if (o.duration) await form.locator('[name=duration]').selectOption(String(o.duration));
    if (o.frequency) await form.locator('[name=frequency]').selectOption(o.frequency);
    if (o.when) await form.locator('[name=when]').selectOption(o.when);
    if (o.at) await form.locator('[name=at_time]').fill(o.at);
    await form.locator('button[type=submit]').click();
    await page.waitForTimeout(3000);
  };
  await capture('Read in bed', 'habit', { duration: 30, frequency: 'daily', when: 'before bed' });
  console.log('Home capture, habit, daily, before bed:', await onDisk('habit', 'Read in bed', ['frequency', 'when', 'start_time', 'duration']));
  await capture('Gym session', 'habit', { duration: 45, frequency: 'none' });
  console.log('Home capture, habit, only when asked:  ', await onDisk('habit', 'Gym session', ['frequency', 'when']));
  await capture('Call mum', 'task', { duration: 15, when: 'at', at: '19:30' });
  console.log('Home capture, task, at 19:30:          ', await onDisk('task', 'Call mum', ['start_time', 'when']));

  // ---------------------------------------------------------------- Routine Builder
  await api('/api/template', { type: 'routine', name: 'Bedtime Routine', children: [
    { type: 'habit', name: 'Brush teeth', duration: 5 }, { type: 'habit', name: 'Read a book', duration: 20 }] });
  await api('/api/item', { type: 'routine', name: 'Bedtime Routine', properties: { category: 'sleep' } });
  await page.evaluate(async () => {
    const host = document.createElement('div');
    host.id = 'rb-host';
    host.style.cssText = 'position:fixed;inset:40px;z-index:5000;background:#111;overflow:auto';
    document.body.appendChild(host);
    const m = await import('/views/routine_builder/index.js');
    await m.mount(host, { bus: window.ChronosBus });
  });
  await page.waitForTimeout(1500);
  const rb = page.locator('#rb-host');
  const load = async () => { await rb.locator('#tName').selectOption('Bedtime Routine'); await rb.locator('#tLoad').click(); await page.waitForTimeout(1200); };
  const save = async () => { await rb.locator('#tSave').click(); await page.waitForTimeout(2500); };
  const fields = async () => `How often="${await rb.locator('#pFreq').inputValue()}" When="${await rb.locator('#pWhen').inputValue()}" At="${await rb.locator('#pAt').inputValue()}"`;
  await rb.locator('#tRefresh').click(); await page.waitForTimeout(800);
  await load();
  await rb.locator('#pFreq').selectOption('daily');
  await rb.locator('#pWhen').selectOption('before bed');
  await save();
  console.log('Routine Builder save daily + before bed:', await onDisk('routine', 'Bedtime Routine', ['frequency', 'when', 'start_time', 'category']));
  await load();
  console.log('Routine Builder fields after reload:     ', await fields());
  await rb.locator('#pFreq').selectOption('');
  await rb.locator('#pWhen').selectOption('');
  await save();
  console.log('Routine Builder save cleared:           ', await onDisk('routine', 'Bedtime Routine', ['frequency', 'when', 'start_time']));
  await rb.locator('#pFreq').selectOption('daily');
  await rb.locator('#pWhen').selectOption('before bed');
  await save();
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/routine_builder.png` });
  console.log('Routine Builder save again:             ', await onDisk('routine', 'Bedtime Routine', ['frequency', 'when']));
  await page.evaluate(() => document.getElementById('rb-host')?.remove());   // the builder covered Home

  // ---------------------------------------------------------------- plan, then Skip this week
  // Laundry gets an early wish so it is the first block, where Home shows "Skip this week".
  await api('/api/item', { type: 'habit', name: 'Laundry', properties: { frequency: 'weekly', duration: '20m', created: '2026-01-01', when: 'morning' } });
  await capture('Next habit after a timed one', 'habit', { duration: 15 });
  console.log('Home capture right after one with When: ', await onDisk('habit', 'Next habit after a timed one', ['frequency', 'when', 'start_time']));
  const planned = await api('/api/cli', { command: 'today', args: ['reschedule'], properties: {} });
  // /api/cli answers in YAML: take the plan's lines ("00:05 - 01:05: Laundry ...") from the raw text.
  const planLines = (raw) => (String(typeof raw === 'string' ? raw : JSON.stringify(raw)).match(/\d\d:\d\d - \d\d:\d\d: [^'\n\\]+/g) || []).join(' | ');
  console.log('Plan:', planLines(planned));
  await home();
  const now = async () => page.evaluate(() => {
    const card = Array.from(document.querySelectorAll('.home-card')).find(c => /Right now/i.test(c.textContent));
    const name = card && card.querySelector('.home-now-name');
    return { name: name ? name.textContent : null, buttons: card ? Array.from(card.querySelectorAll('button')).map(b => b.textContent.trim()) : [] };
  });
  const notes = async () => page.evaluate(() => Array.from(document.querySelectorAll('.home-day-template, .home-plan-note')).map(e => e.textContent));
  let current = await now();
  console.log('Right now:', JSON.stringify(current));
  // Work through the day as a user would until Laundry is "Right now" (the button
  // is on the current block only).
  for (let i = 0; i < 4 && current.name && current.name !== 'Laundry'; i++) {
    await page.locator('.home-card button', { hasText: /^Done$/ }).first().click();
    await page.waitForTimeout(3000);
    await home();
    current = await now();
    console.log('  after Done, right now:', JSON.stringify(current));
  }
  console.log('Home notes:', JSON.stringify(await notes()));
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/home_before_skip.png` });
  const skipThisWeek = page.locator('.home-card button', { hasText: /^Skip this week$/ }).first();
  if (await skipThisWeek.count()) {
    await skipThisWeek.click();
    await page.waitForTimeout(3000);
    const log = await api('/api/cli', { command: 'today', args: ['reschedule'], properties: {} });
    await home();
    current = await now();
    console.log('After Skip this week and a re-plan, right now:', JSON.stringify(current));
    console.log('Plan:', planLines(log));
    console.log('Home notes:', JSON.stringify(await notes()));
    if (SHOTS) await page.screenshot({ path: `${SHOTS}/home_after_skip.png` });
  } else {
    console.log('NO "Skip this week" button on the current block');
  }
  console.log('page errors:', errors.length ? '\n  ' + errors.join('\n  ') : 'none');
  await browser.close();
})().catch(e => { console.error('CHECK FAILED:', e); process.exit(1); });
