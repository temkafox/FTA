/* ActPilot web — маршрут кампании + дерево пассивов, mobile-first. */
'use strict';

const KEY = 'actpilot.web.v1';
const LEVEL_MIN = 1;
const LEVEL_MAX = 100;

/* ───────────── состояние ───────────── */

const defaults = () => ({
  level: 1,
  act: 0,
  done: {},       // id шага -> 1
  splits: {},     // id шага -> секунды на момент отметки
  started: null,  // мс начала таймера
  build: null,    // исходный код PoB
  tab: 'route',
  openExtras: {}, // акт -> раскрыта ли секция «Дополнительно»
});

let state = defaults();

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) state = Object.assign(defaults(), JSON.parse(raw));
  } catch (e) {
    state = defaults();
  }
}

let saveTimer = null;
function save() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { /* переполнение не критично */ }
  }, 120);
}

const $ = (sel) => document.querySelector(sel);

/* ───────────── данные шагов ───────────── */

let acts = [];

function totalSteps() {
  return acts.reduce((sum, act) => sum + act.steps.length, 0);
}

function doneCount() {
  return acts.reduce((sum, act) => sum + act.steps.filter(s => state.done[s.id]).length, 0);
}

function actDone(act) {
  return act.steps.length > 0 && act.steps.every(s => state.done[s.id]);
}

function elapsed() {
  return state.started ? Math.max(0, Math.round((Date.now() - state.started) / 1000)) : 0;
}

