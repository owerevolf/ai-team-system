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
    // Initialize header mode switcher
    var localOpt = document.getElementById('mode-local');
    var cloudOpt = document.getElementById('mode-cloud');
    var indicator = document.getElementById('mode-indicator');
    if (localOpt && cloudOpt && indicator) {
      if (mode === 'cloud') {
        localOpt.classList.remove('active');
        cloudOpt.classList.add('active');
        indicator.classList.add('cloud');
      } else {
        localOpt.classList.add('active');
        cloudOpt.classList.remove('active');
        indicator.classList.remove('cloud');
      }
    }

    // Auto-select models on first run (if no agents configured)
    if (!cfg.agents || Object.keys(cfg.agents).length === 0) {
      try {
        var autoResp = await fetch('/api/models/auto-select', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider: mode === 'cloud' ? 'openrouter' : 'ollama' })
        });
        var autoData = await autoResp.json();
        if (autoData.selections) {
          // Save auto-selected models
          await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agents: autoData.selections })
          });
          console.log('Auto-selected models:', autoData.selections);
        }
      } catch(e) {
        console.log('Auto-select skipped:', e.message);
      }
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
  // Скрываем приветственный оверлей при переходе на любую вкладку
  const overlay = document.getElementById('welcome-overlay');
  if (overlay) {
    overlay.style.display = 'none';
  }
  
  document.querySelectorAll('.tab-content').forEach(function(el) { el.classList.remove('active'); });
  document.querySelectorAll('.tab-btn').forEach(function(el) { el.classList.remove('active'); });
  var tabEl = document.getElementById('tab-' + tabName);
  if (tabEl) tabEl.classList.add('active');
  document.getElementById('tab-btn-' + tabName).classList.add('active');
  var isChat = tabName === 'chat';
  var isDeveloper = tabName === 'developer';
  document.getElementById('agents-bar').style.display = isChat ? 'flex' : 'none';
  document.getElementById('chat').style.display = isChat ? 'flex' : 'none';
  document.querySelector('.input-area').style.display = isChat ? 'block' : 'none';
  document.getElementById('chat-functions').style.display = isChat ? 'flex' : 'none';
  if (tabName === 'settings') loadSettings();
  if (tabName === 'kanban') loadKanbanTasks();
  if (tabName === 'kanban') renderKanban();
  if (tabName === 'promptarchitect') initPromptArchitectIfNotStarted();
  if (isDeveloper) {
    document.getElementById('dev-conversation').style.display = 'flex';
    document.getElementById('dev-content').classList.remove('visible');
  }
}

var settingsData = null;

var settingsData = null;

function loadSettings() {
  var container = document.getElementById('settings-content');
  container.innerHTML = '<div class="settings-loading"><div class="typing-indicator"><span></span><span></span><span></span></div><p>Загрузка настроек...</p></div>';

  Promise.all([
    fetch('/api/providers?force_refresh=true').then(function(r) { return r.json(); }),
    fetch('/api/agents/config').then(function(r) { return r.json(); }),
    fetch('/api/config').then(function(r) { return r.json(); }),
    fetch('/api/health/providers').then(function(r) { return r.json(); }).catch(function() { return {}; })
  ]).then(function(results) {
    settingsData = { providers: results[0], agents: results[1], config: results[2], health: results[3].health || {} };
    renderSettings();
  }).catch(function(e) {
    container.innerHTML = '<div class="settings-status error">Ошибка загрузки: ' + e.message + '</div>';
  });
}

