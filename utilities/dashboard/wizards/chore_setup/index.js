const OVERLAY_TAG = 'chronos-chore-setup';
let stylesInjected = false;

function apiBase() {
  const origin = window.location.origin;
  if (!origin || origin === 'null' || origin.startsWith('file:')) return 'http://127.0.0.1:7357';
  return origin;
}

async function apiRequest(path, { method = 'GET', body } = {}) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.body = JSON.stringify(body);
    opts.headers['Content-Type'] = 'application/json';
  }
  const resp = await fetch(apiBase() + path, opts);
  const text = await resp.text();
  let data = text;
  try { data = JSON.parse(text); } catch {}
  if (!resp.ok || (data && data.ok === false)) {
    const err = (data && (data.error || data.stderr)) || text || `HTTP ${resp.status}`;
    throw new Error(err);
  }
  return data;
}

function injectStyles() {
  if (stylesInjected) return;
  const style = document.createElement('style');
  style.textContent = `
    .chore-setup-overlay {
      position: fixed;
      inset: 0;
      background: var(--chronos-overlay-gradient);
      z-index: 1200;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: clamp(16px,3vw,32px);
      backdrop-filter: var(--chronos-overlay-blur);
    }
    .chore-setup-shell {
      width: min(980px, 96vw);
      max-height: 94vh;
      background: linear-gradient(140deg, var(--chronos-surface-strong), rgba(3,5,12,0.98));
      border: 1px solid rgba(122,162,247,0.25);
      border-radius: 24px;
      box-shadow: 0 30px 90px rgba(0,0,0,0.65);
      display: flex;
      flex-direction: column;
      color: var(--chronos-text);
      padding: clamp(20px, 3vw, 32px);
      gap: 16px;
      position: relative;
    }
    .chore-setup-header h1 {
      margin: 0 0 6px;
      font-size: clamp(22px, 3vw, 30px);
    }
    .chore-setup-header p {
      margin: 0;
      color: var(--chronos-text-muted);
    }
    .chore-setup-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 14px;
      overflow: auto;
      padding-right: 4px;
      max-height: 58vh;
    }
    .chore-group {
      background: rgba(7,12,20,0.7);
      border: 1px solid var(--chronos-border-strong);
      border-radius: 16px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      min-height: 0;
      max-height: 52vh;
      overflow: auto;
    }
    .chore-group h3 {
      margin: 0;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--chronos-text-soft);
    }
    .chore-item {
      display: flex;
      gap: 8px;
      align-items: flex-start;
      font-size: 13px;
      padding: 6px 0;
    }
    .chore-item small {
      display: block;
      color: var(--chronos-text-muted);
    }
    .chore-custom-row {
      flex-direction: column;
      align-items: stretch;
      gap: 6px;
      background: rgba(10, 16, 28, 0.6);
      border: 1px solid rgba(122, 162, 247, 0.18);
      border-radius: 12px;
      padding: 8px;
    }
    .chore-custom-meta {
      display: grid;
      grid-template-columns: 1fr 90px;
      gap: 6px;
    }
    .chore-day-select {
      margin-top: 4px;
      padding: 4px 8px;
      font-size: 12px;
    }
    .chore-custom-meta .chore-day-select {
      grid-column: 1 / -1;
      margin-top: 0;
      padding: 8px 10px;
      font-size: 13px;
    }
    .chore-custom-meta .chore-custom-remove-btn {
      grid-column: 1 / -1;
      justify-self: end;
    }
    .chore-day-select:disabled {
      opacity: 0.55;
    }
    .chore-custom-input,
    .chore-custom-select {
      width: 100%;
      background: rgba(12, 18, 30, 0.9);
      border: 1px solid var(--chronos-border-strong);
      border-radius: 10px;
      color: var(--chronos-text);
      padding: 8px 10px;
      outline: none;
      font-size: 13px;
    }
    .chore-custom-input:focus,
    .chore-custom-select:focus {
      border-color: rgba(122, 162, 247, 0.75);
      box-shadow: 0 0 0 2px rgba(122, 162, 247, 0.2);
    }
    .chore-custom-remove-btn,
    .chore-custom-add-btn {
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 10px;
      padding: 8px 12px;
      background: rgba(12,14,24,0.9);
      color: var(--chronos-text);
      cursor: pointer;
      font-size: 13px;
    }
    .chore-custom-add-btn {
      align-self: flex-start;
      background: linear-gradient(140deg, rgba(122,162,247,0.25), rgba(12,14,24,0.95));
      border-color: rgba(122,162,247,0.45);
    }
    .chore-custom-remove-btn:hover,
    .chore-custom-add-btn:hover {
      filter: brightness(1.08);
    }
    .chore-setup-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }
    .chore-setup-status {
      flex: 1;
      min-height: 20px;
      color: var(--chronos-text-soft);
      background: rgba(21,28,46,0.85);
      border-radius: 12px;
      border: 1px solid rgba(41,55,92,0.8);
      padding: 10px 14px;
      font-size: 13px;
    }
    .chore-setup-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .chore-setup-actions button {
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 12px;
      padding: 10px 18px;
      background: rgba(12,14,24,0.9);
      color: inherit;
      cursor: pointer;
      font-size: 14px;
    }
    .chore-setup-actions button.primary {
      background: var(--chronos-accent-gradient);
      border-color: rgba(143,168,255,0.45);
      color: #fff;
      box-shadow: var(--chronos-accent-glow);
    }
  `;
  document.head.appendChild(style);
  stylesInjected = true;
}

