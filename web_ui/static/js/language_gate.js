// Первый экран: выбор языка с флагами.
//
// Зачем: до этого язык интерфейса и ответов модели нигде не выбирался,
// и ассистент мог уйти в английский посреди русского диалога.
// Выбор запоминается в localStorage (чтобы не спрашивать каждый раз)
// и уходит на сервер, чтобы модель отвечала на том же языке.
(function () {
  'use strict';

  const STORAGE_KEY = 'aiTeamLang';

  const LANGUAGES = [
    { code: 'ru', flag: '🇷🇺', title: 'Русский',  hint: 'Ответы и подписи по-русски' },
    { code: 'en', flag: '🇬🇧', title: 'English', hint: 'Answers and labels in English' },
  ];

  function save(language) {
    try { localStorage.setItem(STORAGE_KEY, language); } catch (error) { /* приватный режим — не беда */ }
    return fetch('/api/ui/language', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lang: language }),
    }).catch(function () { /* сервер недоступен: выбор всё равно останется в браузере */ });
  }

  function chosen() {
    try { return localStorage.getItem(STORAGE_KEY); } catch (error) { return null; }
  }

  function build(overlay) {
    overlay.style.cssText = 'position:fixed;inset:0;z-index:200;display:flex;align-items:center;' +
      'justify-content:center;background:rgba(10,10,16,.92);font:15px/1.5 system-ui';
    const card = document.createElement('div');
    card.style.cssText = 'max-width:420px;padding:28px;border-radius:18px;background:#15151d;color:#eee;' +
      'box-shadow:0 18px 48px rgba(0,0,0,.55);text-align:center';
    card.innerHTML = '<div style="font-size:19px;font-weight:600;margin-bottom:6px">Выбери язык</div>' +
      '<div style="opacity:.65;margin-bottom:16px">Choose your language</div>';

    LANGUAGES.forEach(function (item) {
      const button = document.createElement('button');
      button.type = 'button';
      button.style.cssText = 'display:flex;gap:12px;align-items:center;width:100%;margin:8px 0;padding:12px 14px;' +
        'border-radius:12px;border:1px solid #3a3a4a;background:#1b1b26;color:#eee;cursor:pointer;text-align:left';
      button.innerHTML = '<span style="font-size:22px">' + item.flag + '</span>' +
        '<span><b>' + item.title + '</b><br><span style="opacity:.6">' + item.hint + '</span></span>';
      button.addEventListener('click', function () {
        button.disabled = true;
        save(item.code).then(function () { location.reload(); });
      });
      card.append(button);
    });

    card.append(Object.assign(document.createElement('div'), {
      style: 'opacity:.45;font-size:12px;margin-top:10px',
      textContent: 'Выбор можно изменить позже в настройках',
    }));
    overlay.append(card);
  }

  function start() {
    if (chosen()) return;           // язык уже выбран — первый экран не мешает
    const overlay = document.createElement('div');
    build(overlay);
    document.body.append(overlay);
  }

  document.addEventListener('DOMContentLoaded', start);
})();