function renderSettings() {
  var container = document.getElementById('settings-content');
  var providers = settingsData.providers;
  var agents = settingsData.agents;
  var config = settingsData.config;
  var health = settingsData.health || {};
  var currentMode = config.ai_mode || 'local';
  var selectedProvider = config.selected_provider || 'openrouter';

  var h = '<div class="settings-layout">';

  // ── API Key Section ──
  h += '<div class="settings-card">';
  h += '<div class="settings-card-header"><div class="card-icon api-key">🔑</div><div><h3>API ключ</h3><p>Вставь ключ для облачных моделей</p></div></div>';
  h += '<div class="api-key-input-wrap">';
  h += '<input type="password" id="api-key-input" placeholder="sk-or-v1-..." value="' + (config.openrouter_api_key_set ? '••••••••••••' : '') + '">';
  h += '<button onclick="saveApiKey()">💾 Сохранить</button>';
  h += '</div>';
  h += '<p style="font-size:10px;color:var(--muted);margin-top:8px;">🔗 <a href="https://openrouter.ai/keys" target="_blank" style="color:var(--accent2);">Получить ключ OpenRouter</a> · 🔗 <a href="https://ollama.com/download" target="_blank" style="color:var(--accent2);">Установить Ollama</a></p>';
  h += '</div>';

  // ── Providers Section ──
  h += '<div class="settings-card">';
  h += '<div class="settings-card-header"><div class="card-icon providers">📡</div><div><h3>Провайдеры</h3><p>Выбери провайдера AI моделей</p></div></div>';
  h += '<div class="provider-cards">';
  for (var pid in providers) {
    var info = providers[pid];
    var isSelected = selectedProvider === pid ? ' selected' : '';
    var statusClass = info.is_available ? 'online' : 'offline';
    var statusText = info.is_available ? '● Доступен' : '○ Недоступен';
    h += '<div class="provider-card' + isSelected + '" onclick="selectProvider(\'' + pid + '\')" id="provider-card-' + pid + '">';
    h += '<div class="provider-name">' + info.name + '</div>';
    h += '<div class="provider-desc">' + info.description + '</div>';
    h += '<div class="provider-status ' + statusClass + '">' + statusText + '</div>';
    h += '<div class="provider-models-count">' + info.free_models_count + ' бесплатных</div>';
    h += '</div>';
  }
  h += '</div></div>';

  // ── Agent Models Section ──
  h += '<div class="settings-card">';
  h += '<div class="settings-card-header"><div class="card-icon models">🤖</div><div><h3>Модели агентов</h3><p>Выбери модель для каждого агента</p></div></div>';

  // Auto-select button
  h += '<div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;">';
  h += '<div class="auto-select-btn" id="auto-select-btn" onclick="runAutoSelect()">✨ Авто-выбрать лучшие модели</div>';
  h += '<div class="auto-select-btn" id="test-models-btn" onclick="testAllModels()" style="background:linear-gradient(135deg,rgba(124,110,245,.15),rgba(124,110,245,.05));border-color:rgba(124,110,245,.3);color:var(--accent2);">🧪 Протестировать модели</div>';
  h += '</div>';

  h += '<div class="agent-models-list">';

  var agentIcons = { teamlead:'👔', architect:'🏛', backend:'⚙️', frontend:'🎨', devops:'🚀', tester:'🧪', documentalist:'📝' };
  var agentRoles = { teamlead:'Координирует команду', architect:'Проектирует архитектуру', backend:'Серверная разработка', frontend:'Интерфейс', devops:'Инфраструктура', tester:'Тестирование', documentalist:'Документация' };

  for (var i = 0; i < agents.agents.length; i++) {
    var agent = agents.agents[i];
    var icon = agentIcons[agent.name] || '🤖';
    var role = agentRoles[agent.name] || agent.description;
    var selectedModel = config.agents && config.agents[agent.name] ? config.agents[agent.name].model : null;

    h += '<div class="agent-model-card">';
    h += '<div class="agent-header"><div class="agent-icon">' + icon + '</div><div><div class="agent-name">' + agent.name.toUpperCase() + '</div><div class="agent-role">' + role + '</div></div></div>';
    h += '<div class="model-items" id="models-' + agent.name + '">';

    // Show top models (max 8)
    var maxModels = Math.min(agent.available_models.length, 8);
    for (var j = 0; j < maxModels; j++) {
      var model = agent.available_models[j];
      var isSelected = selectedModel === model.id ? ' selected' : '';
      var isFree = model.id.indexOf(':free') !== -1;
      var isRecommended = j < 2 && isFree; // First 2 free models are recommended

      h += '<div class="model-item' + isSelected + (isRecommended ? ' recommended' : '') + '" onclick="selectModel(\'' + agent.name + '\',\'' + model.id + '\')" id="model-' + agent.name + '-' + j + '">';

      if (isRecommended) {
        h += '<div class="rec-badge">★ Рекомендуем</div>';
      }

      h += '<div class="model-info">';
      h += '<div class="model-name">' + (model.name || model.id.split('/').pop()) + '</div>';
      h += '<div class="model-id">' + model.id + '</div>';
      h += '</div>';

      h += '<div class="model-badges">';
      if (isFree) h += '<span class="model-badge free">FREE</span>';
      if (model.strength) h += '<span class="model-badge ' + model.strength + '">' + model.strength + '</span>';
      var ctx = model.context_length ? (model.context_length >= 1000000 ? (model.context_length/1000000).toFixed(1) + 'M' : (model.context_length/1000).toFixed(0) + 'K') : '?';
      h += '<span style="font-size:9px;color:var(--muted);font-family:monospace;">' + ctx + '</span>';
      h += '</div>';

      h += '<div class="model-status" id="status-' + agent.name + '-' + j + '">';
      h += '<div class="status-dot" id="dot-' + agent.name + '-' + j + '"></div>';
      h += '</div>';

      h += '</div>';
    }

    h += '</div></div>';
  }

  h += '</div></div>'; // end agent-models-list and settings-card

  // ── Actions ──
  h += '<div class="settings-actions">';
  h += '<button class="btn-save" onclick="saveConfig()">💾 Сохранить все настройки</button>';
  h += '<button class="btn-secondary" onclick="loadSettings()">🔄 Обновить</button>';
  h += '</div>';

  h += '<div class="settings-status" id="settings-status"></div>';

  h += '</div>'; // end settings-layout

  container.innerHTML = h;
}

function selectProvider(pid) {
  document.querySelectorAll('.provider-card').forEach(function(el) { el.classList.remove('selected'); });
  document.getElementById('provider-card-' + pid).classList.add('selected');
  settingsData.selectedProvider = pid;
}

function selectModel(agentName, modelId) {
  // Deselect all models for this agent
  var card = document.querySelector('#models-' + agentName);
  if (card) {
    card.querySelectorAll('.model-item').forEach(function(el) { el.classList.remove('selected'); });
  }
  // Select this model
  var items = document.querySelectorAll('#models-' + agentName + ' .model-item');
  items.forEach(function(el) {
    if (el.onclick && el.onclick.toString().indexOf(modelId) !== -1) {
      el.classList.add('selected');
    }
  });
  // Store selection
  if (!settingsData.selectedModels) settingsData.selectedModels = {};
  settingsData.selectedModels[agentName] = modelId;
}

function saveApiKey() {
  var status = document.getElementById('settings-status');
  if (!status) {
    // Create status element if not exists
    var layout = document.querySelector('.settings-layout');
    if (layout) {
      var div = document.createElement('div');
      div.id = 'settings-status';
      div.className = 'settings-status';
      layout.appendChild(div);
      status = div;
    }
  }
  if (!status) return;

  var key = document.getElementById('api-key-input').value;
  if (!key || key === '••••••••••••') {
    status.className = 'settings-status error';
    status.textContent = '⚠️ Введи API ключ';
    return;
  }
  status.className = 'settings-status success';
  status.textContent = '⏳ Сохранение...';

  fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ openrouter_api_key: key })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    status.className = 'settings-status success';
    status.textContent = '✅ API ключ сохранён!';
    // Auto-hide after 5 seconds
    setTimeout(function() {
      status.className = 'settings-status';
      status.textContent = '';
    }, 5000);
  })
  .catch(function(e) {
    status.className = 'settings-status error';
    status.textContent = '❌ Ошибка: ' + e.message;
  });
}

function saveConfig() {
  var status = document.getElementById('settings-status');
  var agents = {};
  if (settingsData.selectedModels) {
    for (var a in settingsData.selectedModels) {
      agents[a] = { provider: settingsData.selectedProvider || 'openrouter', model: settingsData.selectedModels[a] };
    }
  }

  status.className = 'settings-status success';
  status.textContent = 'Сохранение...';

  fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      openrouter_api_key: document.getElementById('api-key-input') ? document.getElementById('api-key-input').value : '',
      agents: agents,
      ai_mode: settingsData.aiMode || 'local',
      selected_provider: settingsData.selectedProvider || 'openrouter'
    })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    status.className = 'settings-status success';
    status.textContent = '✅ Настройки сохранены! ' + (data.message || '');
    setTimeout(function() {
      status.className = 'settings-status';
      status.textContent = '';
    }, 5000);
  })
  .catch(function(e) {
    status.className = 'settings-status error';
    status.textContent = '❌ Ошибка: ' + e.message;
  });
}

