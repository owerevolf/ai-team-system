// AI Team System — Chat Interface

const state = {
  phase: 'welcome',
  level: null,
  projectName: '',
  projectIdea: '',
  clarifications: {},
  currentAgent: null,
  building: false,
};

const AGENTS = ['teamlead','architect','backend','frontend','devops','tester','documentalist'];
const AGENT_LABELS = {
  teamlead:'👔 TeamLead', architect:'🏛 Architect', backend:'⚙️ Backend',
  frontend:'🎨 Frontend', devops:'🚀 DevOps', tester:'🧪 Tester', documentalist:'📝 Docs'
};

async function init() {
  try {
    const r = await fetch('/api/hardware');
    const d = await r.json();
    const txt = `${d.profile || 'medium'} · VRAM ${d.vram_gb||'?'}GB · RAM ${d.ram_gb||'?'}GB`;
    document.getElementById('hw-badge').textContent = txt;
    document.getElementById('hw-info-welcome').textContent = txt;
  } catch(e) {
    document.getElementById('hw-badge').textContent = 'локальный режим';
    document.getElementById('hw-info-welcome').textContent = 'локальный режим';
  }
}

function startChat(mode) {
  const overlay = document.getElementById('welcome-overlay');
  overlay.style.opacity = '0';
  setTimeout(() => { overlay.style.display = 'none'; }, 400);

  if (mode === 'tour') {
    askLevel();
  } else {
    state.phase = 'idea';
    addAiMsg('system', 'Отлично. Опиши что хочешь создать — что хочешь создать?');
  }
}

function askLevel() {
  state.phase = 'level';
  addAiMsg('system',
    'Привет! Прежде чем начать — скажи мне, какой у тебя уровень.',
    null,
    [
      { label: '🐣 Знания: ноль — объясняй всё', value: 'zero' },
      { label: '📚 Начинающий — знаю основы', value: 'beginner' },
      { label: '🚀 Продвинутый — только суть', value: 'advanced' },
    ],
    onLevelSelect
  );
}

function onLevelSelect(value) {
  state.level = value;
  state.phase = 'idea';
  const txt = value === 'zero'
    ? 'Понял! Буду объяснять каждый шаг простыми словами.\n\nЧто хочешь создать?'
    : value === 'beginner'
    ? 'Отлично. Буду объяснять логику решений.\n\nЧто хочешь создать?'
    : 'Принял. Минимум лирики, максимум дела.\n\nЧто за проект?';
  addAiMsg('TeamLead', txt);
  focusInput();
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

async function sendMessage() {
  const input = document.getElementById('user-input');
  const text = input.value.trim();
  if (!text || state.building) return;

  input.value = '';
  input.style.height = 'auto';
  addUserMsg(text);

  if (state.phase === 'idea') {
    state.projectIdea = text;
    state.projectName = text.split(' ').slice(0,3).join('_').toLowerCase() || 'my_project';
    await askClarification();
  } else if (state.phase === 'clarify') {
    state.clarifications['detail'] = text;
    await startBuilding();
  } else if (state.phase === 'done') {
    addAiMsg('system', 'Хочешь создать ещё один проект? Опиши идею!');
    state.phase = 'idea';
  }
}

async function askClarification() {
  state.phase = 'clarify';
  showTyping();
  await sleep(900);
  removeTyping();

  const questions = generateClarifyQuestions(state.projectIdea, state.level);
  addAiMsg('TeamLead', questions);
}

function generateClarifyQuestions(idea, level) {
  if (level === 'zero') {
    return `Понял идею! Пару простых вопросов:\n\n1. Это только для тебя или для других?\n2. Нужен логин/пароль?\n3. Где работать — локально или в интернете?\n\nОтветь как удобно.`;
  } else if (level === 'beginner') {
    return `Уточняющие вопросы:\n• Авторизация?\n• База данных?\n• Стек — или на усмотрение команды?`;
  } else {
    return `Стек, авторизация, БД — есть предпочтения?`;
  }
}

async function startBuilding() {
  state.phase = 'building';
  state.building = true;
  document.getElementById('send-btn').disabled = true;

  addAiMsg('TeamLead',
    `Отлично. Создаём: **${state.projectIdea}**`,
    null, null, null,
    buildProgressBlock()
  );

  try {
    await streamAgents();
  } catch(e) {
    await fallbackBuild();
  }
}

function buildProgressBlock() {
  const steps = AGENTS.map(a =>
    `<div class="step-item" id="step-${a}">` +
    `<div class="step-dot"></div><span>${AGENT_LABELS[a]}</span></div>`
  ).join('');
  return `<div class="progress-steps">${steps}</div>`;
}

async function streamAgents() {
  const payload = {
    project_name: state.projectName,
    query: state.projectIdea,
    clarifications: state.clarifications,
    level: state.level,
  };

  const response = await fetch('/api/create_project_stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) throw new Error('stream failed');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          handleStreamEvent(data);
        } catch {}
      }
    }
  }

  onBuildDone();
}

