// ═══════════════════════════════════════════════════════════════
// AI Team System — Welcome Page JavaScript
// ═══════════════════════════════════════════════════════════════

// ── STATE ──
const state = {
  phase: 'welcome',   // welcome → level → idea → clarify → building → done
  level: null,        // 'zero' | 'beginner' | 'advanced'
  projectName: '',
  projectIdea: '',
  lastUserMsg: '',    // последнее сообщение пользователя (для повторных запросов)
  clarifications: {},
  currentAgent: null,
  building: false,
};

const AGENTS = ['teamlead','architect','backend','frontend','devops','tester','documentalist'];
const AGENT_LABELS = {
  teamlead:'👔 TeamLead', architect:'🏛 Architect', backend:'⚙️ Backend',
  frontend:'🎨 Frontend', devops:'🚀 DevOps', tester:'🧪 Tester', documentalist:'📝 Docs'
};

// AbortController для отмены SSE потока при остановке
let buildAbortController = null;

// ── INIT ──
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

  // Load saved config
  try {
    const cfg = await (await fetch('/api/config')).json();
    if (cfg.openrouter_api_key_set) {
      document.getElementById('tab-btn-settings').innerHTML = '⚙️ Настройки ✅';
    }
    // Update mode badge
    var mode = cfg.ai_mode || 'local';
    var modeBadge = document.getElementById('mode-badge');
    if (modeBadge) {
      modeBadge.textContent = mode === 'local' ? '🏠 Local' : '☁️ Cloud';
      modeBadge.style.borderColor = mode === 'local' ? 'var(--success)' : 'var(--accent2)';
    }
    if (settingsData) settingsData.aiMode = mode;
  } catch(e) {}
}

// ── WELCOME ──
function startChat(mode) {
  const overlay = document.getElementById('welcome-overlay');
  overlay.classList.add('fade-out');
  overlay.style.opacity = '0';
  setTimeout(() => { overlay.style.display = 'none'; }, 500);

  if (mode === 'tour') {
    console.log('Starting tour...');
    startTour();
  } else {
    // skip — сразу к идее
    state.phase = 'idea';
    addAiMsg('system', 'Отлично. Опиши свою идею — что хочешь создать?');
  }
}

// ── TOUR MODE ──
const TOUR_STEPS = [
  {
    title: '👋 Добро пожаловать!',
    text: 'AI Team System — это команда из 7 AI-агентов которые создают проекты вместе.\n\n' +
          'Ты просто говоришь что хочешь — а команда делает всё остальное.\n\n' +
          'Давай познакомимся с каждым!',
  },
  {
    agent: 'teamlead',
    title: '👔 TeamLead — Командир',
    text: 'TeamLead — это как **прораб** на стройке.\n\n' +
          'Он:\n' +
          '• Слушает что ты хочешь\n' +
          '• Задаёт уточняющие вопросы\n' +
          '• Составляет план работы\n' +
          '• Раздаёт задачи команде\n\n' +
          '💡 *TeamLead первый начинает разговор и последний заканчивает.*',
  },
  {
    agent: 'architect',
    title: '🏛 Architect — Архитектор',
    text: 'Architect — это как **архитектор** который рисует план дома.\n\n' +
          'Он:\n' +
          '• Решает какие будут файлы и папки\n' +
          '• Продумывает как части связаны друг с другом\n' +
          '• Выбирает правильную структуру проекта\n\n' +
          '📐 *Без архитектора получилась бы куча файлов без порядка.*',
  },
  {
    agent: 'backend',
    title: '⚙️ Backend — Мозги',
    text: 'Backend — это **мозг** программы.\n\n' +
          'Он пишет то что работает "под капотом":\n' +
          '• Сервер который отвечает на запросы\n' +
          '• Базу данных где хранится информация\n' +
          '• Логику — как 2+2=4, проверка паролей и т.д.\n\n' +
          '🔧 *Backend — это всё что НЕ видно но работает.*',
  },
  {
    agent: 'frontend',
    title: '🎨 Frontend — Красота',
    text: 'Frontend — это **лицо** программы.\n\n' +
          'Он делает то что ты видишь:\n' +
          '• Кнопки которые нажимаешь\n' +
          '• Цвета и шрифты на экране\n' +
          '• Анимации когда всё двигается красиво\n\n' +
          '🎨 *Frontend = то что делает программу красивой и удобной.*',
  },
  {
    agent: 'devops',
    title: '🚀 DevOps — Инженер',
    text: 'DevOps — это **инженер** который делает так чтобы всё работало.\n\n' +
          'Он:\n' +
          '• Упаковывает проект в Docker (чтобы работал везде)\n' +
          '• Настраивает чтобы запускалось одной командой\n' +
          '• Делает инструкции по установке\n\n' +
          '📦 *DevOps = чтобы "у меня работает" стало "у всех работает".*',
  },
  {
    agent: 'tester',
    title: '🧪 Tester — Проверяльщик',
    text: 'Tester — это **контролёр качества**.\n\n' +
          'Он:\n' +
          '• Пишет тесты которые проверяют код\n' +
          '• Ищет ошибки пока ты их не нашёл\n' +
          '• Гарантирует что всё работает как надо\n\n' +
          '✅ *Tester = чтобы ты не получил баги и разочарование.*',
  },
  {
    agent: 'documentalist',
    title: '📝 Docs — Писатель',
    text: 'Documentalist — это **писатель инструкций**.\n\n' +
          'Он:\n' +
          '• Пишет README.md — как пользоваться проектом\n' +
          '• Объясняет что делает каждая часть\n' +
          '• Оставляет заметки для будущего\n\n' +
          '📖 *Docs = чтобы через месяц ты понял как всё работает.*',
  },
  {
    title: '🎉 Готово!',
    text: 'Теперь ты знаешь всю команду! 🎊\n\n' +
          'Все 7 агентов работают вместе чтобы создать твой проект.\n\n' +
          '**Что дальше?**\n' +
          '• Выбери свой уровень (объяснять много или мало)\n' +
          '• Расскажи свою идею\n' +
          '• Команда сделает всё остальное!\n\n' +
          'Готов начать?',
  },
];

function startTour() {
  state.phase = 'tour';
  state.tourStep = 0;
  showTourStep();
}