function runAutoSelect() {
  var btn = document.getElementById('auto-select-btn');
  btn.classList.add('testing');
  btn.textContent = '⏳ Подбираем модели...';

  fetch('/api/models/auto-select', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider: settingsData.selectedProvider || 'openrouter' })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    btn.classList.remove('testing');
    btn.textContent = '✨ Авто-выбрать лучшие модели';

    if (data.selections) {
      // Select each recommended model
      for (var role in data.selections) {
        var modelId = data.selections[role].modelId;
        selectModel(role, modelId);
      }
      var status = document.getElementById('settings-status');
      status.className = 'settings-status success';
      status.textContent = '✅ Авто-выбрано ' + Object.keys(data.selections).length + ' моделей для агентов';
    }
  })
  .catch(function(e) {
    btn.classList.remove('testing');
    btn.textContent = '✨ Авто-выбрать лучшие модели';
    var status = document.getElementById('settings-status');
    status.className = 'settings-status error';
    status.textContent = '❌ Ошибка: ' + e.message;
  });
}

function testAllModels() {
  var btn = document.getElementById('test-models-btn');
  btn.classList.add('testing');
  btn.textContent = '⏳ Тестируем...';

  // Get all visible model items
  var modelItems = document.querySelectorAll('.model-item');
  var total = modelItems.length;
  var tested = 0;
  var passed = 0;

  modelItems.forEach(function(item) {
    var onclick = item.onclick ? item.onclick.toString() : '';
    var match = onclick.match(/selectModel\('([^']+)','([^']+)'\)/);
    if (!match) return;

    var agentName = match[1];
    var modelId = match[2];
    var idx = item.id.split('-').pop();
    var dot = document.getElementById('dot-' + agentName + '-' + idx);
    var statusEl = document.getElementById('status-' + agentName + '-' + idx);

    if (dot) {
      dot.className = 'status-dot testing';
    }

    fetch('/api/models/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_id: modelId, provider: settingsData.selectedProvider || 'openrouter' })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      tested++;
      if (data.status === 'ok') {
        passed++;
        if (dot) dot.className = 'status-dot online';
        if (statusEl) {
          var latency = document.createElement('span');
          latency.className = 'latency';
          latency.textContent = data.latency_ms + 'ms';
          statusEl.appendChild(latency);
        }
      } else {
        if (dot) dot.className = 'status-dot offline';
      }
      updateTestProgress();
    })
    .catch(function() {
      tested++;
      if (dot) dot.className = 'status-dot offline';
      updateTestProgress();
    });
  });

  function updateTestProgress() {
    btn.textContent = '⏳ Тестируем... ' + tested + '/' + total;
    if (tested >= total) {
      btn.classList.remove('testing');
      btn.textContent = '🧪 Протестировать модели';
      var status = document.getElementById('settings-status');
      status.className = 'settings-status success';
      status.textContent = '✅ Готово! ' + passed + ' из ' + total + ' моделей работают';
    }
  }
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

// ══════════════════════════════════════════
//  KANBAN — Full Implementation
// ══════════════════════════════════════════

var kanbanData = {
  columns: [
    { id: 'todo', title: '📋 Ожидание', color: '#6b6b7e' },
    { id: 'in_progress', title: '🔄 В работе', color: '#7c6ef5' },
    { id: 'done', title: '✅ Готово', color: '#4ade80' },
    { id: 'failed', title: '❌ Ошибка', color: '#ef4444' },
  ],
  tasks: [],
  filter: { agent: 'all', priority: 'all' },
  draggedTask: null,
};

// ── API Integration ──

async function loadKanbanTasks() {
  try {
    var r = await fetch('/api/kanban/tasks');
    var d = await r.json();
    kanbanData.tasks = d.tasks || [];
    renderKanban();
  } catch(e) {
    console.error('Failed to load kanban tasks:', e);
  }
}

async function apiCreateTask(agent, title, description, priority, column_id) {
  try {
    var r = await fetch('/api/kanban/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent, title, description, priority, column_id })
    });
    var d = await r.json();
    kanbanData.tasks.push({
      id: d.id, agent, title, description,
      status: column_id, priority, column_id,
      created_at: new Date().toISOString()
    });
    renderKanban();
    return d.id;
  } catch(e) {
    console.error('Failed to create task:', e);
  }
}

async function apiUpdateTask(task_id, updates) {
  try {
    await fetch('/api/kanban/tasks/' + task_id, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    });
    var task = kanbanData.tasks.find(t => t.id === task_id);
    if (task) {
      Object.assign(task, updates);
      if (updates.column_id && !updates.status) {
        task.status = updates.column_id;
      }
    }
    renderKanban();
  } catch(e) {
    console.error('Failed to update task:', e);
  }
}

async function apiDeleteTask(task_id) {
  try {
    await fetch('/api/kanban/tasks/' + task_id, { method: 'DELETE' });
    kanbanData.tasks = kanbanData.tasks.filter(t => t.id !== task_id);
    renderKanban();
  } catch(e) {
    console.error('Failed to delete task:', e);
  }
}

// ── Rendering ──

function renderKanban() {
  var board = document.getElementById('kanban-board');
  if (!board) return;
  
  // Apply filters
  var filteredTasks = kanbanData.tasks.filter(function(t) {
    if (kanbanData.filter.agent !== 'all' && t.agent !== kanbanData.filter.agent) return false;
    if (kanbanData.filter.priority !== 'all' && t.priority !== kanbanData.filter.priority) return false;
    return true;
  });
  
  var h = '';
  for (var col of kanbanData.columns) {
    var colTasks = filteredTasks.filter(t => t.column_id === col.id);
    h += '<div class="kanban-column" data-column="' + col.id + '" ';
    h += 'ondragover="onDragOver(event)" ondragleave="onDragLeave(event)" ondrop="onDrop(event, \'' + col.id + '\')">';
    h += '<div style="font-size:12px;font-weight:600;color:' + col.color + ';margin-bottom:12px;">' + col.title + ' (' + colTasks.length + ')</div>';
    for (var task of colTasks) {
      h += renderTaskCard(task);
    }
    h += '</div>';
  }
  board.innerHTML = h;
  
  // Update task list below board
  var taskList = document.getElementById('kanban-task-list');
  if (taskList) {
    if (filteredTasks.length === 0) {
      taskList.innerHTML = '<p style="color:var(--muted);font-size:12px;">Задачи появятся при запуске сборки проекта.</p>';
    } else {
      var listHtml = '';
      for (var task of filteredTasks) {
        var statusIcon = task.status === 'done' ? '✅' : task.status === 'in_progress' ? '🔄' : task.status === 'failed' ? '❌' : '📋';
        listHtml += '<div style="display:flex;align-items:center;gap:8px;padding:8px;background:var(--surface);border-radius:6px;border:1px solid var(--border);">';
        listHtml += '<span>' + statusIcon + '</span>';
        listHtml += '<span style="font-size:12px;color:var(--text);flex:1;">' + task.agent + ': ' + task.title + '</span>';
        if (task.priority) listHtml += '<span style="font-size:10px;color:var(--muted);">' + task.priority + '</span>';
        listHtml += '</div>';
      }
      taskList.innerHTML = listHtml;
    }
  }
  
  updateFilterOptions();
}