function fmt(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

/* ───────────── маршрут ───────────── */

function renderActs() {
  const host = $('#acts');
  host.innerHTML = '';
  acts.forEach((act, index) => {
    const btn = document.createElement('button');
    btn.className = 'act';
    btn.dataset.act = index;
    btn.textContent = index + 1;
    btn.title = act.name;
    if (actDone(act)) btn.classList.add('done');
    if (index === state.act) btn.classList.add('current');
    if (actDone(act)) {
      const tick = document.createElement('span');
      tick.className = 'tick';
      tick.textContent = '✓';
      btn.append(tick);
    }
    host.append(btn);
  });
}

function renderProgress() {
  const total = totalSteps();
  const pct = total ? (doneCount() / total) * 100 : 0;
  $('#progressFill').style.width = `${pct}%`;
  updateNextButton();
}

function renderSteps() {
  const act = acts[state.act];
  const host = $('#steps');
  host.innerHTML = '';
  if (!act) return;
  let markedNext = false;
  act.steps.forEach((step, index) => {
    const li = document.createElement('li');
    li.className = 'step';
    li.dataset.id = step.id;
    if (state.done[step.id]) li.classList.add('done');
    else if (!markedNext) {
      li.classList.add('now');
      markedNext = true;
    }

    const box = document.createElement('span');
    box.className = 'box';
    box.textContent = '✓';

    const text = document.createElement('span');
    text.className = 'text';
    text.textContent = step.text;

    li.append(box, text);

    if (state.done[step.id] && state.splits[step.id] != null) {
      const split = document.createElement('span');
      split.className = 'split';
      split.textContent = fmt(state.splits[step.id]);
      li.append(split);
    }
    host.append(li);
  });

  if (act.extras && act.extras.length) host.append(buildExtras(act));
}

function buildExtras(act) {
  const open = Boolean(state.openExtras && state.openExtras[state.act]);
  const item = document.createElement('li');
  item.className = 'extras';

  const head = document.createElement('button');
  head.className = 'extras-head';
  head.setAttribute('aria-expanded', String(open));

  const label = document.createElement('span');
  label.className = 'extras-label';
  label.textContent = 'Дополнительно';

  const count = document.createElement('span');
  count.className = 'extras-count';
  count.textContent = act.extras.length;

  const chevron = document.createElement('span');
  chevron.className = 'chev';
  chevron.textContent = '›';

  head.append(label, count, chevron);
  item.append(head);

  const list = document.createElement('ul');
  list.className = 'extras-list';
  list.hidden = !open;
  item.classList.toggle('open', open);
  for (const text of act.extras) {
    const row = document.createElement('li');
    row.textContent = text;
    list.append(row);
  }
  item.append(list);
  return item;
}

function toggleExtras() {
  if (!state.openExtras) state.openExtras = {};
  const open = !state.openExtras[state.act];
  state.openExtras[state.act] = open;
  const item = document.querySelector('.extras');
  if (item) {
    item.classList.toggle('open', open);
    item.querySelector('.extras-head').setAttribute('aria-expanded', String(open));
    item.querySelector('.extras-list').hidden = !open;
  }
  save();
}

function firstOpenAct() {
  const index = acts.findIndex(act => !actDone(act));
  return index < 0 ? acts.length - 1 : index;
}

function nextStepId() {
  const act = acts[state.act];
  if (!act) return null;
  const step = act.steps.find(item => !state.done[item.id]);
  return step ? step.id : null;
}

function updateNextButton() {
  const id = nextStepId();
  $('#nextWrap').hidden = state.tab !== 'route';
  $('#nextBtn').disabled = !id;
  $('#nextBtn').textContent = id ? 'Следующий шаг' : 'Акт пройден';
}

function toggleStep(id) {
  const now = Date.now();
  if (state.done[id]) {
    delete state.done[id];
    delete state.splits[id];
  } else {
    if (!state.started) state.started = now;
    state.done[id] = 1;
    state.splits[id] = elapsed();
  }
  const act = acts[state.act];
  if (act && actDone(act)) {
    const next = acts.findIndex((item, index) => index > state.act && !actDone(item));
    if (next >= 0) state.act = next;
  }
  save();
  renderActs();
  renderSteps();
  renderProgress();
  updateNextButton();
}

/* ───────────── уровень ───────────── */

function setLevel(value) {
  state.level = Math.max(LEVEL_MIN, Math.min(LEVEL_MAX, value));
  $('#lvlNum').textContent = state.level;
  save();
  tree.invalidate();
}

/* ───────────── дерево ───────────── */

const QUEST_LEVELS = [5, 10, 19, 20, 27, 32, 38, 44, 46, 48, 50, 52, 54, 56, 58, 60, 61, 62, 64, 65, 67, 68, 68];

const ORBIT_DEGREES = {
  16: [0, 30, 45, 60, 90, 120, 135, 150, 180, 210, 225, 240, 270, 300, 315, 330],
  40: Array.from({ length: 36 }, (_, i) => i * 10).concat([45, 135, 225, 315]).sort((a, b) => a - b),
};

function orbitAngle(index, count) {
  const table = ORBIT_DEGREES[count];
  if (table && index >= 0 && index < table.length) return (table[index] * Math.PI) / 180;
  return (2 * Math.PI * index) / Math.max(1, count);
}

function passiveBudget(level) {
  return (level - 1) + QUEST_LEVELS.filter(item => item <= level).length;
}

const tree = {
  ready: false,
  data: null,
  points: new Map(),   // id -> [x, y]
  edges: [],           // [a, b]
  view: { k: 1, x: 0, y: 0 },
  plan: { taken: new Set(), next: new Set() },
  loadedCode: null,

  async load() {
    if (this.ready) return;
    const response = await fetch('data/tree.json');
    this.data = await response.json();
    this.project();
    this.ready = true;
    this.resize();
    this.applyPlan();
    this.fit();
  },

  project() {
    const { groups, nodes, orbit_radii: radii, per_orbit: counts } = this.data;
    for (const [id, node] of Object.entries(nodes)) {
      /* ассенданси живёт на отдельном экране — в общем полотне только мешает */
      if (node.asc) continue;
      const group = groups[String(node.g)];
      if (!group) continue;
      const orbit = node.o || 0;
      const radius = orbit < radii.length ? radii[orbit] : 0;
      const count = orbit < counts.length ? counts[orbit] : 1;
      const angle = orbitAngle(node.i || 0, count);
      this.points.set(id, [group[0] + radius * Math.sin(angle), group[1] - radius * Math.cos(angle)]);
    }
    const seen = new Set();
    for (const [id, node] of Object.entries(nodes)) {
      if (!this.points.has(id)) continue;
      for (const other of node.out || []) {
        if (!this.points.has(other) || other === id) continue;
        const key = id < other ? `${id}|${other}` : `${other}|${id}`;
        if (seen.has(key)) continue;
        seen.add(key);
        this.edges.push([id, other]);
      }
    }
  },

  /* билд: один спек — режем по бюджету очков, несколько — берём ближайший по уровню */
  planFor(level) {
    const specs = this.specs();
    if (!specs.length) return { taken: new Set(), next: new Set() };
    const budget = passiveBudget(level);
    let taken;
    let upcoming;
    let stage = null;
    if (specs.length > 1) {
      if (level < specs[0].level) {
        /* до первого этапа показываем ровно то, что позволяют очки */
        taken = new Set(specs[0].nodes.slice(0, budget));
        upcoming = specs[0].nodes.slice(budget, budget + 10);
      } else {
        let current = specs[0];
        for (const spec of specs) if (spec.level <= level) current = spec;
        const index = specs.indexOf(current);
        taken = new Set(current.nodes);
        const following = specs[index + 1];
        upcoming = following ? following.nodes.filter(id => !taken.has(id)) : [];
        stage = current;
      }
    } else {
      const nodes = specs[0].nodes;
      taken = new Set(nodes.slice(0, budget));
      upcoming = nodes.slice(budget, budget + 10);
    }
    const visible = (id) => this.points.has(id);
    return {
      taken: new Set([...taken].filter(visible)),
      next: new Set(upcoming.filter(visible)),
      budget,
      stage,
    };
  },

  specs() {
    const build = state.build ? parseBuild(state.build) : null;
    return build ? build.specs : [];
  },

  applyPlan() {
    this.plan = this.planFor(state.level);
    const count = this.plan.taken.size;
    if (!build) $('#treeCount').textContent = 'билд не загружен';
    else if (this.plan.stage) $('#treeCount').textContent = `${count} нод · этап ур. ${this.plan.stage.level}`;
    else $('#treeCount').textContent = `${count} из ${this.plan.budget} очков · ур. ${state.level}`;
    this.draw();
  },

  invalidate() {
    if (!this.ready) return;
    this.applyPlan();
  },

  resize() {
    const canvas = $('#canvas');
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const ratio = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.round(rect.width * ratio);
    canvas.height = Math.round(rect.height * ratio);
    this.ratio = ratio;
    this.width = rect.width;
    this.height = rect.height;
    this.draw();
  },

  fit() {
    if (!this.ready || !this.points.size) return;
    const { min_x: minX, max_x: maxX, min_y: minY, max_y: maxY } = this.data;
    const worldW = maxX - minX;
    const worldH = maxY - minY;
    const k = Math.min(this.width / worldW, this.height / worldH) * 0.94;
    this.view = {
      k,
      x: this.width / 2 - ((minX + maxX) / 2) * k,
      y: this.height / 2 - ((minY + maxY) / 2) * k,
    };
    this.draw();
  },

  /* вписать в экран именно план билда: всё дерево на телефоне нечитаемо */
  focus() {
    if (!this.ready || !this.points.size) return;
    const points = [...this.plan.taken, ...this.plan.next]
      .map(id => this.points.get(id))
      .filter(Boolean);
    if (points.length < 2) return this.fit();
    const xs = points.map(point => point[0]);
    const ys = points.map(point => point[1]);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const spanX = Math.max(1400, maxX - minX);
    const spanY = Math.max(1400, maxY - minY);
    const k = Math.min(0.3, Math.min(this.width / spanX, this.height / spanY) * 0.86);
    this.view = {
      k,
      x: this.width / 2 - ((minX + maxX) / 2) * k,
      y: this.height / 2 - ((minY + maxY) / 2) * k,
    };
    this.draw();
  },

  toScreen(x, y) {
    const { k, x: tx, y: ty } = this.view;
    return [x * k + tx, y * k + ty];
  },

  draw() {
    if (!this.ready || !this.width) return;
    const canvas = $('#canvas');
    const ctx = canvas.getContext('2d');
    const { k, x: tx, y: ty } = this.view;
    ctx.setTransform(this.ratio, 0, 0, this.ratio, 0, 0);
    ctx.clearRect(0, 0, this.width, this.height);

    if (!this.specs().length) {
      ctx.fillStyle = 'rgba(242,238,229,.42)';
      ctx.font = '14px -apple-system, "Segoe UI", sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Импортируйте билд: «Импорт PoB»', this.width / 2, this.height / 2);
      return;
    }

    const taken = this.plan.taken;
    const next = this.plan.next;
    const pad = 40;

    /* рёбра */
    ctx.lineWidth = 1;
    for (const [a, b] of this.edges) {
      const pa = this.points.get(a);
      const pb = this.points.get(b);
      if (!pa || !pb) continue;
      const x1 = pa[0] * k + tx, y1 = pa[1] * k + ty;
      const x2 = pb[0] * k + tx, y2 = pb[1] * k + ty;
      if ((x1 < -pad && x2 < -pad) || (x1 > this.width + pad && x2 > this.width + pad)) continue;
      if ((y1 < -pad && y2 < -pad) || (y1 > this.height + pad && y2 > this.height + pad)) continue;
      const hot = (taken.has(a) && taken.has(b)) || (next.has(a) && next.has(b));
      ctx.strokeStyle = hot ? 'rgba(55,232,103,.55)' : 'rgba(255,255,255,.05)';
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }

    /* ноды */
    const radius = { 0: 3.2, 1: 6.4, 2: 7.6, 3: 5.4, 4: 6.2, 5: 5.4 };
    for (const [id, node] of Object.entries(this.data.nodes)) {
      const point = this.points.get(id);
      if (!point) continue;
      const sx = point[0] * k + tx;
      const sy = point[1] * k + ty;
      if (sx < -pad || sx > this.width + pad || sy < -pad || sy > this.height + pad) continue;
      const r = radius[node.k] || 3.2;
      const isTaken = taken.has(id);
      const isNext = next.has(id);
      ctx.beginPath();
      ctx.arc(sx, sy, isNext ? r + 1.2 : r, 0, Math.PI * 2);
      if (isTaken) {
        ctx.fillStyle = '#37e867';
        ctx.fill();
        ctx.strokeStyle = 'rgba(10,25,15,.9)';
        ctx.lineWidth = 1;
      } else if (isNext) {
        ctx.fillStyle = '#e0b96f';
        ctx.fill();
        ctx.strokeStyle = 'rgba(255,240,200,.95)';
        ctx.lineWidth = 1.4;
      } else {
        ctx.fillStyle = node.k === 0 ? '#141419' : '#1c1c24';
        ctx.fill();
        ctx.strokeStyle = node.k === 0 ? 'rgba(255,255,255,.16)' : 'rgba(224,185,111,.35)';
        ctx.lineWidth = 1;
      }
      ctx.stroke();
    }
  },

  nodeAt(clientX, clientY) {
    const rect = $('#canvas').getBoundingClientRect();
    const px = clientX - rect.left;
    const py = clientY - rect.top;
    let best = null;
    let bestDist = 18;
    for (const [id, point] of this.points) {
      const [sx, sy] = this.toScreen(point[0], point[1]);
      const dist = Math.hypot(sx - px, sy - py);
      if (dist < bestDist) {
        bestDist = dist;
        best = id;
      }
    }
    return best;
  },
};