function showTourStep() {
  const step = TOUR_STEPS[state.tourStep];
  const isLast = state.tourStep === TOUR_STEPS.length - 1;
  const isFirst = state.tourStep === 0;

  const choices = [];
  if (!isLast) {
    choices.push({ label: '➡️ Дальше', value: 'next' });
  }
  if (!isFirst) {
    choices.push({ label: '⬅️ Назад', value: 'prev' });
  }
  if (isLast) {
    choices.push({ label: '🚀 Выбрать уровень', value: 'level' });
  }

  const html = `<strong>${step.title}</strong>\n\n${step.text}`;

  addAiMsg('system', null, html, choices, onTourChoice);

  // Подсветка текущего агента в панели
  if (step.agent) {
    setAgentActive(step.agent);
  } else if (isLast) {
    AGENTS.forEach(a => setAgentDone(a));
  }
}

function onTourChoice(value) {
  if (value === 'next') {
    state.tourStep++;
    showTourStep();
  } else if (value === 'prev') {
    state.tourStep--;
    showTourStep();
  } else if (value === 'level') {
    // Завершаем тур — просим выбрать уровень
    addUserMsg('Готов начать!');
    AGENTS.forEach(a => {
      const chip = document.getElementById(`chip-${a}`);
      if (chip) chip.className = 'agent-chip';
    });
    askLevel();
  }
}

// ── LEVEL SELECTION ──
function askLevel() {
  state.phase = 'level';
  addAiMsg('system',
    'Привет! Прежде чем начать — скажи мне, какой у тебя уровень. Это поможет мне правильно объяснять.',
    null,
    [
      { label: '🐣 Знания: ноль — объясняй всё', value: 'zero' },
      { label: '📚 Начинающий — знаю основы', value: 'beginner' },
      { label: '🚀 Продвинутый — только суть', value: 'advanced' },
    ],
    onLevelSelect
  );
}

function onLevelSelect(value, label) {
  state.level = value;
  addUserMsg(label);

  // После выбора уровня — просим идею
  state.phase = 'idea';
  state.projectIdea = '';
  state.projectName = '';
  
  addAiMsg('system', 'Отлично! Расскажи свою идею — что хочешь создать?');
  focusInput();
}

// ── USER INPUT ──
function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

async function sendMessage() {
  const input = document.getElementById('user-input');
  const text  = input.value.trim();
  if (!text || state.building) return;

  input.value = '';
  input.style.height = 'auto';
  addUserMsg(text);
  state.lastUserMsg = text;

  if (state.phase === 'idea') {
    state.projectIdea = text;
    state.projectName = text.split(' ').slice(0,3).join('_').toLowerCase() || 'my_project';
    state.phase = 'teamlead_wait';
    await callTeamLead();
  } else if (state.phase === 'teamlead_wait') {
    // Пользователь отвечает после первого ответа TeamLead
    // Если это согласие на сборку — сразу начинаем
    const lowText = text.toLowerCase().trim();
    if (['делаем', 'погнали', 'готов', 'да', 'давай', 'ок', 'окей', 'конечно', 'yes', 'start'].some(w => lowText.includes(w))) {
      // Пользователь хочет начать сборку
      await startBuilding();
    } else {
      // Это вопрос или уточнение — передаём TeamLead'у
      appendClarification(text);
      await callTeamLead();
    }
  } else if (state.phase === 'teamlead_questions') {
    // Пользователь задаёт вопрос TeamLead'у
    appendClarification(text);
    await callTeamLead();
  } else if (state.phase === 'clarify') {
    state.clarifications['detail'] = text;
    await startBuilding();
  } else if (state.phase === 'done') {
    // новый проект
    addAiMsg('system', 'Хочешь создать ещё один проект? Опиши идею!');
    state.phase = 'idea';
  } else {
    // Фоллбэк — отправляем как уточнение
    appendClarification(text);
    await callTeamLead();
  }
}

// Добавляет уточнение к projectIdea, храня только последние 500 символов уточнений
function appendClarification(text) {
  const prefix = state.projectIdea.split('\n\n')[0]; // оригинальная идея
  const existing = state.projectIdea.substring(prefix.length);
  const updated = existing + '\n\n' + text;
  // Храним оригинальную идею + последние 500 символов уточнений
  if (updated.length > 500) {
    state.projectIdea = prefix + '\n\n[...]' + updated.slice(-500);
  } else {
    state.projectIdea = prefix + updated;
  }
}

// ── TEAM LEAD QUERY ──
async function callTeamLead() {
  // isFirst = TeamLead ещё не отвечал в этой сессии
  const isFirst = !state.teamleadAnswered;
  state.teamleadAnswered = true;
  state.phase = 'teamlead_wait';

  showTyping();
  // Блокируем input пока Ollama думает
  const sendBtn = document.getElementById('send-btn');
  const inputEl = document.getElementById('user-input');
  if (sendBtn) sendBtn.disabled = true;
  if (inputEl) inputEl.disabled = true;


  try {
    // Формируем запрос в зависимости от того, первый раз или нет
    const query = isFirst
      ? `Ты впервые общаешься с пользователем. Идея проекта: ${state.projectIdea}\n\nПредставься кратко и предложи помощь.`
      : `КОНТЕКСТ: Ты уже представился пользователю.\nИдея проекта: ${state.projectIdea}\n\nПользователь написал: ${state.lastUserMsg}\n\nОТВЕТЬ НА ЗАПРОС — не представляйся снова.`;

    const response = await fetch('/api/teamlead_query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_name: state.projectName,
        query: query,
        level: state.level
      })
    });

    if (!response.ok) throw new Error('HTTP ' + response.status);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let gotResponse = false;

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

            if (data.type === 'agent_start') {
              setAgentActive(data.agent);
            } else if (data.type === 'agent_done') {
              gotResponse = true;
              removeTyping();
              setAgentDone(data.agent);
              const cleaned = cleanToolCall(data.response);
              const summary = summarizeResponse(cleaned, state.level);

              if (isFirst) {
                if (state.level === 'zero') {
                  // Zero-level: предлагаем демо или свою идею
                  addAiMsg('TeamLead', summary, null,
                    [
                      { label: '🎮 Да, давай пример!', value: 'demo' },
                      { label: '💡 У меня своя идея', value: 'questions' }
                    ],
                    onTeamleadChoice
                  );
                } else {
                  addAiMsg('TeamLead', summary, null,
                    [
                      { label: '❓ Есть вопросы', value: 'questions' },
                      { label: '✅ Делаем!', value: 'start_build' }
                    ],
                    onTeamleadChoice
                  );
                }
              } else {
                addAiMsg('TeamLead', summary, null, null, null);
                setTimeout(() => onTeamleadQuestionDone(), 500);
              }
              // Разблокируем input после ответа
              unlockInput();
            }
          } catch (e) {
            console.log('Parse error:', e);
          }
        }
      }
    }

    if (!gotResponse) {
      removeTyping();
      addAiMsg('system', '⚠️ TeamLead не ответил. Попробуй ещё раз.');
      unlockInput();
    }
  } catch (e) {
    removeTyping();
    const errMsg = friendlyError(e);
    if (errMsg) addAiMsg('system', errMsg);
    unlockInput();
    console.error('callTeamLead error:', e);
  }
}