function renderTaskCard(task) {
  var priorityColor = { high: '#ef4444', medium: '#facc15', low: '#4ade80' }[task.priority] || '#6b6b7e';
  var h = '<div class="kanban-task" draggable="true" data-task-id="' + task.id + '" ';
  h += 'ondragstart="onDragStart(event, ' + task.id + ')" ondragend="onDragEnd(event)" ';
  h += 'onclick="openTaskModal(' + task.id + ')" ';
  h += 'style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px;margin-bottom:8px;font-size:11px;cursor:pointer;transition:all .2s;">';
  h += '<div style="display:flex;justify-content:space-between;align-items:flex-start;">';
  h += '<div style="font-weight:600;color:var(--text);flex:1;">' + escHtml(task.agent) + '</div>';
  h += '<div style="width:8px;height:8px;border-radius:50%;background:' + priorityColor + ';flex-shrink:0;margin-left:4px;margin-top:2px;" title="Priority: ' + task.priority + '"></div>';
  h += '</div>';
  h += '<div style="color:var(--muted);margin-top:4px;">' + escHtml(task.title) + '</div>';
  if (task.description) {
    h += '<div style="color:var(--muted);margin-top:2px;font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escHtml(task.description.substring(0, 60)) + '</div>';
  }
  if (task.created_at) {
    var dt = new Date(task.created_at);
    h += '<div style="color:var(--muted);margin-top:4px;font-size:9px;">' + dt.toLocaleDateString('ru-RU') + '</div>';
  }
  h += '</div>';
  return h;
}

// ── Drag and Drop ──

function onDragStart(e, task_id) {
  kanbanData.draggedTask = task_id;
  e.target.style.opacity = '0.5';
  e.dataTransfer.effectAllowed = 'move';
}

function onDragEnd(e) {
  e.target.style.opacity = '1';
  kanbanData.draggedTask = null;
}

function onDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  var column = e.currentTarget;
  column.style.borderColor = 'var(--accent)';
  column.style.background = 'rgba(124,110,245,0.05)';
}

function onDragLeave(e) {
  var column = e.currentTarget;
  column.style.borderColor = 'var(--border)';
  column.style.background = 'var(--surface)';
}

function onDrop(e, column_id) {
  e.preventDefault();
  var column = e.currentTarget;
  column.style.borderColor = 'var(--border)';
  column.style.background = 'var(--surface)';
  
  var task_id = kanbanData.draggedTask;
  if (task_id) {
    apiUpdateTask(task_id, { column_id: column_id, status: column_id });
  }
}

// ── Task Modal (Edit/Create) ──

function openTaskModal(task_id) {
  var task = kanbanData.tasks.find(t => t.id === task_id);
  if (!task) return;
  
  var modal = document.createElement('div');
  modal.id = 'task-modal';
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;z-index:200;';
  modal.onclick = function(e) { if (e.target === modal) closeTaskModal(); };
  
  var content = '<div style="background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:24px;max-width:500px;width:90%;max-height:80vh;overflow-y:auto;">';
  content += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">';
  content += '<h3 style="font-size:16px;color:var(--text);">✏️ Редактировать задачу</h3>';
  content += '<button onclick="closeTaskModal()" style="background:none;border:none;color:var(--muted);font-size:18px;cursor:pointer;">✕</button>';
  content += '</div>';
  
  content += '<div style="margin-bottom:16px;"><label style="font-size:11px;color:var(--muted);display:block;margin-bottom:6px;">Агент</label>';
  content += '<select id="modal-agent" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:12px;">';
  var agents = ['teamlead','architect','backend','frontend','devops','tester','documentalist'];
  for (var a of agents) {
    content += '<option value="' + a + '"' + (task.agent === a ? ' selected' : '') + '>' + (AGENT_LABELS[a] || a) + '</option>';
  }
  content += '</select></div>';
  
  content += '<div style="margin-bottom:16px;"><label style="font-size:11px;color:var(--muted);display:block;margin-bottom:6px;">Название</label>';
  content += '<input type="text" id="modal-title" value="' + escHtml(task.title) + '" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:12px;"></div>';
  
  content += '<div style="margin-bottom:16px;"><label style="font-size:11px;color:var(--muted);display:block;margin-bottom:6px;">Описание</label>';
  content += '<textarea id="modal-desc" rows="3" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:12px;resize:vertical;">' + escHtml(task.description || '') + '</textarea></div>';
  
  content += '<div style="display:flex;gap:12px;margin-bottom:16px;">';
  content += '<div style="flex:1;"><label style="font-size:11px;color:var(--muted);display:block;margin-bottom:6px;">Статус</label>';
  content += '<select id="modal-status" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:12px;">';
  for (var col of kanbanData.columns) {
    content += '<option value="' + col.id + '"' + (task.column_id === col.id ? ' selected' : '') + '>' + col.title + '</option>';
  }
  content += '</select></div>';
  
  content += '<div style="flex:1;"><label style="font-size:11px;color:var(--muted);display:block;margin-bottom:6px;">Приоритет</label>';
  content += '<select id="modal-priority" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:12px;">';
  var priorities = [['high', '🔴 Высокий'], ['medium', '🟡 Средний'], ['low', '🟢 Низкий']];
  for (var p of priorities) {
    content += '<option value="' + p[0] + '"' + (task.priority === p[0] ? ' selected' : '') + '>' + p[1] + '</option>';
  }
  content += '</select></div></div>';
  
  content += '<div style="display:flex;gap:12px;">';
  content += '<button onclick="saveTaskChanges(' + task.id + ')" class="btn-save" style="flex:1;">💾 Сохранить</button>';
  content += '<button onclick="deleteTaskAndClose(' + task.id + ')" style="padding:10px 20px;border:1px solid #ef4444;border-radius:8px;background:transparent;color:#ef4444;font-size:12px;cursor:pointer;">🗑 Удалить</button>';
  content += '</div></div>';
  
  modal.innerHTML = content;
  document.body.appendChild(modal);
}

