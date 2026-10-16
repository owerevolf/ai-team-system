// Боковая панель «Проекты»: список прошлых сборок и то, что в них лежит.
//
// Зачем: история живёт на диске рядом с приложением, поэтому разговор и результат
// не исчезают вместе с вкладкой браузера. Панель можно свернуть, она не мешает чату.
(function () {
  'use strict';

  const PANEL_WIDTH = '320px';

  function h(tag, style, text) {
    const node = document.createElement(tag);
    if (style) node.style.cssText = style;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function render(session, host) {
    host.innerHTML = '';
    host.append(h('div', 'font-weight:600;margin-bottom:6px', session.name));
    host.append(h('div', 'opacity:.65;font-size:12px;margin-bottom:10px',
      session.modified + ' • файлов: ' + session.file_count));
    (session.files || []).forEach(function (name) {
      host.append(h('div', 'font-size:12px;padding:3px 0;border-bottom:1px solid rgba(255,255,255,.06)', name));
    });
    if (!session.file_count) {
      host.append(h('div', 'opacity:.6;font-size:12px;margin-top:6px',
        'Файлов нет: правки не подтверждены.'));
    }
    const open = h('button', 'margin-top:12px;padding:6px 10px;border-radius:8px;border:1px solid #444;' +
      'background:#1b1b26;color:#eee;cursor:pointer', '📂 Открыть папку');
    open.addEventListener('click', function () {
      open.disabled = true;
      fetch('/api/open_folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: session.path })
      }).then(function (response) {
        open.disabled = false;
        open.textContent = response.ok ? '📂 Открыть папку' : 'Не удалось открыть ✗';
      }).catch(function () {
        open.disabled = false;
        open.textContent = 'Не удалось открыть ✗';
      });
    });
    host.append(open);
  }

  function load(body, detail) {
    body.innerHTML = 'Загружаю…';
    fetch('/api/sessions', { cache: 'no-store' })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        body.innerHTML = '';
        const sessions = data.sessions || [];
        if (!sessions.length) {
          body.append(h('div', 'opacity:.65;font-size:13px',
            'Пока пусто: проекты появятся после первой сборки.'));
          return;
        }
        sessions.forEach(function (session) {
          const item = h('div', 'padding:8px;border-radius:8px;margin-bottom:4px;cursor:pointer;font-size:13px',
            session.name);
          item.addEventListener('mouseenter', function () { item.style.background = 'rgba(255,255,255,.06)'; });
          item.addEventListener('mouseleave', function () { item.style.background = 'transparent'; });
          item.addEventListener('click', function () { render(session, detail); });
          body.append(item);
          body.append(h('div', 'opacity:.5;font-size:11px;margin:0 0 6px 8px',
            session.modified + ' • файлов: ' + session.file_count));
        });
      })
      .catch(function (error) {
        body.innerHTML = 'Не удалось получить список: ' + error;
      });
  }

  function mount() {
    const toggler = h('button', 'position:fixed;left:14px;bottom:16px;z-index:60;padding:8px 12px;' +
      'border-radius:10px;border:1px solid #444;background:#1b1b26;color:#eee;cursor:pointer;' +
      'font:13px/1.4 system-ui', '📁 Проекты');
    const panel = h('aside', 'position:fixed;left:0;top:0;bottom:0;z-index:80;width:' + PANEL_WIDTH + ';' +
      'display:none;padding:16px;background:#15151d;color:#eee;box-shadow:8px 0 24px rgba(0,0,0,.45);' +
      'font:13px/1.4 system-ui;overflow-y:auto');
    const head = h('div', 'display:flex;justify-content:space-between;align-items:center;margin-bottom:12px');
    head.append(h('div', 'font-weight:600', 'Проекты'));
    const close = h('button', 'border:none;background:transparent;color:#eee;font-size:18px;cursor:pointer', '×');
    close.addEventListener('click', function () { panel.style.display = 'none'; });
    head.append(close);
    panel.append(head);

    const body = h('div');
    const detail = h('div', 'margin-top:14px;padding-top:12px;border-top:1px solid rgba(255,255,255,.12)');
    panel.append(body, detail);

    toggler.addEventListener('click', function () {
      const hidden = panel.style.display === 'none';
      panel.style.display = hidden ? 'block' : 'none';
      if (hidden) { load(body, detail); detail.innerHTML = ''; }
    });

    document.body.append(panel, toggler);
  }

  document.addEventListener('DOMContentLoaded', mount);
})();