function onTeamleadChoice(value) {
  if (value === 'demo') {
    // Zero-level: подставляем демо-проект "Супер Калькулятор"
    state.projectIdea = 'Супер Калькулятор — многофункциональный калькулятор с историей вычислений, конвертером валют и научными функциями';
    state.projectName = 'super_calculator';
    addUserMsg('Да, давай пример! Хочу Супер Калькулятор.');
    startBuilding();
  } else if (value === 'questions') {
    if (state.level === 'zero') {
      addAiMsg('TeamLead', 'Окей! Расскажи что хочешь создать — своими словами, не старайся говорить "правильно". Я пойму.');
      state.phase = 'idea';
    } else {
      addAiMsg('system', 'Задавай вопрос — что непонятно? Я объясню.');
      state.phase = 'teamlead_questions';
    }
    focusInput();
  } else if (value === 'start_build') {
    addUserMsg('Делаем!');
    startBuilding();
  }
}

// После вопросов — тоже можно начать билд
function onTeamleadQuestionDone() {
  addAiMsg('system', 'Готов продолжить? Тогда нажми "Делаем!" когда будешь готов.',
    null,
    [{ label: '✅ Делаем!', value: 'start_build' }],
    onTeamleadChoice
  );
}

// ── CLARIFICATION ──
async function askClarification() {
  state.phase = 'clarify';
  showTyping();

  try {
    // Генерируем вопросы через LLM
    const r = await fetch('/api/generate_clarify_questions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_idea: state.projectIdea,
        level: state.level,
      }),
    });

    removeTyping();

    if (r.ok) {
      const d = await r.json();
      const questions = d.questions || [];
      const questionsText = questions.map((q, i) => `${i + 1}. ${q}`).join('\n\n');
      addAiMsg('TeamLead', questionsText + '\n\nОтветь как тебе удобно — можно в одном сообщении.');
    } else {
      // Fallback на локальную генерацию
      removeTyping();
      const questions = generateClarifyQuestions(state.projectIdea, state.level);
      addAiMsg('TeamLead', questions);
    }
  } catch(e) {
    removeTyping();
    const questions = generateClarifyQuestions(state.projectIdea, state.level);
    addAiMsg('TeamLead', questions);
  }
}

function generateClarifyQuestions(idea, level) {
  if (level === 'zero') {
    return `Понял идею! Прежде чем мы начнём, пару простых вопросов:\n\n` +
      `1. Это только для тебя или для других людей тоже?\n` +
      `2. Нужно ли входить через логин/пароль?\n` +
      `3. Где будет работать — на твоём компьютере или в интернете?\n\n` +
      `Можешь ответить в одном сообщении, как тебе удобно.`;
  } else if (level === 'beginner') {
    return `Ясно. Уточняющие вопросы:\n\n` +
      `• Авторизация нужна?\n` +
      `• Данные хранить (база данных)?\n` +
      `• Предпочтения по стеку — или оставить на усмотрение команды?\n\n` +
      `Отвечай как хочешь.`;
  } else {
    return `Понял. Стек, авторизация, БД — есть предпочтения? Если нет — команда решит сама.`;
  }
}

// Человекочитаемые сообщения об ошибках
function friendlyError(e) {
  const msg = (e.message || '').toLowerCase();
  if (msg.includes('http 503') || msg.includes('unavailable') || msg.includes('ollama')) {
    return '🔌 Ollama не отвечает. Убедись что Ollama запущена (ollama serve).';
  }
  if (msg.includes('http 500') || msg.includes('internal server error')) {
    return '💥 Ошибка сервера. Попробуй перезапустить приложение.';
  }
  if (msg.includes('http 429') || msg.includes('rate limit') || msg.includes('too many')) {
    return '⏳ Слишком много запросов. Подожди 30 секунд и попробуй снова.';
  }
  if (msg.includes('http 401') || msg.includes('unauthorized') || msg.includes('api key')) {
    return '🔑 Проблема с API ключом. Проверь .env файл.';
  }
  if (msg.includes('network') || msg.includes('failed to fetch') || msg.includes('connection')) {
    return '🌐 Проблема с сетью. Проверь подключение к интернету.';
  }
  if (msg.includes('abort') || msg.includes('aborted')) {
    return ''; // Пользователь сам остановил — не показываем ошибку
  }
  return '⚠️ Ошибка: ' + (e.message || 'неизвестная ошибка');
}
async function startBuilding() {
  state.phase = 'building';
  state.building = true;
  document.getElementById('send-btn').disabled = true;
  document.getElementById('stop-btn').classList.add('visible');

  addAiMsg('TeamLead',
    `Отлично, всё понял. Передаю задачу команде.\n\nБудем создавать: **${state.projectIdea}**`,
    null, null, null,
    buildProgressBlock()
  );

  try {
    // SSE стриминг от агентов
    await streamAgents();
  } catch(e) {
    // Fallback: обычный запрос
    await fallbackBuild();
  }
}

function buildProgressBlock() {
  const steps = AGENTS.map(a =>
    `<div class="step-item" id="step-${a}">` +
    `<div class="step-dot"></div><span>${AGENT_LABELS[a]}</span>` +
    `</div>`
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

  // Создаём AbortController для возможности отмены
  buildAbortController = new AbortController();

  try {
    const response = await fetch('/api/create_project_stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: buildAbortController.signal,
    });

    if (!response.ok) throw new Error('stream failed');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let buildDoneCalled = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value, { stream: true });
      buffer += text;
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!state.building) {
          reader.cancel();
          return;
        }
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            handleStreamEvent(data, () => { buildDoneCalled = true; });
          } catch {}
        }
      }
    }

    if (!buildDoneCalled && state.building) onBuildDone();
  } catch (e) {
    if (e.name === 'AbortError') {
      console.log('Stream aborted by user');
      // User pressed stop — stopBuild() is handling UI cleanup
      // Just make sure we're in a clean state
      state.building = false;
    } else {
      console.log('Stream error:', e.message);
      if (state.building) {
        const errMsg = friendlyError(e);
        if (errMsg) addAiMsg('system', errMsg);
        onBuildDone();
      }
    }
  } finally {
    buildAbortController = null;
  }
}