function closeTaskModal() {
  var modal = document.getElementById('task-modal');
  if (modal) modal.remove();
}

function saveTaskChanges(task_id) {
  var updates = {
    agent: document.getElementById('modal-agent').value,
    title: document.getElementById('modal-title').value,
    description: document.getElementById('modal-desc').value,
    column_id: document.getElementById('modal-status').value,
    priority: document.getElementById('modal-priority').value,
  };
  apiUpdateTask(task_id, updates);
  closeTaskModal();
}

function deleteTaskAndClose(task_id) {
  if (confirm('Удалить задачу?')) {
    apiDeleteTask(task_id);
    closeTaskModal();
  }
}

// ── Filtering ──

function updateFilterOptions() {
  var agentFilter = document.getElementById('kanban-filter-agent');
  var priorityFilter = document.getElementById('kanban-filter-priority');
  if (!agentFilter || !priorityFilter) return;
  
  // Get unique agents from tasks
  var agents = [...new Set(kanbanData.tasks.map(t => t.agent))];
  var currentAgent = agentFilter.value;
  agentFilter.innerHTML = '<option value="all">Все агенты</option>';
  for (var a of agents) {
    agentFilter.innerHTML += '<option value="' + a + '"' + (currentAgent === a ? ' selected' : '') + '>' + a + '</option>';
  }
  
  var currentPriority = priorityFilter.value;
  var priorities = [['all', 'Все'], ['high', '🔴 Высокий'], ['medium', '🟡 Средний'], ['low', '🟢 Низкий']];
  priorityFilter.innerHTML = '';
  for (var p of priorities) {
    priorityFilter.innerHTML += '<option value="' + p[0] + '"' + (currentPriority === p[0] ? ' selected' : '') + '>' + p[1] + '</option>';
  }
}

function applyKanbanFilter() {
  kanbanData.filter.agent = document.getElementById('kanban-filter-agent').value;
  kanbanData.filter.priority = document.getElementById('kanban-filter-priority').value;
  renderKanban();
}

// ── Create New Task ──

function openNewTaskModal() {
  var modal = document.createElement('div');
  modal.id = 'task-modal';
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;z-index:200;';
  modal.onclick = function(e) { if (e.target === modal) closeTaskModal(); };
  
  var content = '<div style="background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:24px;max-width:500px;width:90%;max-height:80vh;overflow-y:auto;">';
  content += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">';
  content += '<h3 style="font-size:16px;color:var(--text);">➕ Новая задача</h3>';
  content += '<button onclick="closeTaskModal()" style="background:none;border:none;color:var(--muted);font-size:18px;cursor:pointer;">✕</button>';
  content += '</div>';
  
  content += '<div style="margin-bottom:16px;"><label style="font-size:11px;color:var(--muted);display:block;margin-bottom:6px;">Агент</label>';
  content += '<select id="modal-agent" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:12px;">';
  var agents = ['teamlead','architect','backend','frontend','devops','tester','documentalist'];
  for (var a of agents) {
    content += '<option value="' + a + '>' + (AGENT_LABELS[a] || a) + '</option>';
  }
  content += '</select></div>';
  
  content += '<div style="margin-bottom:16px;"><label style="font-size:11px;color:var(--muted);display:block;margin-bottom:6px;">Название</label>';
  content += '<input type="text" id="modal-title" placeholder="Что нужно сделать?" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:12px;"></div>';
  
  content += '<div style="margin-bottom:16px;"><label style="font-size:11px;color:var(--muted);display:block;margin-bottom:6px;">Описание</label>';
  content += '<textarea id="modal-desc" rows="3" placeholder="Детали задачи..." style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:12px;resize:vertical;"></textarea></div>';
  
  content += '<div style="display:flex;gap:12px;margin-bottom:16px;">';
  content += '<div style="flex:1;"><label style="font-size:11px;color:var(--muted);display:block;margin-bottom:6px;">Столбец</label>';
  content += '<select id="modal-status" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:12px;">';
  for (var col of kanbanData.columns) {
    content += '<option value="' + col.id + '>' + col.title + '</option>';
  }
  content += '</select></div>';
  
  content += '<div style="flex:1;"><label style="font-size:11px;color:var(--muted);display:block;margin-bottom:6px;">Приоритет</label>';
  content += '<select id="modal-priority" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);font-size:12px;">';
  content += '<option value="medium">🟡 Средний</option>';
  content += '<option value="high">🔴 Высокий</option>';
  content += '<option value="low">🟢 Низкий</option>';
  content += '</select></div></div>';
  
  content += '<button onclick="createNewTask()" class="btn-save" style="width:100%;">➕ Создать задачу</button>';
  content += '</div>';
  
  modal.innerHTML = content;
  document.body.appendChild(modal);
}

function createNewTask() {
  var agent = document.getElementById('modal-agent').value;
  var title = document.getElementById('modal-title').value.trim();
  var desc = document.getElementById('modal-desc').value.trim();
  var status = document.getElementById('modal-status').value;
  var priority = document.getElementById('modal-priority').value;
  
  if (!title) {
    alert('Введите название задачи');
    return;
  }
  
  apiCreateTask(agent, title, desc || null, priority, status);
  closeTaskModal();
}

// ── Legacy helpers (for build automation) ──

function addKanbanTask(agent, title, status) {
  // Check if task already exists
  var existing = kanbanData.tasks.find(t => t.agent === agent && t.title === title);
  if (existing) {
    existing.status = status;
    existing.column_id = status;
    existing.time = new Date().toLocaleTimeString('ru-RU');
  } else {
    var task = {
      id: 'local_' + Date.now(),
      agent: agent,
      title: title,
      status: status || 'todo',
      column_id: status || 'todo',
      priority: 'medium',
      time: new Date().toLocaleTimeString('ru-RU'),
      created_at: new Date().toISOString()
    };
    kanbanData.tasks.push(task);
  }
  renderKanban();
}

