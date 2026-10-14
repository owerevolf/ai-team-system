/**
 * Словарь терминов и проверка фактов («агент истины»).
 *
 * Виджет самодостаточный: сам создаёт кнопку и панель, стили внутри, ничего
 * не требует от welcome.js. Подключается одной строкой в welcome.html.
 *
 * Данные:
 *   GET  /api/glossary                 — список терминов
 *   GET  /api/glossary/explain?term=…  — объяснение одного термина
 *   POST /api/truth/ask                — факты о коде со ссылками файл:строка
 *   POST /api/truth/verify             — поиск выдуманных имён в тексте
 */
(function () {
    'use strict';

    var state = {terms: null, loading: false, open: false, tab: 'glossary'};

    // Подписи берём из общего модуля проекта (/api/i18n), чтобы не переводить их в JS.
    var translations = {};

    function t(key, fallback) {
        var value = translations[key];
        return value === undefined || value === null ? fallback : value;
    }

    function detectLanguage() {
        var lang = (navigator.language || 'ru').toLowerCase();
        return lang.indexOf('ru') === 0 ? 'ru' : 'en';
    }

    function loadTranslations(done) {
        fetch('/api/i18n?lang=' + detectLanguage())
            .then(function (response) {
                return response.ok ? response.json() : {};
            })
            .then(function (data) {
                translations = (data && data.translations) || {};
            })
            .catch(function () {
                translations = {};
            })
            .then(function () {
                if (typeof done === 'function') {
                    done();
                }
            });
    }

    var CSS = [
        '#glossaryFab{position:fixed;right:22px;bottom:22px;z-index:9998;border:none;cursor:pointer;',
        'padding:12px 18px;border-radius:999px;font:600 14px Segoe UI,system-ui,sans-serif;',
        'background:#4f46e5;color:#fff;box-shadow:0 8px 24px rgba(79,70,229,.45)}',
        '#glossaryFab:hover{background:#5b53ff}',
        '#glossaryPanel{position:fixed;right:22px;bottom:78px;z-index:9999;width:400px;max-width:calc(100vw - 44px);',
        'max-height:70vh;display:none;flex-direction:column;background:#151a23;color:#e6e8ef;',
        'border:1px solid #262d3d;border-radius:14px;box-shadow:0 18px 48px rgba(0,0,0,.55);',
        'font:14px/1.45 Segoe UI,system-ui,sans-serif;overflow:hidden}',
        '#glossaryPanel.open{display:flex}',
        '.gp-head{display:flex;align-items:center;justify-content:space-between;padding:12px 14px;border-bottom:1px solid #262d3d}',
        '.gp-title{font-weight:600}',
        '.gp-close{background:none;border:none;color:#8b93a7;font-size:18px;cursor:pointer;line-height:1}',
        '.gp-tabs{display:flex;gap:6px;padding:10px 12px 0}',
        '.gp-tab{flex:1;padding:8px 10px;border-radius:8px;border:1px solid #262d3d;background:#1b2130;color:#98a0b5;cursor:pointer;font-size:13px}',
        '.gp-tab.active{background:#2a3350;color:#fff;border-color:#3c4778}',
        '.gp-body{padding:12px 14px 14px;overflow:auto}',
        '.gp-input{width:100%;box-sizing:border-box;padding:9px 11px;border-radius:9px;border:1px solid #2c3448;',
        'background:#0f1115;color:#e6e8ef;font:13px Segoe UI,system-ui,sans-serif;margin-bottom:10px}',
        '.gp-btn{width:100%;padding:9px 11px;border-radius:9px;border:none;background:#4f46e5;color:#fff;cursor:pointer;font-weight:600;margin-bottom:8px}',
        '.gp-btn.secondary{background:#2a3350}',
        '.gp-item{padding:9px 10px;border-radius:9px;border:1px solid #232a3a;background:#1a2030;margin-bottom:7px;cursor:pointer}',
        '.gp-item:hover{border-color:#3c4778}',
        '.gp-term{font-weight:600;color:#fff}',
        '.gp-hint{color:#8b93a7;font-size:12px;margin-top:4px}',
        '.gp-plain{color:#cfd4e4;margin:8px 0}',
        '.gp-muted{color:#8b93a7;font-size:12px}',
        '.gp-src{font-family:Consolas,monospace;font-size:12px;color:#7c8cff}',
        '.gp-empty{padding:10px;border-radius:9px;background:#241f1a;color:#ffb86b;font-size:13px}',
        '.gp-bad{color:#ff8f8f}'
    ].join('');

    function style() {
        var tag = document.createElement('style');
        tag.textContent = CSS;
        document.head.appendChild(tag);
    }

    function h(tag, attrs, text) {
        var node = document.createElement(tag);
        Object.keys(attrs || {}).forEach(function (key) {
            if (key === 'class') {
                node.className = attrs[key];
            } else if (key === 'html') {
                node.innerHTML = attrs[key];
            } else {
                node.setAttribute(key, attrs[key]);
            }
        });
        if (text) {
            node.textContent = text;
        }
        return node;
    }

    function fetchJson(url, options) {
        return fetch(url, options).then(function (response) {
            if (!response.ok) {
                throw new Error('HTTP ' + response.status);
            }
            return response.json();
        });
    }

    // ── вкладка «Словарь» ────────────────────────────────────────────────────
    function renderGlossary(body) {
        body.innerHTML = '';
        if (state.loading) {
            body.appendChild(h('div', {class: 'gp-muted'}, 'Загружаю словарь…'));
            return;
        }
        if (!state.terms) {
            body.appendChild(h('div', {class: 'gp-muted'}, 'Словарь пока не загружен.'));
            return;
        }

        var search = h('input', {class: 'gp-input', type: 'text', placeholder: t('widget_search_placeholder', 'Найти термин (например: коммит)')});
        body.appendChild(search);

        var list = h('div', {});
        body.appendChild(list);

        function paint(query) {
            list.innerHTML = '';
            var needle = (query || '').trim().toLowerCase();
            var found = state.terms.filter(function (item) {
                if (!needle) {
                    return true;
                }
                var names = [item.term].concat(item.aliases || []);
                return names.some(function (name) {
                    return String(name).toLowerCase().indexOf(needle) !== -1;
                });
            });

            if (!found.length) {
                list.appendChild(h('div', {class: 'gp-muted'}, 'Ничего не нашлось. Попробуй другое слово.'));
                return;
            }

            found.slice(0, 40).forEach(function (item) {
                var row = h('div', {class: 'gp-item'});
                row.appendChild(h('div', {class: 'gp-term'}, item.term));
                row.appendChild(h('div', {class: 'gp-plain'}, item.simple || ''));

                var details = h('div', {class: 'gp-hint', style: 'display:none'});
                if (item.exact) {
                    details.appendChild(h('div', {}, 'Точно: ' + item.exact));
                }
                if (item.example) {
                    details.appendChild(h('div', {}, 'Пример: ' + item.example));
                }
                if (item.related && item.related.length) {
                    details.appendChild(h('div', {}, 'Связанные: ' + item.related.join(', ')));
                }
                row.appendChild(details);
                row.appendChild(h('div', {class: 'gp-hint'}, 'нажми, чтобы раскрыть'));

                row.addEventListener('click', function () {
                    details.style.display = details.style.display === 'none' ? 'block' : 'none';
                });
                list.appendChild(row);
            });
        }

        search.addEventListener('input', function () {
            paint(search.value);
        });
        paint('');
        search.focus();
    }

    // ── вкладка «Проверить факты» ────────────────────────────────────────────
    function renderTruth(body) {
        body.innerHTML = '';
        body.appendChild(h('div', {class: 'gp-hint'}, t('widget_truth_hint', 'Спроси что-нибудь о коде проекта — ответ придёт со ссылкой файл:строка.')));

        var input = h('textarea', {class: 'gp-input', rows: '3', placeholder: t('widget_search_placeholder', 'Найти термин (например: коммит)')});
        body.appendChild(input);

        var askBtn = h('button', {class: 'gp-btn'}, t('widget_btn_find_facts', 'Найти факты'));
        var verifyBtn = h('button', {class: 'gp-btn secondary'}, t('widget_btn_verify', 'Проверить текст на выдумки'));
        body.appendChild(askBtn);
        body.appendChild(verifyBtn);

        var result = h('div', {});
        body.appendChild(result);

        function mount() {
            input.style.height = '72px';
        }
        mount();

        askBtn.addEventListener('click', function () {
            var question = input.value.trim();
            if (!question) {
                return;
            }
            result.innerHTML = '';
            result.appendChild(h('div', {class: 'gp-muted'}, 'Ищу…'));
            fetchJson('/api/truth/ask', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({question: question})
            }).then(function (data) {
                result.innerHTML = '';
                if (!data.found) {
                    result.appendChild(h('div', {class: 'gp-empty'}, 'В коде этого нет — не выдумываю. Попробуй назвать функцию, файл или маршрут.'));
                    return;
                }
                data.facts.forEach(function (fact) {
                    var row = h('div', {class: 'gp-item'});
                    row.appendChild(h('div', {class: 'gp-term'}, fact.name + '  (' + fact.kind + ')'));
                    row.appendChild(h('div', {class: 'gp-src'}, fact.source));
                    if (fact.reason) {
                        row.appendChild(h('div', {class: 'gp-hint'}, fact.reason));
                    }
                    result.appendChild(row);
                });
            }).catch(function (error) {
                result.innerHTML = '';
                result.appendChild(h('div', {class: 'gp-empty'}, 'Ошибка запроса: ' + error.message));
            });
        });

        verifyBtn.addEventListener('click', function () {
            var text = input.value.trim();
            if (!text) {
                return;
            }
            result.innerHTML = '';
            fetchJson('/api/truth/verify', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: text})
            }).then(function (data) {
                result.innerHTML = '';
                if (!data.unverified) {
                    result.appendChild(h('div', {class: 'gp-item'}, 'Все имена найдены в репозитории.'));
                    return;
                }
                result.appendChild(h('div', {class: 'gp-empty'}, 'Не подтверждено в репозитории: ' + data.unverified));
                data.issues.forEach(function (issue) {
                    result.appendChild(h('div', {class: 'gp-item gp-bad'}, issue.name));
                });
            }).catch(function (error) {
                result.innerHTML = '';
                result.appendChild(h('div', {class: 'gp-empty'}, 'Ошибка запроса: ' + error.message));
            });
        });
    }

    function loadTerms() {
        if (state.terms || state.loading) {
            return;
        }
        state.loading = true;
        fetchJson('/api/glossary').then(function (data) {
            state.terms = data.terms || [];
        }).catch(function () {
            state.terms = [];
        }).then(function () {
            state.loading = false;
            if (state.open && state.tab === 'glossary') {
                renderGlossary(body);
            }
        });
    }

    var body;

    function switchTab(tab) {
        state.tab = tab;
        tabs.forEach(function (node) {
            node.classList.toggle('active', node.dataset.tab === tab);
        });
        if (tab === 'glossary') {
            loadTerms();
            renderGlossary(body);
        } else {
            renderTruth(body);
        }
    }

    var tabs = [];

    function build() {
        if (document.getElementById('glossaryFab')) {
            return;
        }
        style();
        loadTranslations(buildUi);
    }

    function buildUi() {
        var fab = h('button', {
            id: 'glossaryFab',
            title: t('widget_glossary_btn_title', 'Словарь терминов и агент истины')
        }, t('widget_glossary_btn', '📖 Словарь'));
        var panel = h('div', {id: 'glossaryPanel'});

        var head = h('div', {class: 'gp-head'});
        head.appendChild(h('div', {class: 'gp-title'}, t('widget_glossary_title', 'Словарь и факты')));
        var close = h('button', {class: 'gp-close', title: 'Закрыть'}, '×');
        head.appendChild(close);
        panel.appendChild(head);

        var tabBar = h('div', {class: 'gp-tabs'});
        var tabGlossary = h('button', {class: 'gp-tab active'}, t('widget_tab_glossary', 'Словарь терминов'));
        tabGlossary.dataset.tab = 'glossary';
        var tabTruth = h('button', {class: 'gp-tab'}, t('widget_tab_truth', 'Проверить факты'));
        tabTruth.dataset.tab = 'truth';
        tabs = [tabGlossary, tabTruth];
        tabBar.appendChild(tabGlossary);
        tabBar.appendChild(tabTruth);
        panel.appendChild(tabBar);

        body = h('div', {class: 'gp-body'});
        panel.appendChild(body);

        document.body.appendChild(fab);
        document.body.appendChild(panel);

        function toggle(open) {
            state.open = open === undefined ? !state.open : open;
            panel.classList.toggle('open', state.open);
            if (state.open) {
                switchTab(state.tab);
            }
        }

        fab.addEventListener('click', function () {
            toggle();
        });
        close.addEventListener('click', function () {
            toggle(false);
        });
        tabGlossary.addEventListener('click', function () {
            switchTab('glossary');
        });
        tabTruth.addEventListener('click', function () {
            switchTab('truth');
        });
        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                toggle(false);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', build);
    } else {
        build();
    }
})();
