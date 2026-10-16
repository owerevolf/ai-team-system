// Память разговора: диалог переживает обновление страницы.
//
// Зачем: Ctrl+F5 стирал переписку, и человек терял всё, о чём договорился с командой.
// Сохраняем то, что уже отрисовано, и возвращаем при следующем открытии.
// Кнопки прошлого диалога намеренно отключаются: нажимать их нельзя, и делать вид,
// что можно, — обман.
(function () {
  'use strict';

  const KEY = 'aiTeamChatHistory';
  const SAVE_LIMIT = 400000;   // бережём хранилище браузера: обрезаем очень длинные истории

  function save() {
    const chat = document.getElementById('chat');
    if (!chat) return;
    try {
      localStorage.setItem(KEY, chat.innerHTML.slice(0, SAVE_LIMIT));
    } catch (error) {
      // переполнение или приватный режим: история просто не сохранится, приложение работает
    }
  }

  function restore() {
    const chat = document.getElementById('chat');
    if (!chat || chat.children.length) return;   // живой диалог — не подменяем его

    let saved = null;
    try { saved = localStorage.getItem(KEY); } catch (error) { saved = null; }
    if (!saved) return;

    chat.innerHTML = saved;

    // Кнопки прошлого диалога мертвы: превращаем их в подписи, чтобы не обманывать.
    Array.prototype.forEach.call(chat.querySelectorAll('button'), function (button) {
      const label = document.createElement('span');
      label.style.cssText = 'opacity:.55;border:1px solid rgba(255,255,255,.15);border-radius:8px;' +
        'padding:4px 8px;margin:4px 6px 0 0;display:inline-block;font-size:12px';
      label.textContent = button.textContent;
      button.replaceWith(label);
    });

    const note = document.createElement('div');
    note.style.cssText = 'opacity:.5;font-size:12px;margin:10px 0 0 4px';
    note.textContent = 'Это продолжение прошлого разговора. Кнопки того диалога отключены — ' +
      'напиши ответ обычным сообщением или начни новый проект.';
    chat.append(note);
  }

  function start() {
    restore();
    const chat = document.getElementById('chat');
    if (!chat || !window.MutationObserver) return;

    let timer = null;
    new MutationObserver(function () {
      if (timer) clearTimeout(timer);
      timer = setTimeout(save, 400);   // не пишем на каждое изменение: ждём паузу
    }).observe(chat, { childList: true, subtree: true });
  }

  document.addEventListener('DOMContentLoaded', start);
})();