function clearKanban() {
  // Only clear local tasks (not API tasks)
  kanbanData.tasks = kanbanData.tasks.filter(t => !t.id || typeof t.id !== 'number');
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


// ══════════════════════════════════════════
//  CODER CHAT — Full Redesign
// ══════════════════════════════════════════

var coderSessionId = null;
var coderProjectPath = null;

function initCoderChat() {
  var projectName = document.getElementById('coder-project-name').value.trim() || 'my_project';

  fetch('/api/coderchat/init', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_name: projectName })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (data.session_id) {
      coderSessionId = data.session_id;
      coderProjectPath = data.project_path;

      // Show chat area, hide welcome
      document.getElementById('coder-welcome').style.display = 'none';
      var chatArea = document.getElementById('coder-chat-area');
      chatArea.style.display = 'flex';

      // Update sidebar
      document.getElementById('coder-project-path').textContent = data.project_path;
      updateCoderFileTree(data.file_tree || []);
      document.getElementById('coder-sidebar-footer').innerHTML =
        'Проект: <strong>' + data.project_name + '</strong><br>Файлов: ' + (data.file_tree ? data.file_tree.length : 0) + '<br>Стек: ' + (data.tech_stack || []).join(', ');

      // Add system message
      addCoderMsg('system', 'Проект "' + data.project_name + '" инициализирован. Технологии: ' + (data.tech_stack || []).join(', ') + '. Спрашивайте о чём угодно!');
    } else {
      addCoderMsg('system', '⚠️ Ошибка: ' + (data.error || 'не удалось инициализировать'));
    }
  })
  .catch(function(e) { addCoderMsg('system', '⚠️ Ошибка: ' + e.message); });
}

function sendCoderMessage() {
  var input = document.getElementById('coder-input');
  var message = input.value.trim();
  if (!message || !coderSessionId) return;
  input.value = '';
  input.style.height = 'auto';

  addCoderMsg('user', message);
  showCoderTyping();

  fetch('/api/coderchat/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: coderSessionId, message: message })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    hideCoderTyping();
    if (data.response) {
      addCoderMsg('assistant', data.response, data.file_actions);
    } else if (data.error) {
      addCoderMsg('system', '⚠️ Ошибка: ' + data.error);
    }
    if (data.file_actions && data.file_actions.length > 0) refreshCoderFiles();
  })
  .catch(function(e) {
    hideCoderTyping();
    addCoderMsg('system', '⚠️ Ошибка: ' + e.message);
  });
}

function addCoderMsg(role, content, fileActions) {
  var container = document.getElementById('coder-messages');

  var row = document.createElement('div');
  row.className = 'msg-row ' + role;

  // Avatar
  var avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  if (role === 'user') avatar.textContent = '👤';
  else if (role === 'assistant') avatar.textContent = '🤖';
  row.appendChild(avatar);

  // Bubble
  var bubble = document.createElement('div');
  bubble.className = 'msg-bubble';

  if (role === 'assistant' && content) {
    bubble.innerHTML = formatCoderMsg(content);
  } else {
    bubble.textContent = content;
  }

  // File actions
  if (fileActions && fileActions.length > 0) {
    var faDiv = document.createElement('div');
    faDiv.className = 'file-actions';
    fileActions.forEach(function(a) {
      var item = document.createElement('div');
      item.className = 'action-item ' + (a.action || 'create');
      item.innerHTML = (a.action === 'create' ? '📄' : a.action === 'delete' ? '🗑' : '✏️') + ' ' + a.path;
      faDiv.appendChild(item);
    });
    bubble.appendChild(faDiv);
  }

  row.appendChild(bubble);
  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
}

function formatCoderMsg(text) {
  if (!text) return '';
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, function(_, lang, code) {
      return '<pre><span class="code-lang">' + (lang || 'code') + '</span><code>' + code.trim() + '</code></pre>';
    })
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');
}

function showCoderTyping() {
  var c = document.getElementById('coder-messages');
  var row = document.createElement('div');
  row.className = 'msg-row assistant';
  row.id = 'coder-typing-row';

  var avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.textContent = '🤖';
  row.appendChild(avatar);

  var bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
  row.appendChild(bubble);

  c.appendChild(row);
  c.scrollTop = c.scrollHeight;
}

function hideCoderTyping() {
  var t = document.getElementById('coder-typing-row');
  if (t) t.remove();
}

function updateCoderFileTree(tree) {
  var container = document.getElementById('coder-file-tree');
  if (!tree || tree.length === 0) {
    container.innerHTML = '<div class="file-item"><span class="icon">📭</span> Пока пусто</div>';
    return;
  }
  container.innerHTML = '';
  tree.forEach(function(f) {
    var item = document.createElement('div');
    item.className = 'file-item' + (f.endsWith('/') ? ' dir' : '');
    var icon = f.endsWith('/') ? '📁' : getFileIcon(f);
    item.innerHTML = '<span class="icon">' + icon + '</span> ' + f.replace(/\/$/, '');
    container.appendChild(item);
  });
}

function getFileIcon(filename) {
  var ext = filename.split('.').pop().toLowerCase();
  var icons = { py: '🐍', js: '📜', ts: '📘', html: '🌐', css: '🎨', json: '📋', md: '📝', txt: '📄', yml: '⚙️', yaml: '⚙️', sh: '💻', bash: '💻' };
  return icons[ext] || '📄';
}

function refreshCoderFiles() {
  if (!coderSessionId) return;
  fetch('/api/coderchat/files/' + coderSessionId)
    .then(function(r) { return r.json(); })
    .then(function(data) { if (data.file_tree) updateCoderFileTree(data.file_tree); })
    .catch(function() {});
}

function handleCoderKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendCoderMessage();
  }
}

function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
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



// ══════════════════════════════════════════
//  PROMPT ARCHITECT
// ══════════════════════════════════════════

var paSessionId = null;

function initPromptArchitect() {
  fetch('/api/promptarchitect/init', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (data.session_id) {
      paSessionId = data.session_id;
      document.getElementById('pa-init').style.display = 'none';
      document.getElementById('pa-chat-container').style.display = 'block';
      addPAMessage('assistant', data.welcome || '👋 Привет. Я Prompt Architect. С чего начнём?');
      updatePAStats({ total_messages: 1, user_messages: 0, assistant_messages: 1 });
    } else {
      alert('Ошибка: ' + (data.error || 'не удалось инициализировать'));
    }
  })
  .catch(function(e) { alert('Ошибка: ' + e.message); });
}