const CHORES = [
  { name: 'Make Bed _example', frequency: 'daily', duration: 5, description: 'Reset the bed and tidy bedding.' },
  { name: 'Wash Dishes _example', frequency: 'daily', duration: 15, description: 'Clean dishes or load the dishwasher.' },
  { name: 'Wipe Kitchen Counters _example', frequency: 'daily', duration: 5, description: 'Wipe down counters and sink area.' },
  { name: 'Quick Tidy Common Area _example', frequency: 'daily', duration: 10, description: 'Put away clutter in shared spaces.' },
  { name: 'Sort Mail _example', frequency: 'daily', duration: 5, description: 'Sort mail and discard junk.' },
  { name: 'Laundry _example', frequency: 'weekly', duration: 60, description: 'Wash, dry, fold, and put away laundry.' },
  { name: 'Vacuum Floors _example', frequency: 'weekly', duration: 30, description: 'Vacuum main floors and rugs.' },
  { name: 'Clean Bathroom _example', frequency: 'weekly', duration: 30, description: 'Clean sink, toilet, and shower.' },
  { name: 'Change Bed Sheets _example', frequency: 'weekly', duration: 15, description: 'Replace sheets and pillowcases.' },
  { name: 'Take Out Trash and Recycling _example', frequency: 'weekly', duration: 10, description: 'Empty household trash and recycling.' },
  { name: 'Mop Floors _example', frequency: 'weekly', duration: 30, description: 'Mop hard floors.' },
  { name: 'Water Houseplants _example', frequency: 'weekly', duration: 15, description: 'Water and check plant health.' },
  { name: 'Deep Clean Fridge _example', frequency: 'monthly', duration: 30, description: 'Toss expired items and wipe shelves.' },
  { name: 'Clean Microwave and Oven _example', frequency: 'monthly', duration: 30, description: 'Clean inside surfaces and racks.' },
  { name: 'Dust Fans and Baseboards _example', frequency: 'monthly', duration: 30, description: 'Dust fan blades and baseboards.' },
  { name: 'Wash Windows _example', frequency: 'monthly', duration: 45, description: 'Clean interior windows and glass.' },
  { name: 'Clean Shower Drain _example', frequency: 'monthly', duration: 15, description: 'Remove hair and rinse the drain.' },
  { name: 'Organize Pantry _example', frequency: 'monthly', duration: 30, description: 'Group items and check expiration dates.' },
  { name: 'Replace HVAC Filter _example', frequency: 'quarterly', duration: 15, description: 'Replace or clean HVAC filter.' },
  { name: 'Rotate Mattress _example', frequency: 'quarterly', duration: 20, description: 'Rotate mattress to reduce wear.' },
  { name: 'Deep Declutter Closet _example', frequency: 'quarterly', duration: 45, description: 'Remove unused items and reorganize.' },
  { name: 'Clean Behind Appliances _example', frequency: 'quarterly', duration: 45, description: 'Clean behind fridge and stove.' },
  { name: 'Test Smoke and CO Alarms _example', frequency: 'yearly', duration: 20, description: 'Test alarms and replace batteries if needed.' },
  { name: 'Clean Dryer Vent _example', frequency: 'yearly', duration: 30, description: 'Clear lint buildup for safety.' },
  { name: 'Deep Clean Carpets _example', frequency: 'yearly', duration: 90, description: 'Shampoo or steam clean carpets.' },
  { name: 'Review Home Emergency Kit _example', frequency: 'yearly', duration: 30, description: 'Check supplies and refresh as needed.' },
];

