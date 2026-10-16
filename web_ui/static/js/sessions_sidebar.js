// Три колонки: слева прошлые проекты, справа код выбранного файла, в центре — разговор.
//
// Зачем: история и результат должны быть видны постоянно, а не прятаться за кнопкой.
// Панели можно свернуть; при сворачивании экран возвращается к прежнему виду.
(function () {
  'use strict';

  const LEFT_WIDTH = 300;
  const RIGHT_WIDTH = 420;

  const state = { left: true, right: true, current: null };

  function h(tag, style, text) {
    const node = document.createElement(tag);
    if (style) node.style.cssText = style;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function applyBodyShift() {
    document.body.style.marginLeft = state.left ? LEFT_WIDTH + 'px' : '0';
    document.body.style.marginRight = state.right ? RIGHT_WIDTH + 'px' : '0';
    document.body.style.transition = 'margin .15s ease';
  }

  const CODE_STYLE = 'margin:8px 0 0;padding:10px;border-radius:10px;background:#0f0f16;' +
    'white-space:pre-wrap;word-break:break-word;font:12px/1.45 ui-monospace,Consolas,monospace';

  function showFile(path, panel) {
    const body = panel.querySelector('[data-role="code-body"]');
    const title = panel.querySelector('[data-role="code-title"]');
    state.current = path;
    body.textContent = 'Загружаю…';
    fetch('/api/file?path=' + encodeURIComponent(path), { cache: 'no-store' })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        if (data.detail) {
          title.textContent = 'Код';
          body.textContent = 'Не открыть: ' + data.detail;
          return;
        }
        title.textContent = data.name + (data.truncated ? ' (первые 20 000 символов)' : '');
        body.textContent = data.content;
      })
      .catch(function (error) { body.textContent = 'Не удалось прочитать: ' + error; });
  }

  function renderSession(session, list, panel) {
    list.innerHTML = '';
    const back = h('button', 'margin-bottom:8px;padding:4px 8px;border-radius:6px;border:1px solid #444;' +
      'background:#1b1b26;color:#eee;cursor:pointer;font-size:12px', '← ко всем проектам');
    back.addEventListener('click', function () { loadSessions(list, panel); });
    list.append(back, h('div', 'font-weight:600;margin-bottom:4px', session.name));
    list.append(h('div', 'opacity:.6;font-size:11px;margin-bottom:8px',
      session.modified + ' • файлов: ' + session.file_count));

    if (!session.files || !session.files.length) {
      list.append(h('div', 'opacity:.65;font-size:12px',
        'Файлов нет: правки ещё не подтверждены в панели «Подтверждения».'));
      return;
    }
    session.files.forEach(function (name) {
      const item = h('div', 'padding:6px 8px;border-radius:6px;cursor:pointer;font-size:12px', '📄 ' + name);
      item.addEventListener('mouseenter', function () { item.style.background = 'rgba(255,255,255,.06)'; });
      item.addEventListener('mouseleave', function () { item.style.background = 'transparent'; });
      item.addEventListener('click', function () { showFile(session.path + '/' + name, panel); });
      list.append(item);
    });
  }

  function loadSessions(list, panel) {
    list.textContent = 'Загружаю…';
    fetch('/api/sessions', { cache: 'no-store' })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        const sessions = data.sessions || [];
        list.innerHTML = '';
        if (!sessions.length) {
          list.append(h('div', 'opacity:.65;font-size:12px', 'Пока пусто: проекты появятся после первой сборки.'));
          return;
        }
        sessions.forEach(function (session) {
          const item = h('div', 'padding:7px 8px;border-radius:8px;cursor:pointer;font-size:13px', session.name);
          item.addEventListener('mouseenter', function () { item.style.background = 'rgba(255,255,255,.07)'; });
          item.addEventListener('mouseleave', function () { item.style.background = 'transparent'; });
          item.addEventListener('click', function () { renderSession(session, list, panel); });
          list.append(item);
          list.append(h('div', 'opacity:.5;font-size:11px;margin:0 0 6px 8px',
            session.modified + ' • файлов: ' + session.file_count));
        });
        // Сразу показываем код свежего проекта, чтобы правая колонка не пустовала.
        const newest = sessions.find(function (s) { return s.file_count > 0; });
        if (newest && !state.current) showFile(newest.path + '/' + newest.files[0], panel);
      })
      .catch(function (error) { list.textContent = 'Не удалось получить список: ' + error; });
  }

  function panelBox(side, width) {
    return h('aside', 'position:fixed;top:0;bottom:0;' + side + ':0;width:' + width + 'px;z-index:80;' +
      'padding:14px;background:#15151d;color:#eee;overflow-y:auto;font:13px/1.45 system-ui;' +
      'box-shadow:' + (side === 'left' ? '8px 0 24px rgba(0,0,0,.45)' : '-8px 0 24px rgba(0,0,0,.45)'));
  }

  function header(title, onToggle) {
    const head = h('div', 'display:flex;justify-content:space-between;align-items:center;margin-bottom:10px');
    head.append(h('div', 'font-weight:600', title));
    const button = h('button', 'border:none;background:transparent;color:#9aa;font-size:16px;cursor:pointer', '⤢');
    button.title = 'Свернуть панель';
    button.addEventListener('click', onToggle);
    head.append(button);
    return head;
  }

  function mount() {
    // ── левая колонка: диалоги и проекты
    const left = panelBox('left', LEFT_WIDTH);
    const list = h('div');
    left.append(header('Проекты', function () { state.left = false; left.style.display = 'none'; applyBodyShift(); }),
      list);
    const leftToggle = h('button', 'position:fixed;left:10px;bottom:16px;z-index:81;padding:8px 12px;' +
      'border-radius:10px;border:1px solid #444;background:#1b1b26;color:#eee;cursor:pointer;font:13px system-ui',
      '📁 Проекты');
    leftToggle.addEventListener('click', function () {
      state.left = true;
      left.style.display = 'block';
      applyBodyShift();
      loadSessions(list, right);
    });

    // ── правая колонка: код
    const right = panelBox('right', RIGHT_WIDTH);
    right.append(header('Код', function () { state.right = false; right.style.display = 'none'; applyBodyShift(); }));
    right.append(h('div', 'opacity:.6;font-size:12px;margin-bottom:6px', 'Выбери файл в левой панели'));
    const codeTitle = h('div', 'font-weight:600;margin:6px 0 2px', 'Файл не выбран');
    codeTitle.dataset.role = 'code-title';
    right.append(codeTitle);
    const codeBody = h('pre', CODE_STYLE, 'Здесь появится код выбранного файла.');
    codeBody.dataset.role = 'code-body';
    right.append(codeBody);

    const rightToggle = h('button', 'position:fixed;right:10px;bottom:16px;z-index:81;padding:8px 12px;' +
      'border-radius:10px;border:1px solid #444;background:#1b1b26;color:#eee;cursor:pointer;font:13px system-ui',
      '</> Код');
    rightToggle.addEventListener('click', function () {
      state.right = true;
      right.style.display = 'block';
      applyBodyShift();
    });

    document.body.append(left, leftToggle, right, rightToggle);
    applyBodyShift();
    loadSessions(list, right);
  }

  document.addEventListener('DOMContentLoaded', mount);
})();