function sendPAMessage() {
  var input = document.getElementById('pa-input');
  var message = input.value.trim();
  if (!message || !paSessionId) return;
  input.value = '';
  addPAMessage('user', message);
  showPATyping();
  fetch('/api/promptarchitect/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: paSessionId, message: message })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    hidePATyping();
    if (data.response) addPAMessage('assistant', data.response);
    else if (data.error) addPAMessage('system', '⚠️ Ошибка: ' + data.error);
    if (data.success) {
      fetch('/api/promptarchitect/history/' + paSessionId)
        .then(function(r) { return r.json(); })
        .then(function(h) { if (h.stats) updatePAStats(h.stats); })
        .catch(function() {});
    }
  })
  .catch(function(e) { hidePATyping(); addPAMessage('system', '⚠️ Ошибка: ' + e.message); });
}

function addPAMessage(role, content) {
  var container = document.getElementById('pa-messages');
  var placeholder = container.querySelector('p[style*="text-align:center"]');
  if (placeholder) placeholder.remove();
  var msgDiv = document.createElement('div');
  var bg = role === 'user' ? 'rgba(124,110,245,.15)' : role === 'assistant' ? 'var(--surface)' : 'rgba(107,107,126,.1)';
  var border = role === 'user' ? 'rgba(124,110,245,.3)' : 'var(--border)';
  var align = role === 'user' ? 'flex-end' : 'flex-start';
  msgDiv.style.cssText = 'background:' + bg + ';border:1px solid ' + border + ';border-radius:12px;padding:12px 16px;max-width:85%;align-self:' + align + ';';
  var header = role === 'user' ? '<div style="font-size:10px;color:var(--accent);margin-bottom:4px;">👤 Вы</div>' :
               role === 'assistant' ? '<div style="font-size:10px;color:var(--success);margin-bottom:4px;">🧠 Prompt Architect</div>' :
               '<div style="font-size:10px;color:var(--muted);margin-bottom:4px;">⚙️ Система</div>';
  msgDiv.innerHTML = header + formatPAMessage(content);
  container.appendChild(msgDiv);
  container.scrollTop = container.scrollHeight;
}