// Recurring chores (roadmap step 1c, decision D2; docs/scheduling/recurrence_design.md).
// A weekly chore can have a weekday and a monthly one a day of the month (`day:`).
// "Any day" writes no day: Kairos then spreads it over the week or month together
// with the other chores, so no day gets a wall of chores. The wizard does not
// spread on its own, so there is only one spreading rule.
const WEEKDAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function ordinal(n) {
  const tens = n % 100;
  if (tens >= 10 && tens <= 20) return `${n}th`;
  return `${n}${({ 1: 'st', 2: 'nd', 3: 'rd' })[n % 10] || 'th'}`;
}

function fillDayOptions(select, frequency) {
  const previous = select.value;
  select.innerHTML = '';
  const add = (value, label) => {
    const opt = document.createElement('option');
    opt.value = value;
    opt.textContent = label;
    select.appendChild(opt);
  };
  const pickable = frequency === 'weekly' || frequency === 'monthly';
  add('', pickable ? 'Any day (Chronos spreads it)' : (frequency === 'daily' ? 'Every day' : 'Chronos spreads it'));
  if (frequency === 'weekly') WEEKDAYS.forEach(day => add(day, day.charAt(0).toUpperCase() + day.slice(1)));
  if (frequency === 'monthly') {
    for (let n = 1; n <= 31; n += 1) add(String(n), n === 31 ? '31st (always the last day)' : `the ${ordinal(n)}`);
  }
  select.disabled = !pickable;
  select.title = pickable
    ? 'Pick a day, or leave "Any day" and Chronos spreads your chores over the period.'
    : 'Quarterly and yearly chores are spread over the period by Chronos; daily ones are every day.';
  if (Array.from(select.options).some(opt => opt.value === previous)) select.value = previous;
}

function buildDayPicker(frequency, choreName) {
  const select = document.createElement('select');
  select.className = 'chore-custom-select chore-day-select';
  select.dataset.field = 'day';
  if (choreName) select.dataset.chore = choreName;
  fillDayOptions(select, frequency);
  return select;
}

// The fields of a chore habit. Only meaningful fields: through the console's `new`
// an empty list arrives as empty text (and `complete` then fails on it), and a
// missing history, streak or length is the same as an empty one.
function choreProperties({ frequency, duration, description }) {
  const props = {
    status: 'active',
    polarity: 'good',
    chore: true,
    frequency,
    tags: ['chore', frequency],
    created: todayISO(),
  };
  if (description) props.description = description;
  if (duration > 0) props.duration = duration;
  return props;
}

function groupByFrequency(items) {
  const groups = { daily: [], weekly: [], monthly: [], quarterly: [], yearly: [] };
  items.forEach(item => {
    const key = (item.frequency || 'weekly').toLowerCase();
    (groups[key] || (groups[key] = [])).push(item);
  });
  return groups;
}

async function itemExists(type, name) {
  try {
    await apiRequest(`/api/item?type=${encodeURIComponent(type)}&name=${encodeURIComponent(name)}`);
    return true;
  } catch {
    return false;
  }
}