function handleStreamEvent(data, markDone) {
  if (data.type === 'agent_start') {
    setAgentActive(data.agent);
  } else if (data.type === 'agent_chunk') {
    // чанки в реальном времени — можно добавить позже
  } else if (data.type === 'project_dir') {
    state.projectDir = data.path;
  } else if (data.type === 'agent_done') {
    setAgentDone(data.agent);
    const files = data.files && data.files.length
      ? `\n\n📄 **Создано файлов: ${data.files.length}**\n` + data.files.map(f => `• \`${f}\``).join('\n')
      : '';
    
    const summary = summarizeResponse(data.response, state.level);
    const fullMsg = summary + files;
    
    addAiMsg(AGENT_LABELS[data.agent] || data.agent, fullMsg);
  } else if (data.type === 'done') {
    markDone && markDone();
    onBuildDone(data);
  }
}

function cleanToolCall(text) {
  if (!text || !text.trim()) return '\u2713 Done';

  // 1. Remove <tool_call> XML tags
  text = text.replace(/<tool_call[^>]*>/g, '');
  text = text.replace(/<\/tool_call>/g, '');

  // 2. Replace JSON tool_call blocks with their content
  //    Strategy: find all {"tool":"..."} blocks using regex + brace counting
  //    and replace each with the value of its "content" field.
  let result = '';
  let i = 0;
  while (i < text.length) {
    // Look for start of a JSON object containing "tool"
    const remaining = text.slice(i);
    const m = remaining.match(/^\s*\{\s*"tool"\s*:/);
    if (!m) {
      result += text[i];
      i++;
      continue;
    }

    // Found a potential JSON tool block — extract the full object
    let start = i;
    let braceCount = 0;
    let inStr = false;
    let esc = false;
    let found = false;
    let j = i;

    while (j < text.length) {
      const ch = text[j];
      if (esc) { esc = false; j++; continue; }
      if (ch === '\\' && inStr) { esc = true; j++; continue; }
      if (ch === '"') { inStr = !inStr; j++; continue; }
      if (inStr) { j++; continue; }
      if (ch === '{') braceCount++;
      if (ch === '}') {
        braceCount--;
        if (braceCount === 0) {
          found = true;
          break;
        }
      }
      j++;
    }

    if (!found) {
      // Unclosed brace — skip this char
      result += text[i];
      i++;
      continue;
    }

    const jsonStr = text.slice(start, j + 1);
    try {
      const obj = JSON.parse(jsonStr);
      if (obj.content != null) {
        result += '\n' + String(obj.content) + '\n';
      } else if (obj.path && obj.content == null) {
        // create_file with only path — show path
        result += '\u2713 Created: ' + obj.path;
      } else if (obj.tool) {
        result += '\u2713 Tool: ' + obj.tool;
      } else {
        // Unknown JSON — skip it silently
      }
    } catch(e) {
      // JSON parse failed — try to extract "content" field via regex
      const contentMatch = jsonStr.match(/"content"\s*:\s*"((?:[^"\\]|\\.)*)"/);
      if (contentMatch) {
        result += '\n' + contentMatch[1].replace(/\\n/g, '\n').replace(/\\t/g, '\t').replace(/\\"/g, '"') + '\n';
      }
      // else: skip unparseable JSON silently
    }

    i = j + 1;
  }

  text = result;
  text = text.replace(/\n{3,}/g, '\n\n').trim();
  return text || '\u2713 Done';
}
function summarizeResponse(text, level) {
  if (!text) return '✓ Выполнено';
  text = cleanToolCall(text);

  // Показываем полный текст — без обрезки
  // Код скрываем только если он очень длинный (>2000 символов)
  if (text.length > 2000 && /```[\s\S]{500,}```/.test(text)) {
    const short = text.replace(/```[\s\S]{500,}```/g, '[код скрыт — скачай Markdown для полного кода]');
    return short;
  }

  return text;
}

async function fallbackBuild() {
  // Если SSE не работает — поочерёдно вызываем агентов
  for (const agent of AGENTS) {
    if (!state.building) break; // Проверка стопа
    setAgentActive(agent);
    await sleep(800 + Math.random() * 600);

    if (!state.building) break; // Проверка после await

    try {
      const r = await fetch('/api/agent/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_role: agent,
          query: `Создай проект '${state.projectName}': ${state.projectIdea}`,
          user_level: state.level || 'beginner',
        }),
      });
      const d = await r.json();
      setAgentDone(agent);
      addAiMsg(AGENT_LABELS[agent], summarizeResponse(d.response || '', state.level));
    } catch {
      setAgentDone(agent);
      addAiMsg(AGENT_LABELS[agent], '✓ Завершено');
    }
  }
  if (state.building) onBuildDone();
}

function onBuildDone(data) {
  if (state.phase === 'done') return; // защита от двойного вызова
  state.phase = 'done';
  state.building = false;

  // Разблокируем input
  unlockInput();

  document.getElementById('stop-btn').classList.remove('visible');

  const totalFiles = data && data.total_files ? data.total_files : 0;
  const projectDir = data && data.project_dir ? data.project_dir : (state.projectDir || '~/ai-team-projects');
  const mdName = `${state.projectName || 'project'}.md`;

  const summary = totalFiles > 0
    ? `✅ Проект создан! Файлов на диске: **${totalFiles}**\n📁 Папка: \`${projectDir}\`\n\nКоманда завершила работу. Что дальше?`
    : `✅ Проект создан!\n\nКоманда завершила работу. Что дальше?`;

  addAiMsg('system',
    summary,
    null,
    [
      { label: '📥 Скачать Markdown', value: 'download' },
      { label: '📂 Открыть папку',    value: 'open' },
      { label: '🔍 Что было создано?', value: 'explain' },
      { label: '✨ Новый проект',     value: 'new' },
    ],
    (value) => {
      if (value === 'download') {
        window.location.href = `/api/download/${mdName}`;
      } else if (value === 'open') {
        fetch('/api/open_folder', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({path: projectDir})
        });
      } else if (value === 'explain') {
        addUserMsg('Что было создано?');
        addAiMsg('TeamLead',
          `Команда создала структуру проекта "${state.projectIdea}":\n\n` +
          `• **TeamLead** — составил план и распределил задачи\n` +
          `• **Architect** — спроектировал архитектуру (как устроены части)\n` +
          `• **Backend** — написал серверную логику\n` +
          `• **Frontend** — создал интерфейс пользователя\n` +
          `• **DevOps** — подготовил Docker и инфраструктуру\n` +
          `• **Tester** — написал тесты\n` +
          `• **Docs** — оформил документацию\n\n` +
          `Все файлы в Markdown. Скачай и открой — там полный код.`
        );
        state.phase = 'done';
      } else if (value === 'new') {
        addUserMsg('Новый проект');
        state.phase = 'idea';
        state.projectIdea = '';
        state.teamleadAnswered = false;
        AGENTS.forEach(resetAgent);
        addAiMsg('TeamLead', 'Отлично! Какой следующий проект?');
        focusInput();
      }
    }
  );
}

