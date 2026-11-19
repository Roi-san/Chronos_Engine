// Home view: the pilot's landing page.
//
// It answers four questions on one screen and hands off to the existing
// wizards, builders and widgets for everything else:
//   1. What should I be doing right now?        (Now + Today)
//   2. How am I, so Chronos can adapt?           (Status)
//   3. What does my life contain?                (Life map)
//   4. What is still missing for Chronos to run? (Setup path)
//
// Home never writes files itself. It reads `/api/home/summary` and performs
// every change through the same endpoints the rest of the dashboard uses.

const STYLE_ID = 'chronos-home-view-style';
const SETUP_COLLAPSED_KEY = 'chronos_home_setup_collapsed_v1';
const STATUS_EXPANDED_KEY = 'chronos_home_status_expanded_v1';
const PRIMARY_STATUS = ['health', 'energy', 'place'];

function apiBase() {
  const o = window.location.origin;
  if (!o || o === 'null' || o.startsWith('file:')) return 'http://127.0.0.1:7357';
  return o;
}

async function getJSON(path) {
  const resp = await fetch(apiBase() + path);
  return resp.json();
}

async function postJSON(path, body) {
  const resp = await fetch(apiBase() + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await resp.json().catch(() => ({}));
  return { ok: resp.ok && data.ok !== false, data };
}

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  Object.entries(attrs || {}).forEach(([key, value]) => {
    if (value === null || value === undefined || value === false) return;
    if (key === 'class') el.className = value;
    else if (key === 'text') el.textContent = value;
    else if (key.startsWith('on') && typeof value === 'function') el.addEventListener(key.slice(2), value);
    else el.setAttribute(key, value === true ? '' : String(value));
  });
  children.flat().forEach((child) => {
    if (child === null || child === undefined || child === false) return;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  });
  return el;
}

function injectStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = `
    .home-shell { height:100%; overflow:auto; padding:22px 26px 90px; box-sizing:border-box; color:var(--chronos-text, #e8edf7); font-family:var(--font-stack-base); }
    .home-wrap { max-width:1280px; margin:0 auto; display:flex; flex-direction:column; gap:18px; }
    .home-hero { display:flex; align-items:flex-end; justify-content:space-between; gap:16px; flex-wrap:wrap; }
    .home-hello { font-size:26px; font-weight:800; margin:0; letter-spacing:0.01em; }
    .home-sub { margin:4px 0 0; color:var(--chronos-text-muted, #9ca7bd); font-size:13px; }
    .home-hero-actions { display:flex; gap:8px; flex-wrap:wrap; }
    .home-card { border:1px solid var(--chronos-border, rgba(255,255,255,0.1)); border-radius:16px; background:var(--chronos-surface, rgba(21,25,35,0.9)); padding:16px 18px; min-width:0; }
    .home-card-title { display:flex; align-items:center; justify-content:space-between; gap:10px; margin:0 0 10px; font-size:11px; letter-spacing:0.12em; text-transform:uppercase; color:var(--chronos-text-muted, #9ca7bd); font-weight:700; }
    .home-grid-top { display:grid; grid-template-columns:minmax(0,1.25fr) minmax(0,1fr); gap:18px; align-items:start; }
    .home-col { display:flex; flex-direction:column; gap:18px; min-width:0; }
    @media (max-width: 980px) { .home-grid-top { grid-template-columns:1fr; } }

    .home-btn { font:inherit; font-size:13px; color:var(--chronos-text, #e8edf7); background:var(--chronos-surface-soft, rgba(255,255,255,0.05)); border:1px solid var(--chronos-border, rgba(255,255,255,0.12)); border-radius:10px; padding:8px 12px; cursor:pointer; }
    .home-btn:hover { border-color:var(--chronos-border-strong, rgba(255,255,255,0.28)); background:var(--chronos-surface-highlight, rgba(255,255,255,0.09)); }
    .home-btn:disabled { opacity:0.5; cursor:default; }
    .home-btn.primary { background:var(--chronos-accent-gradient, #3d6fe0); border-color:var(--chronos-accent-strong, #5b8cff); font-weight:700; }
    .home-btn.big { padding:12px 18px; font-size:15px; }
    .home-btn.ghost { background:transparent; }
    .home-btn.small { padding:5px 9px; font-size:12px; }
    .home-link { background:none; border:none; padding:0; font:inherit; font-size:12px; color:var(--chronos-accent, #7aa2f7); cursor:pointer; text-decoration:underline; text-underline-offset:3px; }

    .home-now-name { font-size:24px; font-weight:800; margin:2px 0 4px; overflow-wrap:anywhere; }
    .home-now-meta { color:var(--chronos-text-muted, #9ca7bd); font-size:13px; }
    .home-now-label { font-size:11px; letter-spacing:0.12em; text-transform:uppercase; color:var(--chronos-accent, #7aa2f7); font-weight:700; }
    .home-progress { height:6px; border-radius:99px; background:rgba(255,255,255,0.08); overflow:hidden; margin:12px 0; }
    .home-progress > i { display:block; height:100%; background:var(--chronos-accent, #7aa2f7); }
    .home-now-actions { display:flex; gap:8px; flex-wrap:wrap; margin-top:12px; }
    .home-empty { color:var(--chronos-text-muted, #9ca7bd); font-size:13px; line-height:1.55; margin:0 0 12px; }
    .home-empty strong { color:var(--chronos-text, #e8edf7); }

    .home-day { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:2px; max-height:340px; overflow:auto; }
    .home-day li { display:grid; grid-template-columns:92px 1fr auto; gap:10px; align-items:center; padding:7px 8px; border-radius:9px; font-size:13px; }
    .home-day li.group { font-size:11px; letter-spacing:0.08em; text-transform:uppercase; color:var(--chronos-text-muted, #9ca7bd); padding-top:10px; padding-bottom:2px; }
    .home-day li.current { background:var(--chronos-accent-soft, rgba(122,162,247,0.14)); }
    .home-day li.past { opacity:0.55; }
    .home-day li.done .home-day-name { text-decoration:line-through; opacity:0.7; }
    .home-day-time { color:var(--chronos-text-muted, #9ca7bd); font-variant-numeric:tabular-nums; font-size:12px; white-space:nowrap; letter-spacing:0; }
    .home-day-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .home-tag { font-size:10px; letter-spacing:0.08em; text-transform:uppercase; padding:2px 7px; border-radius:99px; border:1px solid var(--chronos-border, rgba(255,255,255,0.14)); color:var(--chronos-text-muted, #9ca7bd); white-space:nowrap; }
    .home-tag.ok { color:var(--chronos-success, #5bdc82); border-color:var(--chronos-success, #5bdc82); }
    .home-tag.warn { color:var(--chronos-warning, #ffbe5c); border-color:var(--chronos-warning, #ffbe5c); }

    .home-status-row { display:grid; grid-template-columns:86px 1fr; gap:10px; align-items:start; margin-bottom:10px; }
    .home-status-name { font-size:12px; color:var(--chronos-text-muted, #9ca7bd); padding-top:6px; }
    .home-chips { display:flex; gap:6px; flex-wrap:wrap; }
    .home-chip { font:inherit; font-size:12px; color:var(--chronos-text, #e8edf7); background:transparent; border:1px solid var(--chronos-border, rgba(255,255,255,0.14)); border-radius:99px; padding:5px 11px; cursor:pointer; }
    .home-chip:hover { border-color:var(--chronos-border-strong, rgba(255,255,255,0.3)); }
    .home-chip[aria-pressed="true"] { background:var(--chronos-accent-soft, rgba(122,162,247,0.2)); border-color:var(--chronos-accent, #7aa2f7); font-weight:700; }
    .home-status-foot { display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap; margin-top:4px; }

    .home-capture { display:grid; grid-template-columns:1fr 150px 110px auto; gap:8px; }
    @media (max-width: 760px) { .home-capture { grid-template-columns:1fr 1fr; } }
    .home-input, .home-select { font:inherit; font-size:13px; color:var(--chronos-text, #e8edf7); background:rgba(0,0,0,0.25); border:1px solid var(--chronos-border, rgba(255,255,255,0.14)); border-radius:10px; padding:9px 11px; min-width:0; color-scheme:dark; }
    .home-input:focus, .home-select:focus { outline:none; border-color:var(--chronos-accent, #7aa2f7); }
    .home-select option { background:#121828; color:#e8edf7; }
    .home-capture-more { grid-column:1 / -1; display:flex; gap:10px; flex-wrap:wrap; }
    .home-capture-more label { display:flex; flex-direction:column; gap:4px; font-size:11px; color:var(--chronos-text-muted, #9ca7bd); min-width:120px; flex:1 1 140px; }
    .home-capture-more label[hidden] { display:none; }
    .home-why { margin:10px 0 0; padding:0; list-style:none; display:flex; flex-direction:column; gap:3px; font-size:12px; color:var(--chronos-warning, #ffbe5c); }
    .home-saved { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:8px; }
    .home-saved li { display:grid; grid-template-columns:1fr auto; gap:4px 10px; align-items:center; padding:8px 10px; border-radius:10px; background:var(--chronos-surface-soft, rgba(255,255,255,0.04)); }
    .home-saved-name { font-size:13px; font-weight:600; }
    .home-saved-why { grid-column:1 / 2; font-size:12px; color:var(--chronos-text-muted, #9ca7bd); line-height:1.45; }
    .home-saved li > button { grid-row:1 / span 2; grid-column:2; }
    .home-note { font-size:12px; color:var(--chronos-text-muted, #9ca7bd); margin:8px 0 0; min-height:16px; }
    .home-note.error { color:var(--chronos-danger, #ef6a6a); }
    .home-note.ok { color:var(--chronos-success, #5bdc82); }

    .home-life { display:grid; grid-template-columns:repeat(auto-fill, minmax(250px, 1fr)); gap:14px; }
    .home-area { border:1px solid var(--chronos-border, rgba(255,255,255,0.1)); border-radius:14px; background:var(--chronos-surface, rgba(21,25,35,0.9)); padding:14px 16px; display:flex; flex-direction:column; gap:8px; min-width:0; }
    .home-area-head { display:flex; align-items:baseline; justify-content:space-between; gap:8px; }
    .home-area-name { font-size:15px; font-weight:800; margin:0; }
    .home-area-count { font-size:20px; font-weight:800; color:var(--chronos-accent, #7aa2f7); font-variant-numeric:tabular-nums; }
    .home-area-count.zero { color:var(--chronos-text-muted, #9ca7bd); }
    .home-area-what { font-size:12px; color:var(--chronos-text-muted, #9ca7bd); margin:0; line-height:1.45; }
    .home-area-notice { color:var(--chronos-warning, #ffbe5c); }
    .home-area-list { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:3px; font-size:13px; }
    .home-area-list li { display:flex; justify-content:space-between; gap:8px; }
    .home-area-list span:first-child { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .home-area-list .dim { color:var(--chronos-text-muted, #9ca7bd); font-size:11px; white-space:nowrap; }
    .home-area-actions { display:flex; gap:6px; flex-wrap:wrap; margin-top:auto; padding-top:4px; }

    .home-steps { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:6px; }
    .home-step { display:grid; grid-template-columns:26px 1fr auto; gap:10px; align-items:center; padding:8px 10px; border-radius:10px; border:1px solid transparent; }
    .home-step.next { border-color:var(--chronos-accent, #7aa2f7); background:var(--chronos-accent-soft, rgba(122,162,247,0.1)); }
    .home-step-dot { width:22px; height:22px; border-radius:50%; border:2px solid var(--chronos-border-strong, rgba(255,255,255,0.3)); display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:800; }
    .home-step.done .home-step-dot { background:var(--chronos-success, #5bdc82); border-color:var(--chronos-success, #5bdc82); color:#08110b; }
    .home-step-title { font-size:14px; font-weight:700; }
    .home-step.done .home-step-title { font-weight:400; color:var(--chronos-text-muted, #9ca7bd); }
    .home-step-why { font-size:12px; color:var(--chronos-text-muted, #9ca7bd); margin-top:1px; }
    .home-foot { display:flex; gap:14px; flex-wrap:wrap; align-items:center; color:var(--chronos-text-muted, #9ca7bd); font-size:12px; }
  `;
  document.head.appendChild(style);
}