export async function launch(context, options = {}) {
  injectStyles();
  const overlay = document.createElement('div');
  overlay.className = 'chore-setup-overlay chronos-wizard-overlay';
  overlay.dataset.wizardOverlay = OVERLAY_TAG;

  const shell = document.createElement('div');
  shell.className = 'chore-setup-shell chronos-wizard-shell';

  const header = document.createElement('div');
  header.className = 'chore-setup-header';
  header.innerHTML = `
    <h1>Chore Setup</h1>
    <p>Select the chores you want. Weekly and monthly chores can have a day; with "Any day", Chronos spreads them over the week or month so no day gets a wall of chores. A missed chore comes back every day until it is done.</p>
  `;

  const grid = document.createElement('div');
  grid.className = 'chore-setup-grid';

  const groups = groupByFrequency(CHORES);
  const selected = new Set(CHORES.map(item => item.name));
  const dayPickers = new Map();   // built-in chore name -> its day picker (weekly and monthly only)
  Object.entries(groups).forEach(([freq, items]) => {
    if (!items.length) return;
    const group = document.createElement('div');
    group.className = 'chore-group';
    const title = document.createElement('h3');
    title.textContent = freq;
    group.appendChild(title);
    items.forEach(item => {
      const row = document.createElement('label');
      row.className = 'chore-item';
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = true;
      checkbox.addEventListener('change', () => {
        if (checkbox.checked) selected.add(item.name);
        else selected.delete(item.name);
      });
      const text = document.createElement('div');
      const liveName = item.name.replace(/ _example$/i, '');
      text.innerHTML = `<strong>${liveName}</strong><small>${item.description} (${item.duration}m)</small>`;
      if (item.frequency === 'weekly' || item.frequency === 'monthly') {
        const picker = buildDayPicker(item.frequency, liveName);
        dayPickers.set(item.name, picker);
        text.appendChild(picker);
      }
      row.append(checkbox, text);
      group.appendChild(row);
    });
    grid.appendChild(group);
  });

  const statusLine = document.createElement('div');
  statusLine.className = 'chore-setup-status chronos-wizard-status';

  const customCard = document.createElement('div');
  customCard.className = 'chore-group';
  const customTitle = document.createElement('h3');
  customTitle.textContent = 'custom chores';
  const customList = document.createElement('div');
  customCard.append(customTitle, customList);
  const customRows = [];

  function buildCustomRow(data = {}) {
    const row = document.createElement('div');
    row.className = 'chore-item chore-custom-row';

    const name = document.createElement('input');
    name.className = 'chore-custom-input';
    name.placeholder = 'Chore name (e.g., "Wipe Fridge Handles")';
    name.value = data.name || '';

    const desc = document.createElement('input');
    desc.className = 'chore-custom-input';
    desc.placeholder = 'Description (optional)';
    desc.value = data.description || '';

    const meta = document.createElement('div');
    meta.className = 'chore-custom-meta';

    const freq = document.createElement('select');
    freq.className = 'chore-custom-select';
    ['daily', 'weekly', 'monthly', 'quarterly', 'yearly'].forEach(val => {
      const opt = document.createElement('option');
      opt.value = val;
      opt.textContent = val;
      if (val === (data.frequency || 'weekly')) opt.selected = true;
      freq.appendChild(opt);
    });

    const day = buildDayPicker(freq.value, '');
    freq.addEventListener('change', () => fillDayOptions(day, freq.value));

    const duration = document.createElement('input');
    duration.className = 'chore-custom-input';
    duration.type = 'number';
    duration.min = '0';
    duration.placeholder = 'Minutes';
    duration.value = data.duration || '';

    const remove = document.createElement('button');
    remove.className = 'chore-custom-remove-btn';
    remove.textContent = 'Remove';
    remove.addEventListener('click', () => {
      const idx = customRows.indexOf(payload);
      if (idx >= 0) customRows.splice(idx, 1);
      row.remove();
    });

    // Two lines: how often and how long, then the day (full width) and Remove.
    meta.append(freq, duration, day, remove);
    row.append(name, desc, meta);

    const payload = {
      nameEl: name,
      descEl: desc,
      freqEl: freq,
      dayEl: day,
      durationEl: duration,
    };
    customRows.push(payload);
    customList.appendChild(row);
  }

  const addCustomBtn = document.createElement('button');
  addCustomBtn.className = 'chore-custom-add-btn';
  addCustomBtn.textContent = 'Add Custom Chore';
  addCustomBtn.addEventListener('click', () => buildCustomRow());
  customCard.appendChild(addCustomBtn);

  grid.appendChild(customCard);

  const actions = document.createElement('div');
  actions.className = 'chore-setup-actions chronos-wizard-actions';
  const createBtn = document.createElement('button');
  createBtn.className = 'primary';
  createBtn.textContent = 'Create Selected Chores';
  const closeBtn = document.createElement('button');
  closeBtn.textContent = 'Close';
  actions.append(createBtn, closeBtn);

  const footer = document.createElement('div');
  footer.className = 'chore-setup-footer';
  footer.append(statusLine, actions);

  shell.append(header, grid, footer);
  overlay.appendChild(shell);
  document.body.appendChild(overlay);

  const helpBtn = context?.createHelpButton?.('ChoreSetup', {
    className: 'wizard-help-btn icon-btn help-btn',
    fallbackLabel: 'Chore Setup Wizard'
  });
  if (helpBtn) shell.appendChild(helpBtn);

  // Make one chore and check that it is really there. Returns 'created', 'skipped' or 'failed'.
  // The dashboard reports a console command as done whenever it exits normally, even when
  // it printed an error (issue 23), so the wizard used to count chores it never made.
  async function createChore(liveName, chore, sourceName) {
    if (await itemExists('habit', liveName)) return 'skipped';
    try {
      if (sourceName && await itemExists('habit', sourceName)) {
        // The original path: copy the shipped "<name> _example" habit when it exists.
        const extra = { created: todayISO() };
        if (chore.day) extra.day = chore.day;
        await apiRequest('/api/item/copy', {
          method: 'POST',
          body: { type: 'habit', source: sourceName, new_name: liveName, properties: extra },
        });
      } else {
        // alpha_v0.3 ships no _example habits (issue 22): make the chore from this list.
        // POST /api/item takes { type, name, properties } (a `data` key was stored as text, issue 29).
        const props = choreProperties(chore);
        if (chore.day) props.day = chore.day;
        await apiRequest('/api/item', {
          method: 'POST',
          body: { type: 'habit', name: liveName, properties: props },
        });
      }
    } catch (err) {
      console.warn('[Chore Setup] could not create', liveName, err);
      return 'failed';
    }
    return (await itemExists('habit', liveName)) ? 'created' : 'failed';
  }

  createBtn.addEventListener('click', async () => {
    createBtn.disabled = true;
    statusLine.textContent = 'Creating chores...';
    const counts = { created: 0, skipped: 0, failed: [] };
    const tally = (result, name) => {
      if (result === 'failed') counts.failed.push(name);
      else counts[result] += 1;
    };
    const selectedItems = CHORES.filter(item => selected.has(item.name));
    for (const item of selectedItems) {
      const liveName = item.name.replace(/ _example$/i, '').trim();
      const picker = dayPickers.get(item.name);
      const chore = {
        frequency: item.frequency,
        duration: item.duration,
        description: item.description,
        day: picker && !picker.disabled ? picker.value : '',
      };
      tally(await createChore(liveName, chore, item.name), liveName);
    }
    for (const row of customRows) {
      const name = row.nameEl.value.trim();
      if (!name) continue;
      const chore = {
        frequency: row.freqEl.value,
        duration: parseInt(row.durationEl.value || '0', 10) || 0,
        description: row.descEl.value.trim(),
        day: row.dayEl && !row.dayEl.disabled ? row.dayEl.value : '',
      };
      tally(await createChore(name, chore, null), name);
    }
    let text = `Created ${counts.created} chores. Skipped ${counts.skipped} existing.`;
    if (counts.failed.length) text += ` Could not create ${counts.failed.length}: ${counts.failed.join(', ')}.`;
    statusLine.textContent = text;
    createBtn.disabled = false;
  });

  closeBtn.addEventListener('click', () => overlay.remove());
  overlay.addEventListener('click', (ev) => { if (ev.target === overlay) overlay.remove(); });
}