// ── AGENT CHIPS ──
function setAgentActive(agent) {
  state.currentAgent = agent;
  AGENTS.forEach(a => {
    const chip = document.getElementById(`chip-${a}`);
    if (!chip) return;
    if (a === agent) chip.className = 'agent-chip active';
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

function resetAgent(agent) {
  const chip = document.getElementById(`chip-${agent}`);
  if (chip) chip.className = 'agent-chip';
  const step = document.getElementById(`step-${agent}`);
  if (step) { step.className = 'step-item'; }
}

// ── RENDER HELPERS ──
function addUserMsg(text) {
  const chat = document.getElementById('chat');
  const el = document.createElement('div');
  el.className = 'msg user';
  el.innerHTML =
    `<div class="avatar">👤</div>` +
    `<div class="bubble">${escHtml(text)}</div>`;
  chat.appendChild(el);
  scrollDown();
}

function addAiMsg(agent, text, html, choices, onChoice, extraHtml) {
  const chat = document.getElementById('chat');
  const el = document.createElement('div');
  el.className = 'msg ai';

  const agentTag = agent && agent !== 'system'
    ? `<div class="agent-tag">${escHtml(agent)}</div>` : '';

  const bodyHtml = html || formatText(text || '');

  let choicesHtml = '';
  if (choices && choices.length) {
    const btns = choices.map(c =>
      `<button class="choice-btn" onclick="onChoiceClick(this,'${c.value}')">` +
      `${escHtml(c.label)}</button>`
    ).join('');
    choicesHtml = `<div class="choices" data-handler="pending">${btns}</div>`;
  }

  el.innerHTML =
    `<div class="avatar">🤖</div>` +
    `<div class="bubble">` +
      agentTag +
      bodyHtml +
      (extraHtml || '') +
      choicesHtml +
    `</div>`;

  if (choices && onChoice) {
    el.dataset.onChoice = 'yes';
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
  if (msgEl && msgEl._onChoice) msgEl._onChoice(value, btn.textContent);
}

function showTyping() {
  const chat = document.getElementById('chat');
  const el = document.createElement('div');
  el.className = 'msg ai'; el.id = 'typing-indicator';
  el.innerHTML =
    `<div class="avatar">🤖</div>` +
    `<div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div>`;
  chat.appendChild(el);
  scrollDown();
}

function removeTyping() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

function unlockInput() {
  const sendBtn = document.getElementById('send-btn');
  const inputEl = document.getElementById('user-input');
  if (sendBtn && !state.building) sendBtn.disabled = false;
  if (inputEl) inputEl.disabled = false;
  if (inputEl) inputEl.focus();
}

function formatText(text) {
  return text
    // code blocks
    .replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => 
      `<div class="code-block"><strong>${lang || 'code'}:</strong><br><pre>${escHtml(code.trim())}</pre></div>`
    )
    // inline code
    .replace(/`([^`]+)`/g, '<code style="background:#1a1a1f;padding:2px 6px;border-radius:4px;font-size:12px;">$1</code>')
    // bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // newlines
    .replace(/\n/g, '<br>');
}

function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

function scrollDown() {
  const chat = document.getElementById('chat');
  chat.scrollTop = chat.scrollHeight;
}

function focusInput() {
  document.getElementById('user-input').focus();
}

function stopBuild() {
  state.building = false;

  // Отменяем SSE запрос немедленно
  if (buildAbortController) {
    buildAbortController.abort();
    buildAbortController = null;
  }

  // Разблокируем input
  unlockInput();

  document.getElementById('stop-btn').classList.remove('visible');
  removeTyping();

  const existingTyping = document.getElementById('typing-indicator');
  if (existingTyping) existingTyping.remove();

  addAiMsg('system', '⏹ Сборка остановлена пользователем.',
    null,
    [
      { label: '🔄 Начать заново', value: 'restart' },
    ],
    (value) => {
      if (value === 'restart') {
        addUserMsg('Начать заново');
        state.phase = 'idea';
        state.projectIdea = '';
        state.projectName = '';
        state.teamleadAnswered = false;
        state.building = false;
        AGENTS.forEach(resetAgent);
        addAiMsg('TeamLead', 'Ок! Какой проект хочешь создать?');
        focusInput();
      }
    }
  );
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── TABS & SETTINGS & CHAT FUNCTIONS ──
function switchTab(tabName) {
  document.querySelectorAll('.tab-content').forEach(function(el) { el.classList.remove('active'); });
  document.querySelectorAll('.tab-btn').forEach(function(el) { el.classList.remove('active'); });
  document.getElementById('tab-' + tabName).classList.add('active');
  document.getElementById('tab-btn-' + tabName).classList.add('active');
  var isChat = tabName === 'chat';
  document.getElementById('agents-bar').style.display = isChat ? 'flex' : 'none';
  document.getElementById('chat').style.display = isChat ? 'flex' : 'none';
  document.querySelector('.input-area').style.display = isChat ? 'flex' : 'none';
  document.getElementById('chat-functions').style.display = isChat ? 'flex' : 'none';
  if (tabName === 'settings') loadSettings();
  if (tabName === 'kanban') renderKanban();
}

var settingsData = null;

function loadSettings() {
  var container = document.getElementById('settings-content');
  container.innerHTML = '<p style="color:var(--muted)">Загрузка...</p>';
  Promise.all([
    fetch('/api/providers?force_refresh=true').then(function(r) { return r.json(); }),
    fetch('/api/agents/config').then(function(r) { return r.json(); }),
    fetch('/api/config').then(function(r) { return r.json(); }),
    fetch('/api/health/providers').then(function(r) { return r.json(); }).catch(function() { return {}; })
  ]).then(function(results) {
    settingsData = { providers: results[0], agents: results[1], config: results[2], health: results[3].health || {} };
    renderSettings();
  }).catch(function(e) {
    container.innerHTML = '<p style="color:#ef4444">Ошибка: ' + e.message + '</p>';
  });
}

function renderSettings() {
  var container = document.getElementById('settings-content');
  var providers = settingsData.providers;
  var agents = settingsData.agents;
  var config = settingsData.config;
  var health = settingsData.health || {};
  var h = '<h2>⚙️ Настройки провайдеров</h2><p>Выбери провайдера и модели для каждого агента.</p>';
  
  // AI Mode toggle
  var currentMode = config.ai_mode || 'local';
  var localSelected = currentMode === 'local' ? 'selected' : '';
  var cloudSelected = currentMode === 'cloud' ? 'selected' : '';
  h += '<h3 style="font-size:14px;margin:20px 0 12px;">🔄 Режим работы</h3>';
  h += '<div style="display:flex;gap:8px;margin-bottom:20px;">';
  h += '<button class="mode-btn ' + localSelected + '" onclick="setAiMode(\'local\')" id="mode-btn-local" style="flex:1;padding:12px;border:1px solid var(--border);border-radius:8px;background:var(--surface);color:var(--text);font-family:\'JetBrains Mono\',monospace;font-size:12px;cursor:pointer;transition:all .2s;">🏠 Local first<div style="font-size:10px;color:var(--muted);margin-top:4px;">Ollama → Cloud fallback</div></button>';
  h += '<button class="mode-btn ' + cloudSelected + '" onclick="setAiMode(\'cloud\')" id="mode-btn-cloud" style="flex:1;padding:12px;border:1px solid var(--border);border-radius:8px;background:var(--surface);color:var(--text);font-family:\'JetBrains Mono\',monospace;font-size:12px;cursor:pointer;transition:all .2s;">☁️ Cloud first<div style="font-size:10px;color:var(--muted);margin-top:4px;">OpenRouter → Ollama fallback</div></button>';
  h += '</div>';
  
  h += '<h3 style="font-size:14px;margin:20px 0 12px;">📡 Провайдеры</h3><div class="provider-grid">';
  for (var pid in providers) {
    var info = providers[pid];
    var sc = info.is_available ? 'available' : 'unavailable';
    var st = info.is_available ? '✅ Доступен' : '❌ Недоступен';
    h += '<div class="provider-card" onclick="selectProvider(\'' + pid + '\')" id="provider-card-' + pid + '"><div class="provider-name">' + info.name + '</div><div class="provider-desc">' + info.description + '</div><div class="provider-status ' + sc + '">' + st + ' · ' + info.free_models_count + ' бесплатных</div></div>';
  }
  h += '</div>';
  // Provider health status
  var health = settingsData.health || {};
  h += '<h3 style="font-size:14px;margin:20px 0 12px;">\u{1f7a2} Здоровье провайдеров</h3>';
  h += '<div style="margin-bottom:20px;">';
  for (var pid in providers) {
    var info = providers[pid];
    var healthInfo = health[pid] || {};
    var statusIcon = info.is_available ? '✅' : '❌';
    var cooldownWarning = healthInfo.in_cooldown ? ' <span style="color:#facc15;">(cooldown)</span>' : '';
    var failuresInfo = healthInfo.recent_failures ? ' <span style="color:#ef4444;">(' + healthInfo.recent_failures + ' ошибок)</span>' : '';
    h += '<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border);font-size:11px;">';
    h += '<span>' + statusIcon + '</span>';
    h += '<span style="color:var(--text);flex:1;">' + info.name + cooldownWarning + failuresInfo + '</span>';
    h += '</div>';
  }
  h += '</div>';
  
  h += '<h3 style="font-size:14px;margin:20px 0 12px;">🔑 API ключ</h3><div style="margin-bottom:20px;"><input type="password" id="api-key-input" placeholder="Вставь API ключ (sk-or-v1-...)" style="width:100%;padding:10px 14px;border:1px solid var(--border);border-radius:8px;background:var(--surface);color:var(--text);font-family:\'JetBrains Mono\',monospace;font-size:12px;"><p style="font-size:11px;color:var(--muted);margin-top:6px;">🔗 <a href="https://openrouter.ai/keys" target="_blank">Получить ключ OpenRouter</a> · 🔗 <a href="https://ollama.com/download" target="_blank">Установить Ollama</a></p></div>';
  // OmniRoute config
  var omnirouteUrl = config.omniroute_url || 'http://localhost:21000/v1';
  var omnirouteKey = config.omniroute_api_key_set ? '••••••••' : '';
  h += '<h3 style="font-size:14px;margin:20px 0 12px;">🇷🇺 OmniRoute</h3><div style="margin-bottom:20px;"><input type="text" id="omniroute-url-input" placeholder="URL (http://localhost:21000/v1)" value="' + omnirouteUrl + '" style="width:100%;padding:10px 14px;border:1px solid var(--border);border-radius:8px;background:var(--surface);color:var(--text);font-family:\'JetBrains Mono\',monospace;font-size:12px;margin-bottom:8px;"><input type="password" id="omniroute-key-input" placeholder="API ключ (опционально)" value="' + omnirouteKey + '" style="width:100%;padding:10px 14px;border:1px solid var(--border);border-radius:8px;background:var(--surface);color:var(--text);font-family:\'JetBrains Mono\',monospace;font-size:12px;"><p style="font-size:11px;color:var(--muted);margin-top:6px;">🔗 <a href="https://omniroute.online" target="_blank">OmniRoute</a> — российский агрегатор AI моделей</p></div>';
  
  // MCP Servers config
  var mcpServers = config.mcp_servers || [];
  h += '<h3 style="font-size:14px;margin:20px 0 12px;">🔌 MCP серверы</h3>';
  h += '<p style="font-size:11px;color:var(--muted);margin-bottom:12px;">Model Context Protocol — подключение внешних инструментов (filesystem, github, sqlite и др.)</p>';
  h += '<div id="mcp-servers-list" style="margin-bottom:16px;">';
  if (mcpServers.length === 0) {
    h += '<p style="font-size:11px;color:var(--muted);">Нет настроенных MCP серверов. Добавьте серверы в config/mcp_servers.json</p>';
  } else {
    for (var m = 0; m < mcpServers.length; m++) {
      var srv = mcpServers[m];
      var srvEnabled = srv.enabled ? '✅' : '❌';
      h += '<div style="display:flex;align-items:center;gap:8px;padding:8px;background:var(--surface);border:1px solid var(--border);border-radius:6px;margin-bottom:6px;">';
      h += '<span>' + srvEnabled + '</span>';
      h += '<span style="font-size:12px;color:var(--text);flex:1;">' + (srv.name || 'unnamed') + '</span>';
      h += '<span style="font-size:10px;color:var(--muted);">' + (srv.transport || 'stdio') + '</span>';
      h += '</div>';
    }
  }
  h += '</div>';
  h += '<div style="margin-bottom:20px;"><input type="text" id="mcp-server-name" placeholder="Имя сервера" style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:6px;background:var(--surface);color:var(--text);font-family:\'JetBrains Mono\',monospace;font-size:11px;margin-bottom:6px;"><input type="text" id="mcp-server-command" placeholder="Команда (npx, python, ...)" style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:6px;background:var(--surface);color:var(--text);font-family:\'JetBrains Mono\',monospace;font-size:11px;margin-bottom:6px;"><input type="text" id="mcp-server-args" placeholder="Аргументы (через запятую)" style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:6px;background:var(--surface);color:var(--text);font-family:\'JetBrains Mono\',monospace;font-size:11px;margin-bottom:6px;"><select id="mcp-server-transport" style="width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:6px;background:var(--surface);color:var(--text);font-family:\'JetBrains Mono\',monospace;font-size:11px;margin-bottom:6px;"><option value="stdio">stdio</option><option value="http">http</option></select></div>';
  h += '<button class="btn-secondary" onclick="addMcpServer()" style="margin-right:8px;">➕ Добавить</button>';
  h += '<button class="btn-secondary" onclick="reloadMcpServers()">🔄 Перезагрузить</button>';
  
  h += '<h3 style="font-size:14px;margin:20px 0 12px;">🤖 Модели агентов</h3>';
  for (var i = 0; i < agents.agents.length; i++) {
    var agent = agents.agents[i];
    h += '<div style="margin-bottom:16px;"><div style="font-size:12px;font-weight:600;color:var(--text);margin-bottom:8px;">' + agent.name.toUpperCase() + ' <span style="font-size:10px;color:var(--muted);font-weight:400;">— ' + agent.description + '</span></div><div class="model-list" id="models-' + agent.name + '">';
    for (var j = 0; j < Math.min(agent.available_models.length, 5); j++) {
      var model = agent.available_models[j];
      var isFree = model.id.indexOf(':free') !== -1 ? '<span class="model-badge free">FREE</span>' : '';
      var strengthBadge = '<span class="model-badge ' + model.strength + '">' + model.strength + '</span>';
      h += '<div class="model-item" onclick="selectModel(\'' + agent.name + '\',\'' + model.id + '\')"><div><div class="model-name">' + (model.name || model.id) + '</div><div class="model-id">' + model.id + '</div><div class="model-meta">' + isFree + strengthBadge + ' · ctx: ' + (model.context_length ? (model.context_length >= 1000000 ? (model.context_length/1000000).toFixed(1) + 'M' : (model.context_length/1000).toFixed(0) + 'K') : '?') + '</div></div></div>';
    }
    h += '</div></div>';
  }
  h += '<div class="settings-actions"><button class="btn-save" onclick="saveConfig()">💾 Сохранить</button><button class="btn-secondary" onclick="testConnection()">🔌 Проверить</button><button class="btn-secondary" onclick="loadSettings()">🔄 Обновить</button></div><div id="settings-status" style="margin-top:12px;font-size:12px;"></div>';
  container.innerHTML = h;
}

function setAiMode(mode) {
  settingsData.aiMode = mode;
  var localBtn = document.getElementById('mode-btn-local');
  var cloudBtn = document.getElementById('mode-btn-cloud');
  if (mode === 'local') {
    localBtn.classList.add('selected');
    cloudBtn.classList.remove('selected');
  } else {
    cloudBtn.classList.add('selected');
    localBtn.classList.remove('selected');
  }
}

function selectProvider(pid) {
  var cards = document.querySelectorAll('.provider-card');
  for (var i = 0; i < cards.length; i++) { cards[i].classList.remove('selected'); }
  document.getElementById('provider-card-' + pid).classList.add('selected');
  settingsData.selectedProvider = pid;
}

function selectModel(agentName, modelId) {
  var items = document.querySelectorAll('#models-' + agentName + ' .model-item');
  for (var i = 0; i < items.length; i++) { items[i].classList.remove('selected'); }
  event.currentTarget.classList.add('selected');
  if (!settingsData.selectedModels) settingsData.selectedModels = {};
  settingsData.selectedModels[agentName] = modelId;
}

function saveConfig() {
  var status = document.getElementById('settings-status');
  status.textContent = 'Сохранение...';
  var agents = {};
  if (settingsData.selectedModels) {
    for (var a in settingsData.selectedModels) {
      agents[a] = { provider: settingsData.selectedProvider || 'openrouter', model: settingsData.selectedModels[a] };
    }
  }
  var apiKey = '';
  var keyInput = document.getElementById('api-key-input');
  if (keyInput) apiKey = keyInput.value || '';
  var omnirouteUrl = '';
  var omnirouteKey = '';
  var omnirouteUrlInput = document.getElementById('omniroute-url-input');
  var omnirouteKeyInput = document.getElementById('omniroute-key-input');
  if (omnirouteUrlInput) omnirouteUrl = omnirouteUrlInput.value || '';
  if (omnirouteKeyInput) omnirouteKey = omnirouteKeyInput.value || '';
  fetch('/api/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ openrouter_api_key: apiKey, agents: agents, ai_mode: settingsData.aiMode || 'local', omniroute_url: omnirouteUrl, omniroute_api_key: omnirouteKey }) })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var msg = '<span style="color:var(--success);">✅ ' + data.message + '</span>';
      if (data.applied && data.applied.length > 0) {
        msg += '<br><span style="color:var(--muted);font-size:11px;">Применено для: ' + data.applied.join(', ') + '</span>';
      }
      status.innerHTML = msg;
    })
    .catch(function(e) { status.innerHTML = '<span style="color:#ef4444;">❌ ' + e.message + '</span>'; });
}

function testConnection() {
  var status = document.getElementById('settings-status');
  status.textContent = 'Проверка...';
  fetch('/api/status')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var r = '<strong>Статус провайдеров:</strong><br>';
      for (var pid in data.providers) {
        r += (data.providers[pid].available ? '✅' : '❌') + ' ' + pid + ': ' + data.providers[pid].free_models + ' моделей<br>';
      }
      status.innerHTML = r;
    })
    .catch(function(e) { status.innerHTML = '<span style="color:#ef4444;">❌ ' + e.message + '</span>'; });
}

function clearChat() {
  if (confirm('Очистить чат?')) {
    document.getElementById('chat').innerHTML = '';
    state.projectIdea = ''; state.projectName = ''; state.lastUserMsg = '';
    state.teamleadAnswered = false; state.phase = 'idea';
    addAiMsg('system', 'Чат очищен. Опиши свою идею!');
  }
}

function exportChat() {
  var msgs = document.querySelectorAll('.chat-area .msg');
  var md = '# AI Team System — Экспорт чата\n\n---\n\n';
  for (var i = 0; i < msgs.length; i++) {
    var m = msgs[i];
    var text = m.querySelector('.bubble') ? m.querySelector('.bubble').innerText : '';
    md += '**' + (m.classList.contains('user') ? '👤' : '🤖') + ':**\n' + text + '\n\n';
  }
  var blob = new Blob([md], { type: 'text/markdown' });
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a'); a.href = url; a.download = 'chat-' + Date.now() + '.md'; a.click();
  URL.revokeObjectURL(url);
}

function newProject() { clearChat(); switchTab('chat'); }

// ── KANBAN ──
var kanbanData = {
  columns: [
    { id: 'todo', title: '📋 Ожидание', color: '#6b6b7e' },
    { id: 'in_progress', title: '🔄 В работе', color: '#7c6ef5' },
    { id: 'done', title: '✅ Готово', color: '#4ade80' },
    { id: 'failed', title: '❌ Ошибка', color: '#ef4444' },
  ],
  tasks: []
};

function renderKanban() {
  var board = document.getElementById('kanban-board');
  if (!board) return;
  var h = '';
  for (var col of kanbanData.columns) {
    var colTasks = kanbanData.tasks.filter(t => t.status === col.id);
    h += '<div class="kanban-column" style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px;min-height:200px;">';
    h += '<div style="font-size:12px;font-weight:600;color:' + col.color + ';margin-bottom:12px;">' + col.title + ' (' + colTasks.length + ')</div>';
    for (var task of colTasks) {
      h += '<div class="kanban-task" style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px;margin-bottom:8px;font-size:11px;">';
      h += '<div style="font-weight:600;color:var(--text);">' + task.agent + '</div>';
      h += '<div style="color:var(--muted);margin-top:4px;">' + task.title + '</div>';
      if (task.time) h += '<div style="color:var(--muted);margin-top:4px;font-size:10px;">⏱ ' + task.time + '</div>';
      h += '</div>';
    }
    h += '</div>';
  }
  board.innerHTML = h;
  
  // Update task list
  var taskList = document.getElementById('kanban-task-list');
  if (taskList && kanbanData.tasks.length > 0) {
    var listHtml = '';
    for (var task of kanbanData.tasks) {
      var statusIcon = task.status === 'done' ? '✅' : task.status === 'in_progress' ? '🔄' : task.status === 'failed' ? '❌' : '📋';
      listHtml += '<div style="display:flex;align-items:center;gap:8px;padding:8px;background:var(--surface);border-radius:6px;border:1px solid var(--border);">';
      listHtml += '<span>' + statusIcon + '</span>';
      listHtml += '<span style="font-size:12px;color:var(--text);flex:1;">' + task.agent + ': ' + task.title + '</span>';
      if (task.time) listHtml += '<span style="font-size:10px;color:var(--muted);">' + task.time + '</span>';
      listHtml += '</div>';
    }
    taskList.innerHTML = listHtml;
  }
}

function addKanbanTask(agent, title, status) {
  var existing = kanbanData.tasks.find(t => t.agent === agent && t.title === title);
  if (existing) {
    existing.status = status;
    existing.time = new Date().toLocaleTimeString('ru-RU');
  } else {
    kanbanData.tasks.push({
      agent: agent,
      title: title,
      status: status || 'todo',
      time: new Date().toLocaleTimeString('ru-RU')
    });
  }
  renderKanban();
}

function clearKanban() {
  kanbanData.tasks = [];
  renderKanban();
  var taskList = document.getElementById('kanban-task-list');
  if (taskList) taskList.innerHTML = '<p style="color:var(--muted);font-size:12px;">Задачи появятся при запуске сборки проекта.</p>';
}

function exportKanban() {
  var md = '# AI Team System — Канбан доска\n\n';
  for (var col of kanbanData.columns) {
    var colTasks = kanbanData.tasks.filter(t => t.status === col.id);
    md += '## ' + col.title + '\n\n';
    for (var task of colTasks) {
      md += '- **' + task.agent + '**: ' + task.title;
      if (task.time) md += ' (' + task.time + ')';
      md += '\n';
    }
    md += '\n';
  }
  var blob = new Blob([md], { type: 'text/markdown' });
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a'); a.href = url; a.download = 'kanban-' + Date.now() + '.md'; a.click();
  URL.revokeObjectURL(url);
}

// Auto-update kanban during build
var originalSetAgentActive = setAgentActive;
setAgentActive = function(agent) {
  originalSetAgentActive(agent);
  addKanbanTask(AGENT_LABELS[agent] || agent, 'Работает...', 'in_progress');
};

var originalSetAgentDone = setAgentDone;
setAgentDone = function(agent) {
  originalSetAgentDone(agent);
  addKanbanTask(AGENT_LABELS[agent] || agent, 'Завершено', 'done');
};


// ── MCP SERVERS ──
function addMcpServer() {
  var name = document.getElementById('mcp-server-name').value.trim();
  var command = document.getElementById('mcp-server-command').value.trim();
  var args = document.getElementById('mcp-server-args').value.trim();
  var transport = document.getElementById('mcp-server-transport').value;
  
  if (!name || !command) {
    alert('Заполните имя и команду');
    return;
  }
  
  // Add to config and save
  var status = document.getElementById('settings-status');
  status.textContent = 'Сохранение...';
  
  fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mcp_add_server: { name: name, command: command, args: args.split(','), transport: transport, enabled: true }
    })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    status.innerHTML = '<span style="color:var(--success);">✅ MCP сервер добавлен</span>';
    loadSettings();
  })
  .catch(function(e) {
    status.innerHTML = '<span style="color:#ef4444;">❌ Ошибка: ' + e.message + '</span>';
  });
}

function reloadMcpServers() {
  var status = document.getElementById('settings-status');
  status.textContent = 'Перезагрузка...';
  
  fetch('/api/mcp/reload', { method: 'POST' })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    status.innerHTML = '<span style="color:var(--success);">✅ MCP серверы перезагружены</span>';
    loadSettings();
  })
  .catch(function(e) {
    status.innerHTML = '<span style="color:#ef4444;">❌ Ошибка: ' + e.message + '</span>';
  });
}
