// Панель «Провайдеры»: какие облачные модели доступны и что мешает.
// Ключи нигде не отображаются — сервер отвечает только «доступно / нет ключа / не отвечает».
(function () {
  'use strict';

  const STATUS = {
    ok: { text: 'доступно', color: '#22c55e' },
    no_key: { text: 'нет ключа', color: '#f59e0b' },
    error: { text: 'не отвечает', color: '#ef4444' },
  };

  function stateOf(probe) {
    if (!probe || Object.keys(probe).length === 0) return 'error';
    if (probe.available) return 'ok';
    return String(probe.note || '').indexOf('ключ') >= 0 ? 'no_key' : 'error';
  }

  function row(provider, probe) {
    const meta = STATUS[stateOf(probe)] || STATUS.error;
    const note = (probe && probe.note) || provider.how || '';
    return '<div style="display:flex;gap:8px;margin:6px 0">' +
      '<span style="color:' + meta.color + ';min-width:86px">' + meta.text + '</span>' +
      '<b>' + (provider.name || provider.id) + '</b>' +
      '<span style="opacity:.7">' + note + '</span></div>';
  }

  function render(box, data) {
    const probe = data.probe || {};
    const rows = (data.providers || []).map(function (p) { return row(p, probe[p.id]); }).join('');
    const free = (data.free_available || []).join(', ') || '—';
    box.innerHTML =
      '<div style="font-weight:600;margin-bottom:6px">Провайдеры облачных моделей</div>' +
      rows +
      '<div style="opacity:.7;margin-top:8px">Доступны без ключа: ' + free + '</div>' +
      '<div style="opacity:.6;margin-top:6px;font-size:12px">Ключ кладётся в .env; сам ключ не показывается</div>' +
      '<button type="button" data-role="refresh" style="margin-top:10px;padding:6px 10px;border-radius:8px;' +
      'border:1px solid #444;background:#1b1b26;color:#eee;cursor:pointer">Проверить заново</button>';
    const refresh = box.querySelector('[data-role="refresh"]');
    if (refresh) refresh.addEventListener('click', function () { load(box, true); });
  }

  async function load(box, refresh) {
    box.innerHTML = refresh ? 'Проверяю провайдеров…' : 'Загружаю…';
    try {
      const response = await fetch('/api/providers' + (refresh ? '?refresh=1' : ''), { cache: 'no-store' });
      render(box, await response.json());
    } catch (error) {
      box.innerHTML = 'Не удалось получить список: ' + error;
    }
  }

  function mount() {
    const host = document.createElement('div');
    host.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:60;font:13px/1.4 system-ui;text-align:right';

    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = '🔌 Провайдеры';
    button.style.cssText = 'padding:8px 12px;border-radius:10px;border:1px solid #444;background:#1b1b26;color:#eee;cursor:pointer';

    const box = document.createElement('div');
    box.style.cssText = 'display:none;max-width:430px;margin-top:8px;padding:12px;border-radius:12px;' +
      'background:#15151d;color:#eee;box-shadow:0 8px 24px rgba(0,0,0,.4);text-align:left';

    button.addEventListener('click', function () {
      const hidden = box.style.display === 'none';
      box.style.display = hidden ? 'block' : 'none';
      if (hidden) load(box, false);
    });

    host.append(box, button);
    document.body.append(host);
  }

  document.addEventListener('DOMContentLoaded', mount);
})();