// ---- small pure helpers -----------------------------------------------------

function toMinutes(hm) {
  const m = /^(\d{1,2}):(\d{2})$/.exec(String(hm || ''));
  return m ? Number(m[1]) * 60 + Number(m[2]) : null;
}

function nowMinutes() {
  const d = new Date();
  return d.getHours() * 60 + d.getMinutes();
}

function greeting() {
  const hour = new Date().getHours();
  if (hour < 5) return 'Still up';
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

function fmtDuration(minutes) {
  const m = Math.max(0, Math.round(minutes));
  if (m < 60) return `${m} min`;
  const hrs = Math.floor(m / 60);
  const rest = m % 60;
  return rest ? `${hrs}h ${rest}m` : `${hrs}h`;
}

const DONE_STATES = new Set(['completed', 'done']);
const CLOSED_STATES = new Set(['completed', 'done', 'skipped', 'cancelled', 'missed']);

// Blocks a person acts on. Windows and gap fills are containers: the work is inside them.
function actionableBlocks(blocks) {
  return (blocks || []).filter((b) => !b.window && !b.container);
}

function findCurrent(blocks) {
  const now = nowMinutes();
  const open = actionableBlocks(blocks).filter((b) => !CLOSED_STATES.has(b.status));
  const running = open.filter((b) => toMinutes(b.start) <= now && now < toMinutes(b.end));
  if (running.length) {
    // The deepest block is the most concrete thing to do (a habit inside a routine).
    return { block: running.sort((a, b) => b.depth - a.depth)[0], running: true };
  }
  const upcoming = open.filter((b) => toMinutes(b.start) > now).sort((a, b) => toMinutes(a.start) - toMinutes(b.start));
  return { block: upcoming[0] || null, running: false };
}

// ---- the view ---------------------------------------------------------------

export function mount(el, context) {
  injectStyles();
  const bus = context?.bus || window.ChronosBus;
  const shell = h('div', { class: 'home-shell' });
  const wrap = h('div', { class: 'home-wrap' });
  shell.appendChild(wrap);
  el.appendChild(shell);

  const state = { summary: null, gate: null, busy: false, statusDirty: false, note: null, loadError: '' };
  let timer = null;
  let disposed = false;

  // -- alpha gate awareness: only offer surfaces the pilot can actually open --
  function gateBlocks(kind, ...names) {
    const snapshot = state.summary?.alpha_gate || {};
    if (String(snapshot.release_profile || '').toLowerCase() === 'full_dev') return false;
    if (!snapshot.disable_hidden_features) return false;
    const profile = state.gate?.profiles?.[snapshot.release_profile] || state.gate?.profiles?.alpha_v0_3;
    const hidden = (profile?.dashboard?.hidden?.[kind] || []).map((v) => String(v).toLowerCase());
    return names.some((n) => hidden.includes(String(n).toLowerCase()));
  }
  const canView = (name, label) => !gateBlocks('views', name, label || name, name.replace(/_/g, ' '), name.replace(/_/g, ''));
  const canWidget = (name) => !gateBlocks('widgets', name);
  const canWizard = (name) => !gateBlocks('wizards', name, name.replace(/_/g, ''));
  // Item types the active release profile refuses to create (the engine enforces this).
  const typeOff = (type) => (state.summary?.alpha_gate?.disabled_item_types || []).includes(type);

  const openView = (name, label) => { try { void window.ChronosOpenView?.(name, label || name); } catch { } };
  const openWidget = (name) => { try { bus?.emit?.('widget:show', name); } catch { } };
  const openWizard = (name) => { try { void window.ChronosLaunchWizard?.(name); } catch { } };
  const openItems = (type) => {
    try { localStorage.setItem('im_type', type); } catch { }
    openWidget('ItemManager');
  };

  async function load({ quiet = false } = {}) {
    try {
      const [summary, gate] = await Promise.all([
        getJSON('/api/home/summary'),
        state.gate ? Promise.resolve(state.gate) : fetch(new URL('../../config/alpha_gate_profiles.json', import.meta.url)).then((r) => r.json()).catch(() => null),
      ]);
      if (!summary?.ok) throw new Error(summary?.error || 'summary unavailable');
      state.summary = summary;
      state.gate = gate;
      state.loadError = '';
    } catch (err) {
      state.loadError = String(err?.message || err);
      if (quiet && state.summary) return;
    }
    if (!disposed) render();
  }

  async function act(label, fn) {
    if (state.busy) return;
    state.busy = true;
    state.note = { text: `${label}…`, tone: '' };
    render();
    try {
      const result = await fn();
      state.note = result?.note || null;
    } catch (err) {
      state.note = { text: `${label} failed: ${String(err?.message || err)}`, tone: 'error' };
    }
    state.busy = false;
    await load();
  }

  // -- actions ---------------------------------------------------------------
  const planDay = () => act('Planning your day', async () => {
    let ok = false;
    let detail = '';
    if (typeof window.ChronosRunCliCommand === 'function') {
      // Shared helper: it also handles the "you should be asleep" prompt.
      const result = await window.ChronosRunCliCommand({ command: 'today', args: ['reschedule'], properties: {} });
      ok = !!(result?.response?.ok && result?.data?.ok !== false);
      detail = result?.data?.stderr || result?.data?.error || '';
    } else {
      const result = await postJSON('/api/cli', { command: 'today', args: ['reschedule'], properties: {} });
      ok = result.ok;
      detail = result.data?.stderr || result.data?.error || '';
    }
    state.statusDirty = false;
    try { window.calendarLoadToday?.(true); } catch { }
    if (!ok) return { note: { text: `Chronos could not plan the day. ${String(detail).split('\n')[0]}`, tone: 'error' } };
    const fresh = await getJSON('/api/home/summary').catch(() => null);
    const count = actionableBlocks(fresh?.today?.blocks).length;
    if (!count) {
      return { note: { text: 'Chronos ran, but placed nothing on today. It places what your day template contains — open Day Builder and give blocks a start time, or add routines to the day.', tone: 'error' } };
    }
    return { note: { text: `Day planned: ${count} block${count === 1 ? '' : 's'}.`, tone: 'ok' } };
  });

  // `turnPeriod` set: "Skip this week" (D9): the turn is handled for the whole
  // period (mark ... skip:period); otherwise Skip means "not today".
  const markBlock = (block, status, turnPeriod = '') => act(status === 'completed' ? 'Marking done' : 'Skipping', async () => {
    const properties = turnPeriod ? { skip: 'period' } : {};
    const result = await postJSON('/api/cli', { command: 'mark', args: [`${block.name}:${status}`], properties });
    if (!result.ok) return { note: { text: `Could not update "${block.name}".`, tone: 'error' } };
    if (turnPeriod) return { note: { text: `Skipped for this ${turnPeriod}: ${block.name}. It is back next ${turnPeriod}.`, tone: 'ok' } };
    return { note: { text: status === 'completed' ? `Done: ${block.name}` : `Skipped: ${block.name}`, tone: 'ok' } };
  });

  // Saved for a better day -> Add back. `today inject "<name>" type:<type>` is a
  // soft injection: Kairos re-plans, places it where it fits (a fixed slot gets
  // its own time back), and status never removes something added by hand.
  // docs/scheduling/status_scale_down_design.md, step 3.
  const addBack = (row) => act(`Adding back ${row.name}`, async () => {
    const payload = { command: 'today', args: ['inject', row.name], properties: { type: row.type || 'task' } };
    let ok = false;
    let detail = '';
    if (typeof window.ChronosRunCliCommand === 'function') {
      const result = await window.ChronosRunCliCommand(payload);
      ok = !!(result?.response?.ok && result?.data?.ok !== false);
      detail = result?.data?.stderr || result?.data?.error || '';
    } else {
      const result = await postJSON('/api/cli', payload);
      ok = result.ok;
      detail = result.data?.stderr || result.data?.error || '';
    }
    try { window.calendarLoadToday?.(true); } catch { }
    if (!ok) return { note: { text: `Could not add back "${row.name}". ${String(detail).split('\n')[0]}`, tone: 'error' } };
    const fresh = await getJSON('/api/home/summary').catch(() => null);
    const placed = (fresh?.today?.blocks || []).find((b) => String(b.name).trim().toLowerCase() === row.name.trim().toLowerCase());
    if (!placed) return { note: { text: `Added back "${row.name}", but there was no free time left for it today.`, tone: 'error' } };
    return { note: { text: `Added back: ${row.name} at ${placed.start}.`, tone: 'ok' } };
  });

  const startDay = () => act('Starting the timer', async () => {
    if (typeof window.ChronosStartDay !== 'function') return { note: { text: 'Timer is not available.', tone: 'error' } };
    await window.ChronosStartDay({ source: 'home' });
    return { note: { text: 'Timer is running through your schedule.', tone: 'ok' } };
  });

  const setStatus = (dimension, value) => act(`Setting ${dimension.name.toLowerCase()}`, async () => {
    const result = await postJSON('/api/status/update', { [dimension.key]: value });
    if (!result.ok) return { note: { text: `Could not set ${dimension.name}.`, tone: 'error' } };
    state.statusDirty = true;
    return { note: { text: `${dimension.name}: ${value}. Re-plan to let Chronos adapt today.`, tone: 'ok' } };
  });

  const sickDay = () => act('Switching to a sick day', async () => {
    const dims = state.summary?.status?.dimensions || [];
    const pick = (key, wanted) => {
      const dim = dims.find((d) => d.key === key);
      const opt = dim?.options?.find((o) => wanted.includes(o.name.toLowerCase()));
      return dim && opt ? [dim.key, opt.name] : null;
    };
    const updates = Object.fromEntries([pick('health', ['poor']), pick('energy', ['low'])].filter(Boolean));
    if (!Object.keys(updates).length) return { note: { text: 'No health or energy status is configured.', tone: 'error' } };
    const result = await postJSON('/api/status/update', updates);
    if (!result.ok) return { note: { text: 'Could not switch to a sick day.', tone: 'error' } };
    state.statusDirty = true;
    return { note: { text: 'Sick day set (health: poor, energy: low). Re-plan to lighten today.', tone: 'ok' } };
  });

  const capture = (form) => {
    // Read the form now: act() re-renders, which replaces this form element.
    // "#word" anywhere in the text becomes a tag: "Call the bank #admin #quick".
    const raw = form.name.value;
    const tags = Array.from(raw.matchAll(/(?:^|\s)#([\p{L}\p{N}_-]+)/gu), (m) => m[1]);
    const name = raw.replace(/(?:^|\s)#[\p{L}\p{N}_-]+/gu, ' ').replace(/\s+/g, ' ').trim();
    const type = form.type.value;
    const minutes = form.duration.value;
    const extra = {
      goal: form.goal?.value || '',
      miniOf: form.mini_of?.value || '',
      due: form.due_date?.value || '',
      priority: form.priority?.value || '',
      times: Number(form.times?.value || 0),
      when: form.when?.value || '',
      atTime: form.at_time?.value || '',
      frequency: form.frequency?.value || '',
      period: form.period?.value || 'week',
      target: form.target?.value || '',
    };
    return act('Saving', async () => {
      if (!name) return { note: { text: 'Type what is on your mind first.', tone: 'error' } };
      if (type === 'commitment' && (!extra.target || extra.times < 1)) {
        return { note: { text: 'A commitment needs a number and the habit or task it counts, e.g. 3 per week of "Gym session".', tone: 'error' } };
      }
      const properties = {};
      // Without a duration the scheduler has nothing to place, so timed types always get one.
      if (['task', 'habit'].includes(type)) properties.duration = `${minutes}m`;
      if (tags.length) properties.tags = tags;
      // goal_defaults.yml is a blueprint with example milestones; a goal typed here is a real one.
      if (type === 'goal') {
        properties.is_template = false; properties.milestones = []; properties.status = 'active';
        if (extra.due) properties.due_date = extra.due;
        if (extra.priority) properties.priority = extra.priority;
      }
      // Links the scheduler reads (modules/scheduler/direction.py).
      if (['task', 'habit'].includes(type)) {
        if (extra.goal) properties.goal = extra.goal;
        if (extra.miniOf) properties.mini_of = extra.miniOf;
        // When (decisions D7, D8): a wish Kairos keeps when there is room.
        if (extra.when === 'at' && extra.atTime) properties.start_time = extra.atTime;
        else if (extra.when && extra.when !== 'at') properties.when = extra.when;
      }
      // How often (D2). Empty = no rhythm of its own: only a goal or commitment brings it in.
      if (type === 'habit' && extra.frequency) properties.frequency = extra.frequency === 'none' ? '' : extra.frequency;
      if (type === 'commitment') {
        const [targetType, ...rest] = extra.target.split(':');
        properties.status = 'active';
        properties.rule = { kind: 'frequency', times: extra.times, period: extra.period };
        properties.targets = [{ type: targetType, name: rest.join(':') }];
      }
      const result = await postJSON('/api/item', { type, name, properties });
      // The engine reports a gated type as a successful command whose output says "disabled".
      const refused = /disabled by the active alpha gate/i.test(String(result.data?.stdout || ''));
      if (!result.ok || refused) {
        const reason = refused ? `${type}s are switched off in this alpha release.` : String(result.data?.stderr || result.data?.error || '').split('\n')[0];
        return { note: { text: `Could not save "${name}". ${reason}`, tone: 'error' } };
      }
      state.clearDraft = true;
      return { note: { text: `Saved ${type}: ${name}${tags.length ? ` (tags: ${tags.join(', ')})` : ''}`, tone: 'ok' } };
    });
  };

  // The scheduler skips anything without a length, so offer a sane default in one click.
  const sizeItems = (type, names) => act('Setting durations', async () => {
    const resp = await fetch(`${apiBase()}/api/items/setprop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type, names, property: 'duration', value: '30m' }),
    });
    if (!resp.ok) return { note: { text: 'Could not set durations for every item.', tone: 'error' } };
    return { note: { text: `Gave ${names.length} ${type}${names.length === 1 ? '' : 's'} a 30 minute length. Adjust any of them in Manage.`, tone: 'ok' } };
  });

  const showEverything = () => act('Unlocking all features', async () => {
    const body = [
      `release_profile: ${state.summary?.alpha_gate?.release_profile || 'alpha_v0_3'}`,
      'show_hidden_items: true',
      'disable_hidden_features: false',
      `show_alpha_gate_toggle: ${state.summary?.alpha_gate?.show_alpha_gate_toggle ? 'true' : 'false'}`,
      '',
    ].join('\n');
    await fetch(`${apiBase()}/api/settings?file=alpha_gate_settings.yml`, { method: 'POST', headers: { 'Content-Type': 'text/yaml' }, body });
    window.setTimeout(() => window.location.reload(), 150);
    return { note: { text: 'Reloading with every feature visible…', tone: 'ok' } };
  });

  // -- sections --------------------------------------------------------------
  function renderHero(s) {
    const name = s.profile?.nickname && s.profile.nickname !== 'Pilot' ? `, ${s.profile.nickname}` : '';
    const blocks = actionableBlocks(s.today?.blocks);
    const done = blocks.filter((b) => DONE_STATES.has(b.status)).length;
    const dateText = new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' });
    const sub = s.today?.exists && blocks.length
      ? `${dateText} · ${done} of ${blocks.length} done today`
      : `${dateText} · today is not planned yet`;
    return h('div', { class: 'home-hero' },
      h('div', {},
        h('h1', { class: 'home-hello', text: `${greeting()}${name}` }),
        h('p', { class: 'home-sub', text: sub }),
      ),
      h('div', { class: 'home-hero-actions' },
        canWidget('NiaAssistant') && h('button', { class: 'home-btn', text: 'Talk to Nia', onclick: () => { openWidget('NiaAssistant'); try { bus?.emit?.('nia:open-chat'); } catch { } } }),
        h('button', { class: 'home-btn', text: 'Refresh', onclick: () => load() }),
      ),
    );
  }

  // Why Kairos put this block on today: commitment progress, the goal it serves,
  // and whether it is standing in for a bigger item.
  function blockReasons(s, block) {
    const key = String(block.name || '').trim().toLowerCase();
    const direction = s.direction || {};
    const reasons = [];
    const standsFor = (direction.scaled_down || {})[key];
    if (standsFor) {
      reasons.push(`Lighter version of "${standsFor}" for how you are today. It still counts.`);
      reasons.push(...(((direction.by_name || {})[standsFor.trim().toLowerCase()] || {}).reasons || []));
    }
    reasons.push(...(((direction.by_name || {})[key] || {}).reasons || []));
    // Kept on the plan although today's status falls short of what it needs.
    const kept = (s.today?.status_effects?.kept || {})[key];
    if (kept) reasons.push(kept);
    // Planned with an assumed length: the default, or a routine's steps added up.
    const lengthNote = (s.today?.length_notes?.notes || {})[key];
    if (lengthNote) reasons.push(lengthNote);
    return Array.from(new Set(reasons));
  }

  function renderNow(s) {
    const card = h('section', { class: 'home-card' }, h('h2', { class: 'home-card-title' }, 'Right now'));
    const blocks = actionableBlocks(s.today?.blocks);
    const hasSkeleton = (s.counts?.day || 0) > 0;

    if (!s.today?.exists || !blocks.length) {
      if (!hasSkeleton) {
        card.append(
          h('p', { class: 'home-empty' }, h('strong', {}, 'Chronos has no shape for your day yet. '),
            'Give it your fixed points once — sleep, work, meals — and it can start planning around them.'),
          h('div', { class: 'home-now-actions' },
            h('button', { class: 'home-btn primary big', text: 'Set up my day skeleton', onclick: () => openWizard('life_setup') }),
          ),
        );
      } else {
        card.append(
          h('p', { class: 'home-empty' }, h('strong', {}, 'Today is not planned yet. '),
            'Chronos will build today from your day template, routines and current status.'),
          h('div', { class: 'home-now-actions' },
            h('button', { class: 'home-btn primary big', text: 'Plan my day', disabled: state.busy, onclick: planDay }),
            h('button', { class: 'home-btn', text: 'Edit day template', onclick: () => openView('day_builder', 'Day Builder') }),
          ),
        );
      }
      return card;
    }

    const { block, running } = findCurrent(s.today.blocks);
    if (!block) {
      card.append(
        h('p', { class: 'home-empty' }, h('strong', {}, 'Nothing left on today. '), 'Everything scheduled has passed or is closed.'),
        h('div', { class: 'home-now-actions' },
          h('button', { class: 'home-btn', text: 'Re-plan from now', disabled: state.busy, onclick: planDay }),
        ),
      );
      return card;
    }

    const start = toMinutes(block.start);
    const end = toMinutes(block.end);
    const now = nowMinutes();
    card.append(
      h('div', { class: 'home-now-label', text: running ? 'Do this now' : `Next up in ${fmtDuration(start - now)}` }),
      h('div', { class: 'home-now-name', text: block.name }),
      h('div', { class: 'home-now-meta', text: running
        ? `${block.start} – ${block.end} · ${fmtDuration(end - now)} left`
        : `${block.start} – ${block.end} · ${fmtDuration(end - start)}` }),
    );
    const why = blockReasons(s, block);
    if (why.length) card.append(h('ul', { class: 'home-why' }, why.map((text) => h('li', { text }))));
    const turnPeriod = (s.today?.turn_periods || {})[String(block.name || '').trim().toLowerCase()] || '';
    if (running) {
      const pct = Math.min(100, Math.max(0, ((now - start) / Math.max(1, end - start)) * 100));
      card.append(h('div', { class: 'home-progress' }, h('i', { style: `width:${pct.toFixed(1)}%` })));
    }
    card.append(h('div', { class: 'home-now-actions' },
      h('button', { class: 'home-btn primary', text: 'Done', disabled: state.busy, onclick: () => markBlock(block, 'completed') }),
      h('button', { class: 'home-btn', text: 'Skip', title: 'Not today: it comes back tomorrow.', disabled: state.busy, onclick: () => markBlock(block, 'skipped') }),
      turnPeriod && h('button', {
        class: 'home-btn', text: `Skip this ${turnPeriod}`, disabled: state.busy,
        title: `Not this ${turnPeriod}: it comes back on its next turn, with no extra push. It does not count as done.`,
        onclick: () => markBlock(block, 'skipped', turnPeriod),
      }),
      canWidget('Timer') && h('button', { class: 'home-btn', text: 'Start timer', disabled: state.busy, onclick: startDay }),
      h('button', { class: 'home-btn ghost', text: 'Re-plan from now', disabled: state.busy, onclick: planDay }),
    ));
    return card;
  }

  function renderDay(s) {
    if (!s.today?.exists || !actionableBlocks(s.today?.blocks).length) return null;
    const now = nowMinutes();
    const current = findCurrent(s.today.blocks);
    const list = h('ul', { class: 'home-day' });
    // Named windows show as a heading above their contents; anonymous gap fills do not.
    const blocks = (s.today.blocks || []).filter((b) => !(b.container || b.window) || b.kind !== 'gap_fill');
    blocks.forEach((b) => {
      if (b.container || b.window) {
        list.appendChild(h('li', { class: 'group' },
          h('span', { class: 'home-day-time', text: `${b.start} – ${b.end}` }),
          h('span', { class: 'home-day-name', title: b.name, text: b.name }),
          h('span'),
        ));
        return;
      }
      const isCurrent = current.running && current.block === b;
      const past = toMinutes(b.end) <= now;
      const done = DONE_STATES.has(b.status);
      let tag = null;
      if (done) tag = h('span', { class: 'home-tag ok', text: 'done' });
      else if (b.status) tag = h('span', { class: 'home-tag', text: b.status });
      else if (past) tag = h('span', { class: 'home-tag warn', text: 'not marked' });
      else if (b.anchored) tag = h('span', { class: 'home-tag', text: 'fixed' });
      else {
        // A lighter version carries the pressure of the item it stands in for.
        const ownKey = String(b.name).trim().toLowerCase();
        const pushKey = String((s.direction?.scaled_down || {})[ownKey] || ownKey).trim().toLowerCase();
        const pushState = ((s.direction?.by_name || {})[pushKey] || {}).state;
        if (['last_chance', 'behind'].includes(pushState)) tag = h('span', { class: 'home-tag warn', text: 'last chance' });
        else if (pushState === 'at_risk') tag = h('span', { class: 'home-tag warn', text: 'at risk' });
        // Kept although today's status falls short of it (the sentence is in the tooltip).
        const kept = (s.today?.status_effects?.kept || {})[ownKey];
        if (!tag && kept) tag = h('span', { class: 'home-tag', title: kept, text: 'tough today' });
        // Planned with the default length because it has none (the sentence is in the tooltip).
        if (!tag && (s.today?.length_notes?.unset || []).includes(ownKey)) {
          tag = h('span', { class: 'home-tag', title: (s.today?.length_notes?.notes || {})[ownKey] || '', text: 'no length' });
        }
      }
      list.appendChild(h('li', { class: [isCurrent ? 'current' : '', past && !isCurrent ? 'past' : '', done ? 'done' : ''].join(' ').trim() },
        h('span', { class: 'home-day-time', text: `${b.start} – ${b.end}` }),
        h('span', { class: 'home-day-name', title: [b.name, ...blockReasons(s, b)].join('\n'), style: `padding-left:${b.group ? 14 : 0}px`, text: b.name }),
        tag || h('span'),
      ));
    });
    // Which day template Kairos used and why (D6), and anything it did that would
    // otherwise be silent (sleep found by name, files it could not read).
    const tpl = s.today?.day_template;
    const notes = s.today?.plan_notes || [];
    return h('section', { class: 'home-card' },
      h('h2', { class: 'home-card-title' }, 'Today',
        h('button', { class: 'home-link', text: 'Open full schedule', onclick: () => openView('schedule', 'Schedule') })),
      tpl && tpl.name && h('p', { class: 'home-sub home-day-template', text: `Day template: ${tpl.name} (${tpl.why}).` }),
      ...notes.map((text) => h('p', { class: 'home-note home-plan-note', text })),
      list,
    );
  }

  // What today's status left out, with a way to have it anyway. Nothing is
  // dropped silently: the pilot sees it and decides.
  function renderSaved(s) {
    const rows = s.today?.exists ? (s.today?.status_effects?.saved || []) : [];
    if (!rows.length) return null;
    return h('section', { class: 'home-card' },
      h('h2', { class: 'home-card-title' }, 'Saved for a better day'),
      h('p', { class: 'home-empty', text: 'Left out of today because of how you are. Add one back if you want it anyway.' }),
      h('ul', { class: 'home-saved' }, rows.map((row) => h('li', {},
        h('span', { class: 'home-saved-name', text: row.fixed_slot ? `${row.name} · ${row.fixed_slot.replace('-', ' – ')}` : row.name }),
        h('button', { class: 'home-btn small', text: 'Add back', disabled: state.busy, title: `Runs: today inject "${row.name}" type:${row.type}`, onclick: () => addBack(row) }),
        h('span', { class: 'home-saved-why', text: row.text }),
      ))),
    );
  }

  function renderStatus(s) {
    const dims = s.status?.dimensions || [];
    if (!dims.length) return null;
    let expanded = false;
    try { expanded = localStorage.getItem(STATUS_EXPANDED_KEY) === 'true'; } catch { }
    const primary = dims.filter((d) => PRIMARY_STATUS.includes(d.key));
    const shown = expanded || !primary.length ? dims : primary;
    const card = h('section', { class: 'home-card' },
      h('h2', { class: 'home-card-title' }, 'How are you right now?',
        h('button', { class: 'home-link', text: 'Sick day', title: 'Sets health to poor and energy to low', onclick: sickDay })),
    );
    shown.forEach((dim) => {
      card.appendChild(h('div', { class: 'home-status-row' },
        h('div', { class: 'home-status-name', title: dim.description, text: dim.name }),
        h('div', { class: 'home-chips' }, dim.options.map((opt) => h('button', {
          class: 'home-chip',
          'aria-pressed': String(String(dim.current).toLowerCase() === opt.name.toLowerCase()),
          title: opt.description,
          text: opt.name,
          disabled: state.busy,
          onclick: () => setStatus(dim, opt.name),
        }))),
      ));
    });
    card.appendChild(h('div', { class: 'home-status-foot' },
      dims.length > primary.length && primary.length
        ? h('button', { class: 'home-link', text: expanded ? 'Show less' : `Show ${dims.length - primary.length} more`, onclick: () => {
          try { localStorage.setItem(STATUS_EXPANDED_KEY, String(!expanded)); } catch { }
          render();
        } })
        : h('span'),
      state.statusDirty && (s.counts?.day || 0) > 0
        ? h('button', { class: 'home-btn primary small', text: 'Re-plan my day with this', disabled: state.busy, onclick: planDay })
        : h('span', { class: 'home-note', style: 'margin:0', text: 'Chronos uses this to choose what fits you today.' }),
    ));
    return card;
  }

  // Show only the detail fields that apply to the chosen kind.
  function syncCaptureFields(form) {
    const type = form.type.value;
    form.duration.disabled = !['task', 'habit'].includes(type);
    form.querySelectorAll('.home-capture-more label').forEach((label) => {
      label.hidden = !(label.getAttribute('data-for') || '').split(' ').includes(type);
    });
    // The clock field only for "At a time…".
    const at = form.querySelector('[data-when="at"]');
    if (at && form.when?.value !== 'at') at.hidden = true;
  }

  function renderCapture(s) {
    const life = s?.life || {};
    const goals = (life.goal || []).filter((g) => !CLOSED_STATES.has(String(g.status || '').toLowerCase()));
    const doable = [...(life.habit || []), ...(life.task || []), ...(life.routine || [])]
      .filter((d) => !CLOSED_STATES.has(String(d.status || '').toLowerCase()));
    const form = h('form', { class: 'home-capture', onsubmit: (ev) => { ev.preventDefault(); capture(form); } },
      h('input', { class: 'home-input', name: 'name', placeholder: 'What is on your mind? Add #tags if you like…', autocomplete: 'off', 'aria-label': 'What is on your mind' }),
      h('select', { class: 'home-select', name: 'type', 'aria-label': 'Kind', onchange: () => syncCaptureFields(form) },
        [['task', 'Task'], ['habit', 'Habit'], ['goal', 'Goal'], ['commitment', 'Commitment'], ['project', 'Project'], ['note', 'Note']]
          .filter(([value]) => !typeOff(value))
          .map(([value, label]) => h('option', { value, text: label }))),
      h('select', { class: 'home-select', name: 'duration', 'aria-label': 'How long' },
        [[5, '5 min'], [15, '15 min'], [30, '30 min'], [45, '45 min'], [60, '1 hour'], [90, '1.5 hours'], [120, '2 hours']]
          .map(([value, label]) => h('option', { value, text: label, selected: value === 30 }))),
      h('button', { class: 'home-btn primary', type: 'submit', text: 'Add', disabled: state.busy }),
      // Optional details, shown per kind. These are the links the scheduler acts on.
      h('div', { class: 'home-capture-more' },
        h('label', { 'data-for': 'task habit' }, 'For goal',
          h('select', { class: 'home-select', name: 'goal' }, h('option', { value: '', text: '(none)' }),
            goals.map((g) => h('option', { value: g.name, text: g.name })))),
        h('label', { 'data-for': 'task habit', title: 'On a day when the full version does not fit your energy or health, Chronos schedules this one instead, and it still counts.' }, 'Lighter version of',
          h('select', { class: 'home-select', name: 'mini_of' }, h('option', { value: '', text: '(none)' }),
            doable.map((d) => h('option', { value: d.name, text: d.name })))),
        h('label', { 'data-for': 'habit', title: 'How often it comes back on its own. Once a week or less often: it shows up until done, spread over the period.' }, 'How often',
          h('select', { class: 'home-select', name: 'frequency' },
            [['daily', 'Every day'], ['weekly', 'Once a week'], ['monthly', 'Once a month'], ['quarterly', 'Once a quarter'], ['yearly', 'Once a year'], ['none', 'Only when a goal or commitment asks']]
              .map(([value, label]) => h('option', { value, text: label, selected: value === 'daily' })))),
        h('label', { 'data-for': 'task habit', title: 'A wish: Chronos keeps it when there is room, otherwise it plans it in free time and says why.' }, 'When',
          h('select', { class: 'home-select', name: 'when', onchange: () => syncCaptureFields(form) },
            [['', 'Any time'], ['morning', 'Morning'], ['afternoon', 'Afternoon'], ['evening', 'Evening'], ['before bed', 'Before bed'], ['at', 'At a time…']]
              .map(([value, label]) => h('option', { value, text: label })))),
        h('label', { 'data-for': 'task habit', 'data-when': 'at' }, 'At',
          h('input', { class: 'home-input', type: 'time', name: 'at_time' })),
        h('label', { 'data-for': 'goal' }, 'Target date',
          h('input', { class: 'home-input', type: 'date', name: 'due_date' })),
        h('label', { 'data-for': 'goal' }, 'Priority',
          h('select', { class: 'home-select', name: 'priority' },
            [['', '(none)'], ['high', 'High'], ['medium', 'Medium'], ['low', 'Low']].map(([value, label]) => h('option', { value, text: label })))),
        h('label', { 'data-for': 'commitment' }, 'How often',
          h('input', { class: 'home-input', type: 'number', name: 'times', min: '1', max: '31', value: '3' })),
        h('label', { 'data-for': 'commitment' }, 'Per',
          h('select', { class: 'home-select', name: 'period' },
            [['day', 'day'], ['week', 'week'], ['month', 'month']].map(([value, label]) => h('option', { value, text: label, selected: value === 'week' })))),
        h('label', { 'data-for': 'commitment' }, 'Of',
          h('select', { class: 'home-select', name: 'target' }, h('option', { value: '', text: doable.length ? 'choose…' : 'add a habit or task first' }),
            doable.map((d) => h('option', { value: `${d.type}:${d.name}`, text: `${d.name} (${d.type})` })))),
      ),
    );
    syncCaptureFields(form);
    return h('section', { class: 'home-card' },
      h('h2', { class: 'home-card-title' }, 'Get it out of your head',
        canWizard('brain_dump') && h('button', { class: 'home-link', text: 'Brain dump many at once', onclick: () => openWizard('brain_dump') })),
      form,
      h('p', { class: `home-note ${state.note?.tone || ''}`, role: 'status', text: state.note?.text || '' }),
    );
  }

  function areaDefinitions(s) {
    const life = s.life || {};
    const meta = (item) => (Array.isArray(item.tags) && item.tags.length
      ? item.tags.map((t) => `#${t}`).join(' ')
      : item.due_date || item.deadline || item.frequency || item.duration || item.status || '');
    const goalInfo = Object.fromEntries((s.direction?.goals || []).map((g) => [String(g.name).toLowerCase(), g]));
    const commitmentInfo = Object.fromEntries((s.direction?.commitments || []).map((c) => [String(c.name).toLowerCase(), c]));
    const goalMeta = (item) => {
      const info = goalInfo[String(item.name).toLowerCase()];
      if (!info) return meta(item);
      const when = info.days_left === null || info.days_left === undefined ? 'no date'
        : info.days_left < 0 ? `${-info.days_left}d overdue` : info.days_left === 0 ? 'due today' : `${info.days_left}d left`;
      return `${when} · ${info.linked_items ? `${info.linked_items} linked` : 'nothing linked yet'}`;
    };
    const commitmentMeta = (item) => {
      const info = commitmentInfo[String(item.name).toLowerCase()];
      if (!info) return 'no rule set, so it is not scheduled';
      const label = { met: 'met', on_track: 'on track', tightening: 'tightening', at_risk: 'at risk', last_chance: 'last chance', behind: 'behind' }[info.state] || info.state;
      return `${info.progress}/${info.required} ${info.period === 'day' ? 'today' : `this ${info.period}`} · ${label}`;
    };
    return [
      {
        name: 'Goals', what: 'Where you are heading. Link tasks and habits to a goal and Chronos pulls them forward as its date nears.',
        items: [...(life.goal || []), ...(life.milestone || [])],
        count: (life.goal || []).length, meta: goalMeta, off: typeOff('goal'),
        actions: [
          canWizard('goal_planning') && ['Plan a goal', () => openWizard('goal_planning')],
          canView('goal_planner', 'Goal Planner') ? ['Open planner', () => openView('goal_planner', 'Goal Planner')] : ['Manage', () => openItems('goal')],
        ],
      },
      {
        name: 'Commitments', what: 'Promises to yourself: "3 workouts a week". Chronos pushes the habit harder as the week runs out.',
        items: life.commitment || [], meta: commitmentMeta, off: typeOff('commitment'),
        actions: [canWidget('Commitments') ? ['Open tracker', () => openWidget('Commitments')] : ['Manage', () => openItems('commitment')]],
      },
      {
        name: 'Habits', what: 'Small repeated actions, including chores. Chronos tracks streaks.',
        items: life.habit || [], meta,
        actions: [
          canWizard('chore_setup') && ['Set up chores', () => openWizard('chore_setup')],
          canWidget('HabitTracker') ? ['Open tracker', () => openWidget('HabitTracker')] : ['Manage', () => openItems('habit')],
        ],
      },
      {
        name: 'Routines', what: 'Reusable sequences: routine → subroutine → microroutine → single action.',
        items: [...(life.routine || []), ...(life.subroutine || []), ...(life.microroutine || [])],
        meta: (item) => `${item.type}${item.children ? ` · ${item.children} step${item.children === 1 ? '' : 's'}` : ''}`,
        actions: [['Open Routine Builder', () => openView('routine_builder', 'Routine Builder')]],
      },
      {
        name: 'Days & weeks', what: 'The shape of your time: fixed anchors, routines and open windows for each kind of day.',
        items: [...(life.day || []), ...(life.week || [])],
        meta: (item) => `${item.type}${item.children ? ` · ${item.children} block${item.children === 1 ? '' : 's'}` : ''}`,
        actions: [
          canWizard('life_setup') && ['Life Setup', () => openWizard('life_setup')],
          ['Day Builder', () => openView('day_builder', 'Day Builder')],
          canView('week_builder', 'Week Builder') && ['Week Builder', () => openView('week_builder', 'Week Builder')],
        ],
      },
      (() => {
        const open = (life.task || []).filter((t) => !CLOSED_STATES.has(String(t.status || '').toLowerCase()));
        const unsized = open.filter((t) => !t.duration || String(t.duration).trim() === '0').map((t) => t.name);
        return {
          name: 'Tasks', what: 'One-off things to get done. Give each a length; without one, Chronos plans it with your default length.',
          items: open,
          meta,
          notice: unsized.length ? `${unsized.length} of these ha${unsized.length === 1 ? 's' : 've'} no length yet, so Chronos plans ${unsized.length === 1 ? 'it' : 'them'} as ${s.defaults?.item_minutes || 30} min. Set real lengths in Manage.` : '',
          actions: [
            unsized.length && [`Give ${unsized.length === 1 ? 'it' : 'them'} 30 min`, () => sizeItems('task', unsized)],
            canWizard('brain_dump') && ['Brain Dump', () => openWizard('brain_dump')],
            ['Manage', () => openItems('task')],
          ],
        };
      })(),
      {
        name: 'Projects', what: 'Bigger pieces of work that group tasks and milestones.',
        items: life.project || [], meta, off: typeOff('project'),
        actions: [canView('project_manager', 'Project Manager') ? ['Open projects', () => openView('project_manager', 'Project Manager')] : ['Manage', () => openItems('project')]],
      },
      {
        name: 'Fixed times', what: 'Appointments, reminders and alarms: where you must be, and when.',
        items: [...(life.appointment || []), ...(life.reminder || []), ...(life.alarm || [])],
        meta: (item) => [item.date, item.time].filter(Boolean).join(' ') || item.type,
        actions: [canWidget('Clock') && ['Alarms & reminders', () => openWidget('Clock')], ['Manage', () => openItems('appointment')]],
      },
    ];
  }

  function renderLife(s) {
    const grid = h('div', { class: 'home-life' });
    areaDefinitions(s).forEach((area) => {
      const count = area.count ?? area.items.length;
      const list = h('ul', { class: 'home-area-list' });
      area.items.slice(0, 5).forEach((item) => {
        list.appendChild(h('li', {}, h('span', { title: item.name, text: item.name }), h('span', { class: 'dim', text: String(area.meta(item) || '') })));
      });
      if (area.items.length > 5) list.appendChild(h('li', {}, h('span', { class: 'dim', text: `+ ${area.items.length - 5} more` })));
      grid.appendChild(h('article', { class: 'home-area' },
        h('div', { class: 'home-area-head' },
          h('h3', { class: 'home-area-name', text: area.name }),
          h('span', { class: `home-area-count ${count ? '' : 'zero'}`, text: String(count) }),
        ),
        area.items.length ? list : h('p', { class: 'home-area-what', text: area.what }),
        area.off && h('p', { class: 'home-area-what', text: 'Switched off in this alpha release because it is unfinished.' }),
        area.notice && h('p', { class: 'home-area-what home-area-notice', text: area.notice }),
        h('div', { class: 'home-area-actions' },
          area.off
            ? h('button', { class: 'home-btn small', text: `Turn on ${area.name.toLowerCase()}`, title: 'Turns on every unfinished feature, not only this one.', disabled: state.busy, onclick: showEverything })
            : area.actions.filter(Boolean).map(([label, fn], idx) => h('button', { class: `home-btn small ${idx === 0 && !area.items.length ? 'primary' : ''}`, text: label, onclick: fn })),
        ),
      ));
    });
    return h('section', {},
      h('h2', { class: 'home-card-title', style: 'margin:6px 2px 10px' }, 'Your life in Chronos'),
      grid,
    );
  }

  function setupSteps(s) {
    const c = s.counts || {};
    const named = !!s.profile?.nickname && s.profile.nickname !== 'Pilot';
    const statusSet = Object.keys(s.status?.current || {}).length > 0;
    const routines = (c.routine || 0) + (c.subroutine || 0) + (c.microroutine || 0);
    const planned = !!s.today?.exists && actionableBlocks(s.today.blocks).length > 0;
    return [
      { title: 'Introduce yourself', why: 'Name, life categories and how you check in.', done: named, label: 'Onboarding', run: () => openWizard('onboarding'), show: canWizard('onboarding') },
      { title: 'Lay down your day skeleton', why: 'Sleep, work, meals, commute: the fixed points everything else flows around.', done: (c.day || 0) > 0, label: 'Life Setup', run: () => openWizard('life_setup'), show: canWizard('life_setup') },
      { title: 'Empty your head', why: 'Dump every task and worry once, so you stop carrying them.', done: (c.task || 0) > 0, label: 'Brain Dump', run: () => openWizard('brain_dump'), show: canWizard('brain_dump') },
      { title: 'Build your first routine', why: 'Start with one — a morning routine — and break it into small steps.', done: routines > 0, label: 'Routine Builder', run: () => openView('routine_builder', 'Routine Builder'), show: true },
      { title: 'Add your habits and chores', why: 'The repeating upkeep you no longer want to remember.', done: (c.habit || 0) > 0, label: 'Chore Setup', run: () => openWizard('chore_setup'), show: canWizard('chore_setup') },
      { title: 'Name what you are aiming for', why: 'Goals and commitments tell Chronos what matters.', done: (c.goal || 0) + (c.commitment || 0) > 0, label: typeOff('goal') && typeOff('commitment') ? 'Turn on goals' : (canWizard('goal_planning') ? 'Goal Planning' : 'Add a goal'), run: () => {
        if (typeOff('goal') && typeOff('commitment')) return showEverything();
        if (canWizard('goal_planning')) return openWizard('goal_planning');
        const type = wrap.querySelector('.home-capture select[name="type"]');
        if (type) { type.value = typeOff('goal') ? 'commitment' : 'goal'; type.dispatchEvent(new Event('change')); }
        wrap.querySelector('.home-capture input[name="name"]')?.focus();
      }, show: true },
      { title: 'Tell Chronos how you are', why: 'Energy, health and place change what a good day looks like.', done: statusSet, label: 'Set status', run: () => wrap.querySelector('.home-chip')?.focus(), show: true },
      { title: 'Let Chronos plan today', why: 'Then just follow "Right now" at the top of this page.', done: planned, label: 'Plan my day', run: planDay, show: true },
    ].filter((step) => step.show);
  }

  function renderSetup(s) {
    const steps = setupSteps(s);
    const doneCount = steps.filter((st) => st.done).length;
    const allDone = doneCount === steps.length;
    let collapsed = allDone;
    try {
      const stored = localStorage.getItem(SETUP_COLLAPSED_KEY);
      if (stored !== null) collapsed = stored === 'true';
    } catch { }
    const toggle = h('button', { class: 'home-link', text: collapsed ? 'Show' : 'Hide', onclick: () => {
      try { localStorage.setItem(SETUP_COLLAPSED_KEY, String(!collapsed)); } catch { }
      render();
    } });
    const card = h('section', { class: 'home-card' },
      h('h2', { class: 'home-card-title' }, `Set up once · ${doneCount} of ${steps.length}`, toggle),
    );
    if (collapsed) return card;
    const nextIdx = steps.findIndex((st) => !st.done);
    const list = h('ol', { class: 'home-steps' });
    steps.forEach((step, idx) => {
      list.appendChild(h('li', { class: `home-step ${step.done ? 'done' : ''} ${idx === nextIdx ? 'next' : ''}`.trim() },
        h('span', { class: 'home-step-dot', text: step.done ? '✓' : String(idx + 1) }),
        h('div', {}, h('div', { class: 'home-step-title', text: step.title }), h('div', { class: 'home-step-why', text: step.why })),
        h('button', { class: `home-btn small ${idx === nextIdx ? 'primary' : ''}`, text: step.label, disabled: state.busy, onclick: step.run }),
      ));
    });
    card.appendChild(list);
    return card;
  }

  function renderFoot(s) {
    const gate = s.alpha_gate || {};
    const limited = String(gate.release_profile || '').toLowerCase() !== 'full_dev' && (gate.disable_hidden_features || !gate.show_hidden_items);
    return h('div', { class: 'home-foot' },
      h('button', { class: 'home-link', text: 'What is Chronos?', onclick: () => openView('docs', 'Docs') }),
      h('button', { class: 'home-link', text: 'All items', onclick: () => openWidget('ItemManager') }),
      canWidget('Settings') && h('button', { class: 'home-link', text: 'Settings', onclick: () => openWidget('Settings') }),
      limited && h('button', { class: 'home-link', title: 'Shows the features this alpha release hides because they are unfinished: goal planner, commitments tracker, calendar, cockpit and more.', text: 'Show unfinished features too', onclick: showEverything }),
    );
  }

  function render() {
    const s = state.summary;
    if (!s) {
      wrap.replaceChildren(h('div', { class: 'home-card' },
        h('p', { class: 'home-empty', text: state.loadError ? `Home could not load: ${state.loadError}` : 'Loading your life…' }),
        state.loadError && h('button', { class: 'home-btn', text: 'Try again', onclick: () => load() }),
      ));
      return;
    }
    // Keep what the pilot was typing across re-renders.
    const oldForm = wrap.querySelector('form.home-capture');
    const draft = oldForm ? {
      values: Object.fromEntries(Array.from(oldForm.elements).filter((el) => el.name).map((el) => [el.name, el.value])),
      focused: document.activeElement && oldForm.contains(document.activeElement) ? document.activeElement.name : '',
    } : null;

    wrap.replaceChildren(
      renderHero(s),
      h('div', { class: 'home-grid-top' },
        h('div', { class: 'home-col' }, renderNow(s), renderStatus(s), renderCapture(s)),
        h('div', { class: 'home-col' }, renderDay(s), renderSaved(s), renderSetup(s)),
      ),
      renderLife(s),
      renderFoot(s),
    );

    if (draft) {
      const form = wrap.querySelector('form.home-capture');
      Array.from(form.elements).forEach((el) => {
        if (!el.name || !(el.name in draft.values)) return;
        // A select only takes a value it still offers (lists change as items are added).
        if (el.tagName !== 'SELECT' || Array.from(el.options).some((o) => o.value === draft.values[el.name])) el.value = draft.values[el.name];
      });
      if (state.clearDraft) {
        form.name.value = '';
        // When and How often belong to the item just added, not to the next one
        // (found 2026-11-20: a "before bed" carried over to the next habit).
        if (form.when) form.when.value = '';
        if (form.at_time) form.at_time.value = '';
        if (form.frequency) form.frequency.value = 'daily';
      }
      state.clearDraft = false;
      syncCaptureFields(form);
      if (draft.focused && form.elements[draft.focused]) form.elements[draft.focused].focus();
    }
  }

  // Refresh when the pilot returns from a wizard/builder, and once a minute so
  // "Right now" follows the clock. Never re-render under someone who is typing.
  const refreshQuietly = () => {
    if (disposed || state.busy || document.hidden) return;
    const active = document.activeElement;
    if (active && wrap.contains(active) && ['INPUT', 'SELECT'].includes(active.tagName)) return;
    void load({ quiet: true });
  };
  const onFocus = () => refreshQuietly();
  window.addEventListener('focus', onFocus);
  timer = window.setInterval(() => {
    if (!el.isConnected) { dispose(); return; }
    refreshQuietly();
  }, 60000);
  // Wizards are overlays on the same page: refresh when one closes.
  const observer = new MutationObserver((records) => {
    const removedOverlay = records.some((r) => Array.from(r.removedNodes).some((n) => n.nodeType === 1 && (n.matches?.('[data-wizard-overlay], .chronos-wizard-overlay, .wizard-overlay') || n.querySelector?.('[data-wizard-overlay]'))));
    if (removedOverlay) window.setTimeout(refreshQuietly, 300);
  });
  observer.observe(document.body, { childList: true });

  function dispose() {
    disposed = true;
    if (timer) window.clearInterval(timer);
    window.removeEventListener('focus', onFocus);
    observer.disconnect();
  }

  render();
  void load();
  return { dispose, refresh: load };
}