function formatPAMessage(text) {
  if (!text) return '';
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<div class="code-block"><strong>$1</strong><br><pre style="margin:0;white-space:pre-wrap;">$2</pre></div>')
    .replace(/`([^`]+)`/g, '<code style="background:rgba(124,110,245,.1);padding:2px 6px;border-radius:4px;font-size:11px;">$1</code>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');
}

function showPATyping() {
  var c = document.getElementById('pa-messages');
  var t = document.createElement('div');
  t.id = 'pa-typing';
  t.style.cssText = 'background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:12px 16px;align-self:flex-start;';
  t.innerHTML = '<div class="typing"><span></span><span></span><span></span></div>';
  c.appendChild(t);
  c.scrollTop = c.scrollHeight;
}

function hidePATyping() { var t = document.getElementById('pa-typing'); if (t) t.remove(); }

function updatePAStats(stats) {
  var d = document.getElementById('pa-stats');
  if (d && stats) {
    d.innerHTML = 'Сообщений: ' + (stats.total_messages || 0) +
      '<br>Ваших: ' + (stats.user_messages || 0) +
      '<br>Ответов: ' + (stats.assistant_messages || 0);
  }
}

function clearPAChat() {
  if (paSessionId) {
    fetch('/api/promptarchitect/clear/' + paSessionId, { method: 'POST' }).catch(function() {});
  }
  paSessionId = null;
  document.getElementById('pa-chat-container').style.display = 'none';
  document.getElementById('pa-init').style.display = 'block';
  document.getElementById('pa-messages').innerHTML = '<p style="color:var(--muted);font-size:12px;text-align:center;">Нажми "Начать обучение" чтобы начать...</p>';
  document.getElementById('pa-stats').innerHTML = 'Нет активной сессии';
}

document.addEventListener('keydown', function(e) {
  if (e.target && e.target.id === 'pa-input' && e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendPAMessage();
  }
});

// Функция для инициализации Prompt Architect если еще не запущен
function initPromptArchitectIfNotStarted() {
  if (!paSessionId) {
    // Проверяем, есть ли уже содержимое в чате промтов
    var chatContainer = document.getElementById('pa-messages');
    var placeholder = chatContainer ? chatContainer.querySelector('p[style*="text-align:center"]') : null;
    
    // Если есть только плейсхолдер или нет сообщений, инициализируем
    if (!placeholder || chatContainer.children.length <= 1) {
      fetch('/api/promptarchitect/init', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.session_id) {
          paSessionId = data.session_id;
          document.getElementById('pa-init').style.display = 'none';
          document.getElementById('pa-chat-container').style.display = 'block';
          addPAMessage('assistant', data.welcome || '👋 Привет. Я Prompt Architect. С чего начнём?');
          updatePAStats({ total_messages: 1, user_messages: 0, assistant_messages: 1 });
        }
      })
      .catch(function(e) { 
        console.error('Ошибка инициализации Prompt Architect:', e);
        // Даже при ошибке показываем интерфейс
        document.getElementById('pa-init').style.display = 'none';
        document.getElementById('pa-chat-container').style.display = 'block';
        addPAMessage('system', '⚠️ Ошибка инициализации. Интерфейс будет показан без данных.');
      });
    }
  }
}// Вызов инициализации при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
  init();

  // All tabs — direct click handlers (browser_click doesn't bubble to delegation)
  var tabIds = ['chat', 'coder', 'settings', 'instruction', 'kanban', 'promptarchitect'];
  tabIds.forEach(function(tabName) {
    var btn = document.getElementById('tab-btn-' + tabName);
    if (btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        switchTab(tabName);
      });
    }
  });

  // Agent chip click handler
  var agentsBar = document.getElementById('agents-bar');
  if (agentsBar) {
    agentsBar.addEventListener('click', function(e) {
      var chip = e.target.closest('.agent-chip');
      if (chip && chip.dataset.agent) {
        var agent = chip.dataset.agent;
        document.querySelectorAll('.agent-chip').forEach(function(c) {
          c.classList.remove('active');
        });
        chip.classList.add('active');
        if (typeof state !== 'undefined') {
          state.currentAgent = agent;
        }
        console.log('Agent selected:', agent);
      }
    });
  }

  // ── DEVELOPER MODE ──
  var devTabIds = ['developer'];
  devTabIds.forEach(function(tabName) {
    var btn = document.getElementById('tab-btn-' + tabName);
    if (btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        switchTab(tabName);
      });
    }
  });

  // Dev sidebar navigation
  window.switchDevSection = function(section) {
    document.querySelectorAll('.dev-nav-item').forEach(function(el) {
      el.classList.remove('active');
    });
    var navItem = document.getElementById('dev-nav-' + section);
    if (navItem) navItem.classList.add('active');

    // Toggle panels vs conversation
    var panels = document.getElementById('dev-content');
    var conv = document.getElementById('dev-conversation');
    if (section === 'conversations') {
      panels.classList.add('visible');
      conv.style.display = 'none';
    } else {
      panels.classList.add('visible');
      conv.style.display = 'none';
    }

    document.querySelectorAll('.dev-panel').forEach(function(p) {
      p.classList.remove('active');
    });
    var panel = document.getElementById('dev-panel-' + section);
    if (panel) panel.classList.add('active');
  };

  // Toggle sidebar collapse
  window.toggleDevSidebar = function() {
    var sidebar = document.getElementById('dev-sidebar');
    if (sidebar) sidebar.classList.toggle('collapsed');
  };

  // Dev search
  window.devSearch = function(query) {
    var q = query.toLowerCase();
    document.querySelectorAll('.dev-nav-item').forEach(function(item) {
      var text = item.textContent.toLowerCase();
      item.style.display = q && text.indexOf(q) === -1 ? 'none' : 'flex';
    });
  };

  // Dev conversation
  window.sendDevMessage = function() {
    var input = document.getElementById('dev-input');
    if (!input) return;
    var text = input.value.trim();
    if (!text) return;
    input.value = '';
    autoResizeTextarea(input);

    var messages = document.getElementById('dev-conv-messages');
    if (!messages) return;

    // User message
    var userMsg = document.createElement('div');
    userMsg.className = 'dev-msg dev-msg-user';
    userMsg.innerHTML = '<div class="dev-msg-avatar">👤</div><div class="dev-msg-body"><div class="dev-msg-name">Ты</div><div class="dev-msg-text">' + escapeHtml(text) + '</div></div>';
    messages.appendChild(userMsg);
    messages.scrollTop = messages.scrollHeight;

    // Show typing indicator
    var typingMsg = document.createElement('div');
    typingMsg.className = 'dev-msg dev-msg-ai';
    typingMsg.id = 'dev-typing';
    typingMsg.innerHTML = '<div class="dev-msg-avatar">🛠</div><div class="dev-msg-body"><div class="dev-msg-name">Developer Mode</div><div class="dev-msg-text"><div class="typing-indicator"><span></span><span></span><span></span></div></div></div>';
    messages.appendChild(typingMsg);
    messages.scrollTop = messages.scrollHeight;

    // Call understanding API
    fetch('/api/developer/message', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text, project_id: ''})
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var typing = document.getElementById('dev-typing');
      if (typing) typing.remove();

      if (data && data.understanding) {
        var u = data.understanding;
        var formatted = u.formatted || 'Анализ завершен.';

        // Build understanding response
        var html = '<div class="dev-msg-avatar">🛠</div><div class="dev-msg-body"><div class="dev-msg-name">Developer Mode — Understanding Phase</div><div class="dev-msg-text">' +
          '<div class="dev-understanding">' +
          formatted.replace(/\n/g, '<br>') +
          '</div>';

        // Add "Начать разработку" button if ready
        if (u.is_ready) {
          html += '<br><button class="dev-execute-btn" onclick="devStartExecution()">&#128640; Начать разработку</button>';
        } else if (u.clarification_questions && u.clarification_questions.length > 0) {
          html += '<br><span class="dev-waiting-hint">⏳ Ответь на уточняющие вопросы чтобы продолжить</span>';
        }

        html += '</div></div>';

        var aiMsg = document.createElement('div');
        aiMsg.className = 'dev-msg dev-msg-ai';
        aiMsg.innerHTML = html;
        messages.appendChild(aiMsg);
      } else {
        var errMsg = document.createElement('div');
        errMsg.className = 'dev-msg dev-msg-ai';
        errMsg.innerHTML = '<div class="dev-msg-avatar">🛠</div><div class="dev-msg-body"><div class="dev-msg-name">Developer Mode</div><div class="dev-msg-text">Ошибка анализа. Попробуй ещё раз.</div></div>';
        messages.appendChild(errMsg);
      }
      messages.scrollTop = messages.scrollHeight;
    })
    .catch(function() {
      var typing = document.getElementById('dev-typing');
      if (typing) typing.remove();
      var errMsg = document.createElement('div');
      errMsg.className = 'dev-msg dev-msg-ai';
      errMsg.innerHTML = '<div class="dev-msg-avatar">🛠</div><div class="dev-msg-body"><div class="dev-msg-name">Developer Mode</div><div class="dev-msg-text">Ошибка соединения с сервером.</div></div>';
      messages.appendChild(errMsg);
      messages.scrollTop = messages.scrollHeight;
    });
  };

  window.devStartExecution = function() {
    var messages = document.getElementById('dev-conv-messages');
    if (!messages) return;
    var infoMsg = document.createElement('div');
    infoMsg.className = 'dev-msg dev-msg-system';
    infoMsg.innerHTML = '<div class="dev-msg-avatar">🛠</div><div class="dev-msg-body"><div class="dev-msg-name">Developer Mode</div><div class="dev-msg-text">⏳ Execution engine будет реализован в Phase 19C — Safe Orchestration Runtime.</div></div>';
    messages.appendChild(infoMsg);
    messages.scrollTop = messages.scrollHeight;
  };

  window.handleDevKey = function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendDevMessage();
    }
  };

  window.devNewConversation = function() {
    var messages = document.getElementById('dev-conv-messages');
    if (messages) messages.innerHTML = '';
    var panels = document.getElementById('dev-content');
    var conv = document.getElementById('dev-conversation');
    if (panels) panels.classList.remove('visible');
    if (conv) conv.style.display = 'flex';
  };

  window.devSelectConversation = function(el, id) {
    document.querySelectorAll('.dev-conv-item').forEach(function(i) {
      i.classList.remove('active');
    });
    el.classList.add('active');
    var panels = document.getElementById('dev-content');
    var conv = document.getElementById('dev-conversation');
    if (panels) panels.classList.remove('visible');
    if (conv) conv.style.display = 'flex';
  };

  window.devOpenProjectModal = function() {
    alert('Project Browser будет добавлен в Phase 19B');
  };

  window.devNewTask = function() {
    alert('Task Creator будет добавлен в Phase 19C');
  };

  // Escape HTML helper
  function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

});