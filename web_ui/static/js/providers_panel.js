// Блок «Проверка провайдеров» внутри вкладки «Настройки».
//
// Почему так: содержимое вкладки перерисовывается целиком, поэтому плавающая кнопка
// осталась бы поверх интерфейса, а прямая вставка стиралась бы при каждом открытии.
// Здесь блок добавляется в конец #settings-content после каждой перерисовки.
// Ключи не показываются: сервер отвечает только «доступно / нет ключа / не отвечает».
(function () {
  'use strict';

  const HOST_ID = 'settings-content';
  const BLOCK_ROLE = 'providers-block';

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

  function render(body, data) {
    const probe = data.probe || {};
    const rows = (data.providers || []).map(function (p) { return row(p, probe[p.id]); }).join('');
    const free = (data.free_available || []).join(', ') || '—';
    body.innerHTML = rows +
      '<div style="opacity:.7;margin-top:8px">Доступны без ключа: ' + free + '</div>' +
      '<div style="opacity:.6;margin-top:6px;font-size:12px">Ключ кладётся в .env; сам ключ не показывается</div>' +
      '<button type="button" data-role="refresh" style="margin-top:10px;padding:6px 10px;border-radius:8px;' +
      'border:1px solid #444;background:#1b1b26;color:#eee;cursor:pointer">Проверить заново</button>';
    const refresh = body.querySelector('[data-role="refresh"]');
    if (refresh) refresh.addEventListener('click', function () { load(body, true); });
  }

  async function load(body, refresh) {
    body.innerHTML = refresh ? 'Проверяю провайдеров…' : 'Загружаю…';
    try {
      const response = await fetch('/api/providers' + (refresh ? '?refresh=1' : ''), { cache: 'no-store' });
      render(body, await response.json());
    } catch (error) {
      body.innerHTML = 'Не удалось получить список: ' + error;
    }
  }

  function attach() {
    const host = document.getElementById(HOST_ID);
    if (!host || host.querySelector('[data-role="' + BLOCK_ROLE + '"]')) return;

    const block = document.createElement('section');
    block.dataset.role = BLOCK_ROLE;
    block.style.cssText = 'margin-top:18px;padding:14px;border-radius:12px;background:rgba(255,255,255,.04)';
    block.innerHTML = '<div style="font-weight:600;margin-bottom:8px">Проверка провайдеров</div>' +
      '<div data-role="providers-body">Загружаю…</div>';
    host.append(block);

    load(block.querySelector('[data-role="providers-body"]'), false);
  }

  function start() {
    attach();
    // Вкладка перерисовывается из JS: следим и возвращаем блок на место.
    new MutationObserver(attach).observe(document.body, { childList: true, subtree: true });
  }

  document.addEventListener('DOMContentLoaded', start);
})();
