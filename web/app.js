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
  pausedAt: null, // мс, когда таймер встал на паузу
  pausedTotal: 0, // сколько мс таймер простоял на паузе
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
  if (!state.started) return 0;
  const now = state.pausedAt || Date.now();
  return Math.max(0, Math.round((now - state.started - (state.pausedTotal || 0)) / 1000));
}

function timerPaused() {
  return Boolean(state.pausedAt);
}

function togglePause() {
  if (!state.started) return;
  if (state.pausedAt) {
    state.pausedTotal = (state.pausedTotal || 0) + (Date.now() - state.pausedAt);
    state.pausedAt = null;
  } else {
    state.pausedAt = Date.now();
  }
  save();
  renderTimer();
}

function renderTimer() {
  const paused = timerPaused();
  $('#timer').textContent = fmt(elapsed());
  $('#timer').classList.toggle('paused', paused);
  $('#pauseBtn').textContent = paused ? '▶' : '❚❚';
  $('#pauseBtn').classList.toggle('active', paused);
  $('#pauseBtn').disabled = !state.started;
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

/* шапка акта: название и «пройдено / всего» */
function renderActHead(current) {
  const head = $('#actHead');
  if (!current) {
    head.innerHTML = '';
    return;
  }
  const passed = current.steps.filter((step) => state.done[step.id]).length;
  head.innerHTML = `<span class="act-head-name">${escapeHtml(current.name)}</span>`
    + `<span class="act-head-count">${passed} / ${current.steps.length}</span>`;
}

function renderSteps() {
  const act = acts[state.act];
  const host = $('#steps');
  host.innerHTML = '';
  renderActHead(act);
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
  if (state.done[id]) {
    clearFrom(id);
  } else {
    if (!state.started) state.started = Date.now();
    setProgressTo(id);
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
  renderTimer();
}

/* Прогресс — непрерывный курсор: всё до шага включительно пройдено, всё после — нет.
   Поэтому отметка любого шага подтягивает префикс и стирает хвост, а снятие
   галочки откатывает прогресс к предыдущему шагу. */
function setProgressTo(id) {
  const split = elapsed();
  let seen = false;
  for (const act of acts) {
    for (const step of act.steps) {
      if (step.id === id) {
        seen = true;
        if (!state.done[step.id]) {
          state.done[step.id] = 1;
          state.splits[step.id] = split;
        }
        continue;
      }
      if (!seen) {
        if (!state.done[step.id]) state.done[step.id] = 1;
      } else if (state.done[step.id]) {
        delete state.done[step.id];
        delete state.splits[step.id];
      }
    }
  }
}

function clearFrom(id) {
  let seen = false;
  for (const act of acts) {
    for (const step of act.steps) {
      if (step.id === id) seen = true;
      if (seen) {
        delete state.done[step.id];
        delete state.splits[step.id];
      }
    }
  }
}

/* ───────────── уровень ───────────── */

function setLevel(value) {
  state.level = Math.max(LEVEL_MIN, Math.min(LEVEL_MAX, value));
  $('#lvlNum').textContent = state.level;
  save();
  tree.invalidate();
  if (state.tab === 'gems') renderGemLinks();
}

/* ───────────── дерево ───────────── */

const QUEST_LEVELS = [5, 10, 19, 20, 27, 32, 38, 44, 46, 48, 50, 52, 54, 56, 58, 60, 61, 62, 64, 65, 67, 68, 68];

/* уровни лабиринтов: по 2 очка ассенданси за каждый */
const LAB_LEVELS = [33, 55, 68, 75];

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
  view: { k: 1, x: 0, y: 0 },
  plan: { taken: new Set(), next: new Set() },
  ascPlan: { taken: new Set(), next: new Set(), points: 0, total: 0, labs: 0 },
  cluster: { points: new Map(), edges: [], ids: new Set() },
  mode: 'main',        // 'main' | 'asc'
  mainIds: [],
  mainIdSet: new Set(),
  ascIds: new Map(),   // ассенданси -> [id]
  edgesByMode: new Map(),
  ascendancy: null,
  focusedCode: null,

  async load() {
    if (this.ready) return;
    const [treeResponse, clusterResponse] = await Promise.all([
      fetch('data/tree.json'),
      fetch('data/cluster_jewels.json').catch(() => null),
    ]);
    this.data = await treeResponse.json();
    try {
      this.clusterTemplates = clusterResponse ? await clusterResponse.json() : null;
    } catch (error) {
      this.clusterTemplates = null;
    }
    this.project();
    this.ready = true;
    this.resize();
    this.applyPlan();
    this.fit();
  },

  project() {
    const { groups, nodes, orbit_radii: radii, per_orbit: counts } = this.data;
    const mainIds = [];
    const ascIds = new Map();
    for (const [id, node] of Object.entries(nodes)) {
      const group = groups[String(node.g)];
      if (!group) continue;
      const orbit = node.o || 0;
      const radius = orbit < radii.length ? radii[orbit] : 0;
      const count = orbit < counts.length ? counts[orbit] : 1;
      const angle = orbitAngle(node.i || 0, count);
      this.points.set(id, [group[0] + radius * Math.sin(angle), group[1] - radius * Math.cos(angle)]);
      if (node.asc) {
        if (!ascIds.has(node.asc)) ascIds.set(node.asc, []);
        ascIds.get(node.asc).push(id);
      } else {
        mainIds.push(id);
      }
    }
    this.mainIds = mainIds;
    this.mainIdSet = new Set(mainIds);
    this.ascIds = ascIds;
    this.edgesByMode = new Map([['main', this.edgesFor(mainIds)]]);
    for (const [name, ids] of ascIds) this.edgesByMode.set(name, this.edgesFor(ids));
  },

  edgesFor(ids) {
    const members = new Set(ids);
    const edges = [];
    const seen = new Set();
    for (const id of ids) {
      for (const other of this.data.nodes[id].out || []) {
        if (!members.has(other) || other === id) continue;
        const key = id < other ? `${id}|${other}` : `${other}|${id}`;
        if (seen.has(key)) continue;
        seen.add(key);
        edges.push([id, other]);
      }
    }
    return edges;
  },

  currentIds() {
    if (this.mode === 'asc' && this.ascendancy) return this.ascIds.get(this.ascendancy) || [];
    return this.mainIds;
  },

  currentEdges() {
    return this.edgesByMode.get(this.mode === 'asc' && this.ascendancy ? this.ascendancy : 'main') || [];
  },

  planNodes() {
    const plan = this.mode === 'asc' ? this.ascPlan : this.plan;
    return [...plan.taken, ...plan.next];
  },

  /* кольца кластерных самоцветов: порт cluster_jewels.cluster_overlay.
     PoB пишет ноды кластера синтетическими id: биты 0-3 — слот в шаблоне,
     4-5 — размер, старшие — номер гнезда. */
  clusters() {
    const data = this.data;
    const templates = this.clusterTemplates;
    const empty = { points: new Map(), edges: [], ids: new Set() };
    if (!templates || !data.sockets) return empty;

    const specIds = new Set();
    for (const spec of this.specs()) for (const id of spec.nodes) specIds.add(id);

    const pools = new Map();
    for (const id of specIds) {
      const value = Number(id);
      if (!Number.isFinite(value) || value < 0x10000) continue;
      const base = value & ~0x3F;
      const size = (value >> 4) & 3;
      const key = `${base}:${size}`;
      if (!pools.has(key)) pools.set(key, { members: {} });
      pools.get(key).members[value & 0xF] = id;
    }
    if (!pools.size) return empty;

    const counts = data.per_orbit;
    const radii = data.orbit_radii;
    const out = { points: new Map(), edges: [], ids: new Set() };
    const ORBIT_TABLE = {
      '12:16': [0, 1, 3, 4, 5, 7, 8, 9, 11, 12, 13, 15],
      '6:16': [0, 3, 5, 8, 11, 13],
    };

    const templateToOrbit = (index, total, slots) => {
      if (total === slots) return index;
      const table = ORBIT_TABLE[`${total}:${slots}`];
      return table ? table[index] : Math.floor((index * slots) / total);
    };

    const ringSlot = (proxyId, size, templateIndex, slots) => {
      const offsets = (templates.orbit_offsets || {})[String(proxyId)];
      const offset = offsets ? offsets[String(size)] : undefined;
      if (offset === undefined) return null;
      const total = templates.sizes[String(size)].total;
      return templateToOrbit((Number(templateIndex) + offset) % total, total, slots);
    };

    const place = (group, orbit, orbitIndex) => {
      const center = data.proxy_groups[String(group)];
      if (!center) return null;
      const radius = radii[orbit] || 0;
      const count = counts[orbit] || 1;
      const angle = orbitAngle(orbitIndex, count);
      return [center[0] + radius * Math.sin(angle), center[1] - radius * Math.cos(angle)];
    };

    const build = (socketId, base, socketSize) => {
      let size = null;
      for (let candidate = socketSize; candidate >= 0; candidate -= 1) {
        if (pools.has(`${base}:${candidate}`)) { size = candidate; break; }
      }
      if (size === null) return;
      const socket = data.sockets[socketId];
      if (!socket) return;
      const proxy = data.proxies[socket.p];
      if (!proxy) return;
      const orbit = size + 1;
      const slots = counts[orbit];
      if (!slots || orbit >= radii.length) return;
      if (ringSlot(socket.p, size, 0, slots) === null) return;

      const template = templates.sizes[String(size)];
      const total = template.total;
      const pool = pools.get(`${base}:${size}`);
      pools.delete(`${base}:${size}`);
      const members = pool.members;
      const nested = {};

      /* JEWEL_ORDER: вложенные гнёзда разложены как 0, 2, 1 */
      (template.sockets || []).forEach((templateIndex, position) => {
        const jewelIndex = [0, 2, 1][position];
        const nestedId = (data.nested[String(proxy.g)] || {})[String(jewelIndex)];
        if (nestedId && specIds.has(nestedId) && members[templateIndex] === undefined) {
          members[templateIndex] = nestedId;
          nested[nestedId] = jewelIndex;
        }
      });

      for (const [templateIndex, nodeId] of Object.entries(members)) {
        let point = this.points.get(nodeId);
        if (!point) {
          const slot = ringSlot(socket.p, size, templateIndex, slots);
          if (slot === null) continue;
          point = place(proxy.g, orbit, slot);
          if (!point) continue;
          out.ids.add(nodeId);
        }
        out.points.set(nodeId, point);
      }

      const indexes = Object.keys(members).map(Number).sort((a, b) => a - b);
      const ring = [];
      for (let index = 0; index + 1 < indexes.length; index += 1) {
        ring.push([indexes[index], indexes[index + 1]]);
      }
      if (size > 0 && indexes.length > 2) {
        ring.push([indexes[indexes.length - 1], indexes[0]]);
        const gaps = ring.map(([a, b]) => (b - a + total) % total);
        const widest = Math.max(...gaps);
        if (gaps.filter((gap) => gap === widest).length === 1) ring.splice(gaps.indexOf(widest), 1);
      }
      for (const [a, b] of ring) {
        const first = members[a];
        const second = members[b];
        if (first && second && out.points.has(first) && out.points.has(second)) out.edges.push([first, second]);
      }
      if (members[0] && this.points.has(socketId)) {
        out.points.set(socketId, this.points.get(socketId));
        out.edges.push([members[0], socketId]);
      }

      for (const [nestedId, jewelIndex] of Object.entries(nested)) {
        const nestedSize = (data.sockets[nestedId] || {}).s ?? 0;
        build(nestedId, base + (nestedSize === 1 ? (jewelIndex << 9) : 0), nestedSize);
      }
    };

    for (const [id, socket] of Object.entries(data.sockets)) {
      if (socket.s === 2 && !socket.par) build(id, 0x10000 + (socket.i << 6), 2);
    }
    return out;
  },

  /* билд: один спек — режем по бюджету очков, несколько — берём ближайший по уровню */
  planFor(level) {
    const specs = this.specs();
    if (!specs.length) return { taken: new Set(), next: new Set(), refund: [] };
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
    const visible = (id) => this.mainIdSet.has(id);
    /* респек: ноды прошлого этапа, которых нет в текущем — их надо снять */
    let refund = [];
    if (stage) {
      const index = specs.indexOf(stage);
      const previous = specs[index - 1];
      if (previous) refund = previous.nodes.filter((id) => !taken.has(id) && visible(id));
    }
    return {
      taken: new Set([...taken].filter(visible)),
      next: new Set(upcoming.filter(visible)),
      refund,
      budget,
      stage,
    };
  },

  specs() {
    const build = state.build ? parseBuild(state.build) : null;
    return build ? build.specs : [];
  },

  applyPlan() {
    this.syncAscendancy();
    this.plan = this.planFor(state.level);
    this.ascPlan = this.ascPlanFor(state.level);
    this.cluster = this.mode === 'asc' ? { points: new Map(), edges: [], ids: new Set() } : this.clusters();
    this.updateLabels();
    this.draw();
  },

  syncAscendancy() {
    this.ascendancy = build && this.ascIds.has(build.ascendancy) ? build.ascendancy : null;
    if (!this.ascendancy) this.mode = 'main';
  },

  /* 2 очка ассенданси за лабиринт: 33 / 55 / 68 / 75 уровни */
  ascPlanFor(level) {
    const empty = { taken: new Set(), next: new Set(), points: 0, total: 0, labs: 0 };
    const name = this.ascendancy;
    if (!name) return empty;
    const members = new Set(this.ascIds.get(name) || []);
    const order = [];
    for (const spec of this.specs()) {
      for (const id of spec.nodes) {
        if (members.has(id) && !order.includes(id)) order.push(id);
      }
    }
    if (!order.length) return empty;
    const labs = LAB_LEVELS.filter(value => value <= level).length;
    const points = Math.min(2 * labs, order.length);
    return {
      taken: new Set(order.slice(0, points)),
      next: new Set(order.slice(points, points + 2)),
      points,
      total: order.length,
      labs,
    };
  },

  updateLabels() {
    const button = $('#ascBtn');
    button.hidden = !(build && this.ascendancy);
    button.textContent = this.mode === 'asc' ? 'К дереву' : 'Ассенданси';
    button.classList.toggle('active', this.mode === 'asc');
    if (!build) {
      $('#treeCount').textContent = 'билд не загружен';
      return;
    }
    if (this.mode === 'asc') {
      $('#treeCount').textContent = `${this.ascPlan.taken.size} из ${this.ascPlan.total} · лаб ${this.ascPlan.labs}`;
      return;
    }
    const count = this.plan.taken.size;
    const refund = (this.plan.refund || []).length;
    if (this.plan.stage) {
      $('#treeCount').textContent = `${count} нод · этап ур. ${this.plan.stage.level}${refund ? ` · снять ${refund}` : ''}`;
    }
    else $('#treeCount').textContent = `${count} из ${this.plan.budget} очков · ур. ${state.level}`;
    const legend = $('#legendRefund');
    if (legend) legend.hidden = !refund;
  },

  toggleMode() {
    if (!this.ascendancy) return;
    this.mode = this.mode === 'asc' ? 'main' : 'asc';
    this.applyPlan();
    this.focus();
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
    const points = this.currentIds().map(id => this.points.get(id)).filter(Boolean);
    let minX;
    let maxX;
    let minY;
    let maxY;
    if (points.length) {
      const xs = points.map(point => point[0]);
      const ys = points.map(point => point[1]);
      minX = Math.min(...xs);
      maxX = Math.max(...xs);
      minY = Math.min(...ys);
      maxY = Math.max(...ys);
    } else {
      ({ min_x: minX, max_x: maxX, min_y: minY, max_y: maxY } = this.data);
    }
    const worldW = Math.max(1, maxX - minX);
    const worldH = Math.max(1, maxY - minY);
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
    const asc = this.mode === 'asc';
    /* на экране ассенданси вписываем весь граф класса, а не только взятое */
    const source = asc ? this.currentIds() : this.planNodes();
    const points = source
      .map(id => this.points.get(id))
      .filter(Boolean);
    if (points.length < 2) return this.fit();
    const xs = points.map(point => point[0]);
    const ys = points.map(point => point[1]);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    /* экран ассенданси — компактный граф, ему нужен зум крупнее */
    const spanX = Math.max(asc ? 420 : 1400, maxX - minX);
    const spanY = Math.max(asc ? 420 : 1400, maxY - minY);
    const k = Math.min(asc ? 1.2 : 0.3, Math.min(this.width / spanX, this.height / spanY) * (asc ? 0.72 : 0.86));
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

    const plan = this.mode === 'asc' ? this.ascPlan : this.plan;
    const taken = plan.taken;
    const next = plan.next;
    const refund = new Set(this.mode === 'asc' ? [] : (plan.refund || []));
    const ids = this.currentIds();
    const pad = 40;

    if (this.mode === 'asc' && this.ascendancy) {
      ctx.fillStyle = 'rgba(224,185,111,.85)';
      ctx.font = '13px -apple-system, "Segoe UI", sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(`${this.ascendancy} · ${this.ascPlan.taken.size} из ${this.ascPlan.total}`, this.width / 2, 26);
      ctx.textAlign = 'left';
    }

    /* рёбра */
    ctx.lineWidth = 1;
    for (const [a, b] of this.currentEdges()) {
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
    const radius = this.mode === 'asc'
      ? { 0: 5.5, 1: 12.5, 2: 14, 3: 9, 4: 10, 5: 9 }
      : { 0: 3.2, 1: 6.4, 2: 7.6, 3: 5.4, 4: 6.2, 5: 5.4 };
    for (const id of ids) {
      const node = this.data.nodes[id];
      const point = this.points.get(id);
      if (!node || !point) continue;
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
      if (refund.has(id)) {
        ctx.beginPath();
        ctx.arc(sx, sy, r + 3.5, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(255,92,92,.9)';
        ctx.lineWidth = 1.8;
        ctx.stroke();
      }
    }

    /* кластерные самоцветы: кольца вокруг гнёзд */
    if (this.cluster.points.size) {
      ctx.lineWidth = 1;
      ctx.strokeStyle = 'rgba(55,232,103,.4)';
      for (const [a, b] of this.cluster.edges) {
        const pa = this.points.get(a) || this.cluster.points.get(a);
        const pb = this.points.get(b) || this.cluster.points.get(b);
        if (!pa || !pb) continue;
        const x1 = pa[0] * k + tx;
        const y1 = pa[1] * k + ty;
        const x2 = pb[0] * k + tx;
        const y2 = pb[1] * k + ty;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
      for (const point of this.cluster.points.values()) {
        const sx = point[0] * k + tx;
        const sy = point[1] * k + ty;
        if (sx < -pad || sx > this.width + pad || sy < -pad || sy > this.height + pad) continue;
        ctx.beginPath();
        ctx.arc(sx, sy, 5.4, 0, Math.PI * 2);
        ctx.fillStyle = '#37e867';
        ctx.fill();
        ctx.strokeStyle = 'rgba(10,25,15,.92)';
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }
  },

  nodeAt(clientX, clientY) {
    const rect = $('#canvas').getBoundingClientRect();
    const px = clientX - rect.left;
    const py = clientY - rect.top;
    let best = null;
    let bestDist = 18;
    for (const id of this.currentIds()) {
      const point = this.points.get(id);
      if (!point) continue;
      const [sx, sy] = this.toScreen(point[0], point[1]);
      const dist = Math.hypot(sx - px, sy - py);
      if (dist < bestDist) {
        bestDist = dist;
        best = id;
      }
    }
    for (const [id, point] of this.cluster.points) {
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

/* ── связки на текущем уровне: перенос gems/data.links_at_level ── */

const gemLevels = { ready: false, data: null };

async function ensureGemLevels() {
  if (gemLevels.ready) return;
  const response = await fetch('data/gem_levels.json');
  gemLevels.data = await response.json();
  gemLevels.ready = true;
}

/* максимальный уровень камня, который можно держать на этом уровне персонажа */
function effectiveGemLevel(name, characterLevel, importedLevel) {
  const key = (name || '').trim().toLowerCase();
  const table = gemLevels.data ? gemLevels.data[key] : null;
  const cap = Number(importedLevel);
  if (!table) return Number.isFinite(cap) && cap > 0 ? cap : null;
  const limit = Math.min(Number.isFinite(cap) && cap > 0 ? cap : 20, table.length);
  let best = null;
  for (let index = 0; index < limit; index += 1) {
    const requirement = table[index];
    if (requirement !== null && requirement !== undefined && requirement <= characterLevel) best = index + 1;
  }
  return best;
}

function gemRequirement(name) {
  const table = gemLevels.data ? gemLevels.data[(name || '').trim().toLowerCase()] : null;
  return table && table.length ? table[0] : null;
}

function linksAtLevel(links, characterLevel) {
  const result = [];
  for (const link of links || []) {
    const gems = [];
    for (const gem of link.gems || []) {
      const known = Boolean(gemLevels.data && gemLevels.data[(gem.name || '').trim().toLowerCase()]);
      const level = effectiveGemLevel(gem.name, characterLevel, gem.level);
      if (known && level === null) continue;
      gems.push({ ...gem, level: level === null ? gem.level : String(level) });
    }
    if (gems.length) result.push({ label: link.label, gems });
  }
  return result;
}

function gemSetFor(level) {
  const sets = (build && build.gemSets ? build.gemSets : []).slice().sort((a, b) => a.level - b.level);
  if (!sets.length) return null;
  let current = sets[0];
  for (const set of sets) if (set.level <= level) current = set;
  return current;
}

async function renderGemLinks() {
  const host = $('#gemsLinks');
  if (!host) return;
  if (!build || !build.gemSets || !build.gemSets.length) {
    host.innerHTML = '';
    return;
  }
  try {
    await ensureGemLevels();
  } catch (error) {
    host.innerHTML = '<p class="gems-empty">Не удалось загрузить уровни камней.</p>';
    return;
  }
  const set = gemSetFor(state.level);
  const links = linksAtLevel(set.links, state.level);
  const locked = [];
  for (const link of set.links || []) {
    for (const gem of link.gems || []) {
      const key = (gem.name || '').trim().toLowerCase();
      if (!gemLevels.data || !gemLevels.data[key]) continue;
      if (effectiveGemLevel(gem.name, state.level, gem.level) === null) {
        locked.push({ name: gem.name, requirement: gemRequirement(gem.name) });
      }
    }
  }

  const parts = [
    `<div class="links-head"><span>Связки на ур. ${state.level}</span>`
    + `<span class="links-note">${escapeHtml(set.title || '')}</span></div>`,
  ];
  if (!links.length) {
    parts.push('<p class="gems-empty">Из связок на этом уровне пока ничего не собрать.</p>');
  }
  for (const link of links) {
    const gems = link.gems.map((gem) => {
      const label = gemLabel(gemKey(gem.name, gem.support), gem.name);
      return `<span class="gem-pill${gem.support ? ' sup' : ''}">${escapeHtml(label)}`
        + `<b>${escapeHtml(gem.level || '—')}</b></span>`;
    }).join('');
    parts.push(`<div class="link-row">${gems}</div>`);
  }
  if (locked.length) {
    const names = locked.map((item) => `${escapeHtml(gemLabel(gemKey(item.name, false), item.name))}`
      + ` (с ур. ${item.requirement ?? '?'})`).join(', ');
    parts.push(`<p class="links-locked">Не влезает на этом уровне: ${names}</p>`);
  }
  host.innerHTML = parts.join('');
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
  renderGemLinks();
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

  $('#menuBtn').addEventListener('click', () => {
    $('#menuModal').hidden = false;
    showBuildStamp();
  });
  $('#menuClose').addEventListener('click', () => { $('#menuModal').hidden = true; });
  $('#resetProgress').addEventListener('click', () => {
    if (!confirm('Сбросить отметки всех актов?')) return;
    state.done = {};
    state.splits = {};
    state.started = null;
    state.pausedAt = null;
    state.pausedTotal = 0;
    state.act = 0;
    save();
    renderAll();
    renderTimer();
    $('#menuModal').hidden = true;
  });
  $('#resetTimer').addEventListener('click', () => {
    state.started = Object.keys(state.done).length ? Date.now() : null;
    state.pausedAt = null;
    state.pausedTotal = 0;
    save();
    renderTimer();
    $('#menuModal').hidden = true;
  });

  $('#pauseBtn').addEventListener('click', togglePause);

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
  $('#ascBtn').addEventListener('click', () => tree.toggleMode());

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
  const known = tree.data.nodes[id];
  const isCluster = !known && tree.cluster.points.has(id);
  if (!known && !isCluster) return;
  if (isCluster) {
    $('#nodeName').textContent = 'Пассив кластерного самоцвета';
    $('#nodeStats').innerHTML = '<p class="node-status">взято</p>'
      + '<p>Свойства задаёт сам самоцвет: в экспорте PoB есть только номер ноды.</p>';
    $('#nodeSheet').hidden = false;
    return;
  }
  $('#nodeName').textContent = known.n || (known.k === 3 ? 'Мастери' : `Нода ${id}`);
  const lines = [];
  const plan = tree.mode === 'asc' ? tree.ascPlan : tree.plan;
  const status = plan.taken.has(id) ? 'взято' : plan.next.has(id) ? 'следующая' : 'не взято';
  lines.push(`<p class="node-status">${status}</p>`);
  for (const stat of known.s || []) lines.push(`<p>${escapeHtml(stat)}</p>`);
  if (tree.mode === 'asc') {
    lines.push('<p class="node-hint">Ассенданси: 2 очка за лабиринт (ур. 33, 55, 68, 75).</p>');
  }
  $('#nodeStats').innerHTML = lines.join('');
  $('#nodeSheet').hidden = false;
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (ch) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]
  ));
}

/* какая версия app.js реально работает в этом окне — чтобы не спорить с кэшем */
async function showBuildStamp() {
  const line = $('#buildLine');
  line.textContent = 'сборка: …';
  try {
    const response = await fetch('app.js', { method: 'HEAD', cache: 'no-store' });
    const stamp = response.headers.get('last-modified');
    const size = response.headers.get('content-length');
    if (!stamp) {
      line.textContent = 'сборка: без заголовков (кэш?)';
      return;
    }
    const when = new Date(stamp);
    const date = when.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
    line.textContent = `сборка: ${date} · ${size ? Math.round(Number(size) / 1024) + ' КБ' : '—'}`;
  } catch (e) {
    line.textContent = 'сборка: нет связи с сервером';
  }
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
    if (!timerPaused()) renderTimer();
  }, 1000);
  renderTimer();
}

boot();