/* ───────────── разбор PoB ───────────── */

let build = null;

function decodeBase64(text) {
  const normalized = text.replace(/\s+/g, '').replace(/-/g, '+').replace(/_/g, '/');
  const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

async function inflate(bytes, format) {
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream(format));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

async function decodePob(text) {
  const raw = (text || '').trim();
  if (!raw) throw new Error('Пусто');
  if (raw.startsWith('<')) return raw;
  if (/^https?:/i.test(raw)) throw new Error('Ссылки pobb.in не поддерживаются — вставьте код экспорта');
  const bytes = decodeBase64(raw);
  for (const format of ['deflate', 'deflate-raw']) {
    try {
      return new TextDecoder('utf-8').decode(await inflate(bytes, format));
    } catch (e) { /* пробуем следующий формат */ }
  }
  throw new Error('Не удалось распаковать код Path of Building');
}

function parseBuildXml(xmlText) {
  const document_ = new DOMParser().parseFromString(xmlText, 'application/xml');
  const root = document_.documentElement;
  if (!root || root.nodeName !== 'PathOfBuilding') throw new Error('Это не экспорт Path of Building');
  const buildNode = root.querySelector('Build');
  const class_ = buildNode ? buildNode.getAttribute('className') || '' : '';
  const ascendancy = buildNode ? buildNode.getAttribute('ascendClassName') || '' : '';
  const buildLevel = buildNode ? Number(buildNode.getAttribute('level') || 1) : 1;
  const specs = [];
  for (const spec of root.querySelectorAll('Tree > Spec')) {
    const nodes = (spec.getAttribute('nodes') || '')
      .split(',')
      .map(value => value.trim())
      .filter(Boolean);
    const title = spec.getAttribute('title') || '';
    specs.push({ level: levelFromTitle(title, 1), nodes, title });
  }
  specs.sort((a, b) => a.level - b.level);
  if (!specs.length) throw new Error('В билде нет дерева пассивов');
  return { class: class_, ascendancy, specs, gemSets: parseGemSets(root, buildLevel) };
}

function levelFromTitle(title, fallback) {
  const explicit = title.match(/(?:level|lvl|lev|уров(?:ень|ня)?|ур\.?)[\s:_-]*(\d{1,3})/i)
    || title.match(/(?<!\d)(\d{1,3})\s*[-–—]\s*(\d{1,3})(?!\d)/)
    || title.match(/(?<!\d)(\d{1,3})\s*(?:points?|pts?|очк\w*)/i)
    || title.match(/^\s*(\d{1,3})\s*$/);
  if (!explicit) return Math.max(1, Math.min(100, Number(fallback) || 1));
  const value = explicit[1];
  return Math.max(1, Math.min(100, Number(value) || 1));
}

function gemIsSupport(gem) {
  const explicit = gem.getAttribute('support');
  if (explicit !== null) return explicit.toLowerCase() === 'true';
  if ((gem.getAttribute('skillId') || '').startsWith('Support')) return true;
  return (gem.getAttribute('gemId') || '').includes('SupportGem');
}

function parseGemSets(root, buildLevel) {
  const sets = [];
  const containers = root.querySelectorAll('Skills > SkillSet');
  const groups = containers.length ? [...containers] : [root.querySelector('Skills')].filter(Boolean);
  for (const set of groups) {
    const title = set.getAttribute('title') || set.getAttribute('label') || 'Набор камней';
    const level = containers.length ? levelFromTitle(title, buildLevel) : Math.max(1, buildLevel || 1);
    const links = [];
    for (const skill of set.querySelectorAll('Skill')) {
      if ((skill.getAttribute('enabled') || 'true').toLowerCase() === 'false') continue;
      if ((skill.getAttribute('source') || '').trim()) continue;
      const gems_ = [];
      for (const gem of skill.querySelectorAll('Gem')) {
        if ((gem.getAttribute('enabled') || 'true').toLowerCase() === 'false') continue;
        const name = gem.getAttribute('nameSpec') || gem.getAttribute('name') || '';
        if (!name.trim()) continue;
        gems_.push({ name: name.trim(), support: gemIsSupport(gem), level: gem.getAttribute('level') });
      }
      if (!gems_.length) continue;
      links.push({ label: skill.getAttribute('label') || skill.getAttribute('slot') || 'Связка', gems: gems_ });
    }
    if (links.length) sets.push({ level, title, links });
  }
  return sets;
}

function parseBuild(code) {
  if (!code || !build || build.code !== code) return null;
  return build;
}

async function loadBuild(code) {
  const xml = await decodePob(code);
  const parsed = parseBuildXml(xml);
  build = { code, ...parsed };
  state.build = code;
  save();
}

/* ───────────── план камней ───────────── */

const ACT_END_LEVEL = { 1: 12, 2: 22, 3: 33, 4: 40, 5: 45, 6: 50, 7: 55, 8: 60, 9: 64, 10: 68 };
const PURCHASE_LEAD = 10;
const GRANTED_NON_GEMS = new Set(['primal aegis']);

const gemsData = { ready: false, data: null, known: new Set(), plan: null, error: null };

async function ensureGemsData() {
  if (gemsData.ready) return;
  const response = await fetch('data/gems.json');
  gemsData.data = await response.json();
  gemsData.known = new Set(gemsData.data.known);
  gemsData.ready = true;
}

function normalizedClass(value) {
  const wanted = (value || '').trim().toLowerCase();
  const found = (gemsData.data?.classes || []).find(name => name.toLowerCase() === wanted);
  return found || null;
}

function gemKey(name, support) {
  const key = (name || '').trim().toLowerCase();
  if (!key) return '';
  const candidates = key.endsWith(' support')
    ? [key, key.slice(0, -' support'.length)]
    : (support ? [`${key} support`, key] : [key, `${key} support`]);
  return candidates.find(candidate => gemsData.known.has(candidate)) || key;
}

function gemLabel(key, fallback) {
  return (gemsData.data && gemsData.data.names[key]) || fallback || key;
}

function requiredGems(sets) {
  const needed = new Map();
  const ordered = [...sets].sort((a, b) => a.level - b.level);
  for (const set of ordered) {
    const counts = new Map();
    for (const link of set.links) {
      for (const gem of link.gems) {
        const name = (gem.name || '').trim();
        if (!name || GRANTED_NON_GEMS.has(name.toLowerCase())) continue;
        const key = gemKey(name, gem.support);
        counts.set(key, (counts.get(key) || 0) + 1);
        if (!needed.has(key)) {
          needed.set(key, { key, name, support: Boolean(gem.support), level: set.level, count: 0 });
        }
      }
    }
    for (const [key, count] of counts) {
      const item = needed.get(key);
      item.count = Math.max(item.count, count);
    }
  }
  return [...needed.values()];
}

function planGems(needed, className) {
  const data = gemsData.data;
  const owned = new Map(needed.map(item => [item.key, 0]));
  const actions = new Map(needed.map(item => [item.key, []]));
  const starts = [];

  const startKeys = data.start_gems[className] || {};
  for (const kind of ['start', 'chest']) {
    const key = startKeys[kind];
    if (key && owned.has(key) && !owned.get(key)) {
      owned.set(key, 1);
      actions.get(key).push({ kind, act: 1, count: 1 });
      starts.push({ key, kind, name: gemLabel(key) });
    }
  }

  const lastVendor = new Map();
  data.quests.forEach((quest, index) => {
    for (const offer of quest.offers) {
      for (const [key, info] of Object.entries(offer.vendor)) {
        if ((info.classes || []).includes(className)) lastVendor.set(key, index);
      }
    }
  });

  const steps = [];
  data.quests.forEach((quest, index) => {
    const act = quest.act;
    const step = { act, quest: quest.name, rewards: [], purchases: [] };

    /* награда: один нужный камень за предложение */
    for (const offer of quest.offers) {
      for (const item of needed) {
        if (owned.get(item.key)) continue;
        if (!(offer.rewards[item.key] || []).includes(className)) continue;
        owned.set(item.key, 1);
        const entry = {
          kind: 'reward', act, quest: quest.name, npc: offer.npc,
          key: item.key, name: item.name, support: item.support, count: 1,
        };
        actions.get(item.key).push(entry);
        step.rewards.push(entry);
        break;
      }
    }

    /* покупка: недостающие копии, отложенные — у последнего вендора */
    for (const offer of quest.offers) {
      for (const item of needed) {
        const missing = item.count - owned.get(item.key);
        const info = offer.vendor[item.key];
        if (missing <= 0 || !info || !(info.classes || []).includes(className)) continue;
        const deferred = (ACT_END_LEVEL[act] || ACT_END_LEVEL[10]) < item.level - PURCHASE_LEAD;
        if (deferred && lastVendor.get(item.key) !== index) continue;
        owned.set(item.key, owned.get(item.key) + missing);
        const entry = {
          kind: 'buy', act, quest: quest.name, npc: info.npc || offer.npc, deferred,
          key: item.key, name: item.name, support: item.support, count: missing, neededLevel: item.level,
          duplicate: owned.get(item.key) - missing > 0,
        };
        actions.get(item.key).push(entry);
        step.purchases.push(entry);
      }
    }
    if (step.rewards.length || step.purchases.length) steps.push(step);
  });

  const unavailable = [];
  for (const item of needed) {
    if (owned.get(item.key) >= item.count) continue;
    const base = item.name.includes(' of ') ? item.name.split(' of ')[0] : null;
    const reason = base && gemsData.known.has(gemKey(base)) ? 'divine_font' : 'trade';
    unavailable.push({ key: item.key, name: item.name, support: item.support, reason, base });
  }
  return { class: className, steps, unavailable, starts, total: needed.length };
}

function refreshGems() {
  if (state.tab !== 'gems') return;
  renderGems();
}

async function renderGems() {
  const host = $('#gemsList');
  const counter = $('#gemsCount');
  try {
    await ensureGemsData();
  } catch (error) {
    host.innerHTML = '<p class="gems-empty">Не удалось загрузить данные камней.</p>';
    return;
  }

  if (!build || !build.gemSets || !build.gemSets.length) {
    counter.textContent = '';
    host.innerHTML = '<p class="gems-empty">Импортируйте билд: «Импорт PoB» — план камней строится по связкам из Path of Building.</p>';
    return;
  }

  const className = normalizedClass(build.class);
  if (!className) {
    counter.textContent = '';
    host.innerHTML = `<p class="gems-empty">Класс «${escapeHtml(build.class || '—')}» не найден в справочнике камней.</p>`;
    return;
  }

  const plan = planGems(requiredGems(build.gemSets), className);
  gemsData.plan = plan;
  counter.textContent = `${className} · ${plan.total} камней`;

  const fragment = document.createDocumentFragment();
  if (plan.starts.length) {
    const block = document.createElement('div');
    block.className = 'gem-step starts';
    block.append(headRow('Старт', 'Акт 1 · Twilight Strand'));
    for (const item of plan.starts) {
      block.append(gemRow({ badge: 'Q', name: item.name, note: item.kind === 'chest' ? 'с сундука' : 'стартовый камень класса' }));
    }
    fragment.append(block);
  }

  for (const step of plan.steps) {
    const block = document.createElement('div');
    block.className = 'gem-step';
    block.append(headRow(`Акт ${step.act}`, step.quest));
    for (const entry of step.rewards) {
      block.append(gemRow({ badge: 'Q', name: entry.name, note: '' }));
    }
    for (const entry of step.purchases) {
      let note = entry.duplicate ? 'ещё копия' : '';
      if (entry.npc) note += `${note ? ' · ' : ''}у ${entry.npc}`;
      if (entry.count > 1) note += ` · ×${entry.count}`;
      if (entry.deferred) note += ` · нужен с ур. ${entry.neededLevel}`;
      block.append(gemRow({ badge: 'B', name: entry.name, note }));
    }
    fragment.append(block);
  }

  if (plan.unavailable.length) {
    const block = document.createElement('div');
    block.className = 'gem-step unavailable';
    block.append(headRow('Остальное', 'нет награды и ранней покупки'));
    for (const item of plan.unavailable) {
      const note = item.reason === 'divine_font'
        ? `Divine Font в Лабиринте (из ${item.base}) или трейд`
        : 'только дроп или трейд';
      block.append(gemRow({ badge: '·', name: item.name, note }));
    }
    fragment.append(block);
  }

  if (!plan.steps.length && !plan.unavailable.length) {
    fragment.append(Object.assign(document.createElement('p'), {
      className: 'gems-empty',
      textContent: 'В этом билде нет камней, требующих плана.',
    }));
  }

  host.replaceChildren(fragment);
}

function headRow(title, subtitle) {
  const head = document.createElement('div');
  head.className = 'gem-step-head';
  const pill = document.createElement('span');
  pill.className = 'act-pill';
  pill.textContent = title;
  const text = document.createElement('span');
  text.className = 'gem-step-quest';
  text.textContent = subtitle || '';
  head.append(pill, text);
  return head;
}

function gemRow({ badge, name, note }) {
  const row = document.createElement('div');
  row.className = `gem-row ${badge === 'Q' ? 'reward' : badge === 'B' ? 'buy' : ''}`;
  const mark = document.createElement('span');
  mark.className = 'gem-badge';
  mark.textContent = badge;
  const label = document.createElement('span');
  label.className = 'gem-name';
  label.textContent = name;
  const text = document.createElement('span');
  text.className = 'gem-note';
  text.textContent = note || '';
  row.append(mark, label, text);
  return row;
}

/* ───────────── вкладки, модалки, жесты ───────────── */

function setTab(tab) {
  state.tab = tab;
  save();
  document.querySelectorAll('.tabs button').forEach(btn => btn.classList.toggle('active', btn.dataset.tab === tab));
  $('#viewRoute').hidden = tab !== 'route';
  $('#viewTree').hidden = tab !== 'tree';
  $('#viewGems').hidden = tab !== 'gems';
  updateNextButton();
  if (tab === 'tree') {
    tree.load().then(() => {
      tree.resize();
      tree.applyPlan();
      if (build && tree.focusedCode !== build.code) {
        tree.focus();
        tree.focusedCode = build.code;
      } else if (!build && !tree.focusedCode) {
        tree.fit();
      }
    });
  }
  if (tab === 'gems') renderGems();
}

function bind() {
  $('#acts').addEventListener('click', (event) => {
    const btn = event.target.closest('.act');
    if (!btn) return;
    state.act = Number(btn.dataset.act);
    save();
    renderActs();
    renderSteps();
    $('#viewRoute').scrollTop = 0;
  });

  $('#steps').addEventListener('click', (event) => {
    if (event.target.closest('.extras-head')) {
      toggleExtras();
      return;
    }
    const li = event.target.closest('.step');
    if (li) toggleStep(li.dataset.id);
  });

  $('#nextBtn').addEventListener('click', () => {
    const id = nextStepId();
    if (!id) return;
    toggleStep(id);
    const now = document.querySelector('.step.now');
    if (now) now.scrollIntoView({ block: 'center', behavior: 'smooth' });
  });

  document.querySelectorAll('.lvl-btn').forEach(btn => {
    btn.addEventListener('click', () => setLevel(state.level + Number(btn.dataset.step)));
  });

  document.querySelectorAll('.tabs button').forEach(btn => {
    btn.addEventListener('click', () => setTab(btn.dataset.tab));
  });

  $('#menuBtn').addEventListener('click', () => { $('#menuModal').hidden = false; });
  $('#menuClose').addEventListener('click', () => { $('#menuModal').hidden = true; });
  $('#resetProgress').addEventListener('click', () => {
    if (!confirm('Сбросить отметки всех актов?')) return;
    state.done = {};
    state.splits = {};
    state.started = null;
    state.act = 0;
    save();
    renderAll();
    $('#menuModal').hidden = true;
  });
  $('#resetTimer').addEventListener('click', () => {
    state.started = Object.keys(state.done).length ? Date.now() : null;
    save();
    $('#menuModal').hidden = true;
  });

  $('#pobBtn').addEventListener('click', () => {
    $('#pobInput').value = state.build || '';
    $('#pobError').hidden = true;
    $('#pobModal').hidden = false;
  });
  $('#gemsPobBtn').addEventListener('click', () => {
    $('#pobInput').value = state.build || '';
    $('#pobError').hidden = true;
    $('#pobModal').hidden = false;
  });
  $('#pobCancel').addEventListener('click', () => { $('#pobModal').hidden = true; });
  $('#pobApply').addEventListener('click', async () => {
    const button = $('#pobApply');
    button.disabled = true;
    try {
      await loadBuild($('#pobInput').value);
      $('#pobModal').hidden = true;
      tree.applyPlan();
      tree.focus();
      tree.focusedCode = build.code;
      refreshGems();
    } catch (error) {
      $('#pobError').textContent = error.message || 'Не удалось прочитать билд';
      $('#pobError').hidden = false;
    } finally {
      button.disabled = false;
    }
  });
  $('#pobClear').addEventListener('click', () => {
    state.build = null;
    build = null;
    save();
    tree.plan = { taken: new Set(), next: new Set() };
    tree.applyPlan();
    tree.focusedCode = null;
    tree.fit();
    refreshGems();
    $('#pobModal').hidden = true;
  });

  $('#fitBtn').addEventListener('click', () => (build ? tree.focus() : tree.fit()));

  $('#nodeClose').addEventListener('click', () => { $('#nodeSheet').hidden = true; });

  window.addEventListener('resize', () => {
    if (state.tab === 'tree') tree.resize();
  });

  setupGestures();
}

function setupGestures() {
  const canvas = $('#canvas');
  let pointer = null;
  let last = null;
  let pinch = null;
  let moved = 0;

  canvas.addEventListener('pointerdown', (event) => {
    canvas.setPointerCapture(event.pointerId);
    moved = 0;
    if (pointer === null) {
      pointer = { id: event.pointerId, x: event.clientX, y: event.clientY };
    } else {
      pinch = {
        distance: Math.hypot(event.clientX - pointer.x, event.clientY - pointer.y),
        k: tree.view.k,
      };
    }
    last = { x: event.clientX, y: event.clientY };
  });

  canvas.addEventListener('pointermove', (event) => {
    if (!last) return;
    if (pinch && pointer && event.pointerId !== pointer.id) {
      const distance = Math.hypot(event.clientX - pointer.x, event.clientY - pointer.y);
      if (pinch.distance > 8) {
        const k = Math.max(0.004, Math.min(3, pinch.k * (distance / pinch.distance)));
        zoomAt(k, (pointer.x + event.clientX) / 2, (pointer.y + event.clientY) / 2);
      }
      return;
    }
    if (pointer && event.pointerId === pointer.id) {
      const dx = event.clientX - last.x;
      const dy = event.clientY - last.y;
      moved += Math.abs(dx) + Math.abs(dy);
      tree.view.x += dx;
      tree.view.y += dy;
      last = { x: event.clientX, y: event.clientY };
      tree.draw();
    }
  });

  const release = (event) => {
    if (pointer && event.pointerId === pointer.id) {
      if (moved < 6) {
        const id = tree.nodeAt(event.clientX, event.clientY);
        if (id) showNode(id);
      }
      pointer = null;
    }
    pinch = null;
    last = null;
  };

  canvas.addEventListener('pointerup', release);
  canvas.addEventListener('pointercancel', release);

  canvas.addEventListener('wheel', (event) => {
    event.preventDefault();
    zoomAt(tree.view.k * (event.deltaY < 0 ? 1.15 : 0.87), event.clientX, event.clientY);
  }, { passive: false });

  function zoomAt(k, clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    const px = clientX - rect.left;
    const py = clientY - rect.top;
    const before = tree.view;
    const worldX = (px - before.x) / before.k;
    const worldY = (py - before.y) / before.k;
    tree.view = { k, x: px - worldX * k, y: py - worldY * k };
    tree.draw();
  }
}

function showNode(id) {
  const node = tree.data.nodes[id];
  if (!node) return;
  $('#nodeName').textContent = node.n || (node.k === 3 ? 'Мастери' : `Нода ${id}`);
  const lines = [];
  const status = tree.plan.taken.has(id) ? 'взято' : tree.plan.next.has(id) ? 'следующая' : 'не взято';
  lines.push(`<p class="node-status">${status}</p>`);
  for (const stat of node.s || []) lines.push(`<p>${escapeHtml(stat)}</p>`);
  $('#nodeStats').innerHTML = lines.join('');
  $('#nodeSheet').hidden = false;
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (ch) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]
  ));
}

function renderAll() {
  $('#lvlNum').textContent = state.level;
  renderActs();
  renderProgress();
  renderSteps();
}

async function boot() {
  load();
  const response = await fetch('data/steps.json');
  acts = (await response.json()).acts;
  if (state.act >= acts.length) state.act = 0;
  if (!acts[state.act]) state.act = 0;

  if (state.build) {
    try {
      const xml = await decodePob(state.build);
      build = { code: state.build, ...parseBuildXml(xml) };
    } catch (e) {
      state.build = null;
      save();
    }
  }

  bind();
  renderAll();
  setTab(state.tab === 'tree' ? 'tree' : 'route');

  setInterval(() => {
    $('#timer').textContent = fmt(elapsed());
  }, 1000);
  $('#timer').textContent = fmt(elapsed());
}

boot();
