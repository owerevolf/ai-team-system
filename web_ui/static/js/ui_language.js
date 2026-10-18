// Надписи интерфейса на выбранном языке: меняем только текст, разметку не трогаем.
// Зачем: английский гость видел русские кнопки «Подтверждения», «Словарь», «Сцена».
(function () {
  'use strict';

  const EN = {
    '💬 Чат': '💬 Chat',
    '💻 Код': '💻 Code',
    '⚙️ Настройки': '⚙️ Settings',
    '📖 Инструкция': '📖 Guide',
    '📋 Канбан': '📋 Kanban',
    '📋 Проект': '📋 Project',
    '✅ Подтверждения': '✅ Approvals',
    '🎬 Сцена': '🎬 Scene',
    '📖 Словарь': '📖 Glossary',
    '🗑 Очистить': '🗑 Clear',
    '📥 Экспорт': '📥 Export',
    '✨ Новый проект': '✨ New project'
  };

  function apply() {
    let language = 'ru';
    try {
      language = localStorage.getItem('aiTeamLang') || 'ru';
    } catch (error) {
      language = 'ru';
    }
    if (language !== 'en') return;

    Array.prototype.forEach.call(document.querySelectorAll('button, .tab-btn'), function (node) {
      const text = (node.textContent || '').trim();
      if (EN[text]) node.textContent = EN[text];
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    apply();
    // Интерфейс перерисовывается сам — возвращаем перевод на место.
    new MutationObserver(apply).observe(document.body, { childList: true, subtree: true });
  });
})();