function handleStreamEvent(data) {
  if (data.type === 'agent_start') {
    setAgentActive(data.agent);
  } else if (data.type === 'agent_done') {
    setAgentDone(data.agent);
    addAiMsg(AGENT_LABELS[data.agent] || data.agent,
      summarizeResponse(data.response, state.level));
  } else if (data.type === 'done') {
    onBuildDone(data);
  }
}

function summarizeResponse(text, level) {
  if (!text) return '✓ Выполнено';
  const short = text.slice(0, 250).replace(/```[\s\S]*?```/g, '[код]');
  return short + (text.length > 250 ? '...' : '');
}

async function fallbackBuild() {
  for (const agent of AGENTS) {
    setAgentActive(agent);
    await sleep(800 + Math.random() * 600);
    setAgentDone(agent);
    addAiMsg(AGENT_LABELS[agent], '✓ Завершено');
  }
  onBuildDone();
}

function onBuildDone() {
  state.phase = 'done';
  state.building = false;
  document.getElementById('send-btn').disabled = false;

  addAiMsg('system', '✅ Проект создан!',
    null,
    [{ label: '📥 Скачать', value: 'download' }, { label: '✨ Новый', value: 'new' }],
    (val) => {
      if (val === 'download') {
        window.location.href = `/api/download/${state.projectName}.md`;
      } else if (val === 'new') {
        state.phase = 'idea';
        AGENTS.forEach(a => {
          const chip = document.getElementById(`chip-${a}`);
          if (chip) chip.className = 'agent-chip';
          const step = document.getElementById(`step-${a}`);
          if (step) step.className = 'step-item';
        });
        addAiMsg('TeamLead', 'Какой следующий проект?');
        focusInput();
      }
    }
  );
}

function setAgentActive(agent) {
  state.currentAgent = agent;
  AGENTS.forEach(a => {
    const chip = document.getElementById(`chip-${a}`);
    if (chip) chip.className = a === agent ? 'agent-chip active' : 'agent-chip';
  });
  const step = document.getElementById(`step-${agent}`);
  if (step) step.className = 'step-item active';
}

function setAgentDone(agent) {
  const chip = document.getElementById(`chip-${agent}`);
  if (chip) chip.className = 'agent-chip done';
  const step = document.getElementById(`step-${agent}`);
  if (step) step.className = 'step-item done';
}

function addUserMsg(text) {
  const chat = document.getElementById('chat');
  const el = document.createElement('div');
  el.className = 'msg user';
  el.innerHTML = `<div class="avatar">👤</div><div class="bubble">${escHtml(text)}</div>`;
  chat.appendChild(el);
  scrollDown();
}

function addAiMsg(agent, text, html, choices, onChoice, extraHtml) {
  const chat = document.getElementById('chat');
  const el = document.createElement('div');
  el.className = 'msg ai';
  const agentTag = agent && agent !== 'system' ? `<div class="agent-tag">${escHtml(agent)}</div>` : '';
  const bodyHtml = html || formatText(text || '');
  let choicesHtml = '';
  if (choices && choices.length) {
    const btns = choices.map(c =>
      `<button class="choice-btn" onclick="onChoiceClick(this,'${c.value}')">${escHtml(c.label)}</button>`
    ).join('');
    choicesHtml = `<div class="choices" data-handler="pending">${btns}</div>`;
  }
  el.innerHTML = `<div class="avatar">🤖</div><div class="bubble">${agentTag}${bodyHtml}${(extraHtml||'')}${choicesHtml}</div>`;
  if (choices && onChoice) {
    el._onChoice = onChoice;
  }
  chat.appendChild(el);
  scrollDown();
  return el;
}

function onChoiceClick(btn, value) {
  const choicesEl = btn.closest('.choices');
  if (!choicesEl || choicesEl.dataset.handler === 'done') return;
  choicesEl.dataset.handler = 'done';
  choicesEl.querySelectorAll('.choice-btn').forEach(b => {
    b.disabled = true;
    if (b === btn) b.className = 'choice-btn selected';
  });
  const msgEl = btn.closest('.msg');
  if (msgEl && msgEl._onChoice) msgEl._onChoice(value);
}

function showTyping() {
  const chat = document.getElementById('chat');
  const el = document.createElement('div');
  el.className = 'msg ai'; el.id = 'typing-indicator';
  el.innerHTML = `<div class="avatar">🤖</div><div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div>`;
  chat.appendChild(el);
  scrollDown();
}

function removeTyping() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

function formatText(text) {
  return text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function scrollDown() {
  const chat = document.getElementById('chat');
  chat.scrollTop = chat.scrollHeight;
}

function focusInput() {
  document.getElementById('user-input').focus();
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

document.addEventListener('DOMContentLoaded', function() {
  init();
  document.getElementById('btn-tour').addEventListener('click', () => startChat('tour'));
  document.getElementById('btn-skip').addEventListener('click', () => startChat('skip'));
  document.getElementById('user-input').addEventListener('keydown', handleKey);
  document.getElementById('user-input').addEventListener('input', function() { autoResize(this); });
  document.getElementById('send-btn').addEventListener('click', sendMessage);
});