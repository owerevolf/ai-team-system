/**
 * «Сцена» — наглядная схема команды: кто чем занимается и как зависит от других.
 *
 * Виджет самодостаточный: сам создаёт кнопку, панель и схему (HTML-узлы + SVG-стрелки).
 * Живые данные берутся из канбана (/api/kanban/tasks) и обновляются раз в несколько секунд.
 *
 * Честно про данные: это счётчики задач из канбана, а не поток событий в реальном времени.
 * Живой поток (SSE) ведёт основной чат; сюда его подключим, когда сцена станет частью чата.
 */
(function () {
    'use strict';

    var AGENTS = [
        {id: 'teamlead', name: 'TeamLead', role: 'координирует и распределяет задачи', x: 8, y: 168, accent: true},
        {id: 'architect', name: 'Architect', role: 'решает, как устроен проект', x: 236, y: 28},
        {id: 'backend', name: 'Backend', role: 'логика, данные, API', x: 236, y: 140},
        {id: 'frontend', name: 'Frontend', role: 'интерфейс и вёрстка', x: 236, y: 252},
        {id: 'devops', name: 'DevOps', role: 'запуск, окружение, сборка', x: 236, y: 364},
        {id: 'tester', name: 'Tester', role: 'проверяет, что всё работает', x: 470, y: 140},
        {id: 'documentalist', name: 'Documentalist', role: 'объясняет проект человеку', x: 668, y: 140}
    ];

    var EDGES = [
        ['teamlead', 'architect'], ['teamlead', 'backend'], ['teamlead', 'frontend'], ['teamlead', 'devops'],
        ['architect', 'backend'], ['architect', 'frontend'], ['architect', 'devops'],
        ['backend', 'tester'], ['frontend', 'tester'], ['devops', 'tester'],
        ['tester', 'documentalist']
    ];

    var NODE_W = 168, NODE_H = 62, SCENE_W = 850, SCENE_H = 440;
    var REFRESH_MS = 6000;

    var state = {tasks: [], byAgent: {}, selected: null, timer: null, open: false};

    var CSS = [
        '#sceneFab{position:fixed;right:160px;bottom:22px;z-index:9998;border:none;cursor:pointer;',
        'padding:12px 18px;border-radius:999px;font:600 14px Segoe UI,system-ui,sans-serif;',
        'background:#2a3350;color:#e6e8ef;box-shadow:0 8px 24px rgba(0,0,0,.4)}',
        '#sceneFab:hover{background:#39446b}',
        '#scenePanel{position:fixed;left:50%;transform:translateX(-50%);bottom:78px;z-index:9999;',
        'width:880px;max-width:calc(100vw - 40px);max-height:78vh;display:none;flex-direction:column;',
        'background:#151a23;color:#e6e8ef;border:1px solid #262d3d;border-radius:14px;',
        'box-shadow:0 18px 48px rgba(0,0,0,.6);font:14px/1.45 Segoe UI,system-ui,sans-serif;overflow:hidden}',
        '#scenePanel.open{display:flex}',
        '.sc-head{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid #262d3d}',
        '.sc-title{font-weight:600}',
        '.sc-close{background:none;border:none;color:#8b93a7;font-size:20px;cursor:pointer;line-height:1}',
        '.sc-body{padding:14px 16px;overflow:auto}',
        '.sc-stage{position:relative;width:850px;height:440px;transform-origin:top left}',
        '.sc-node{position:absolute;box-sizing:border-box;border-radius:12px;padding:10px 12px;cursor:pointer;',
        'background:#1b2130;border:1px solid #39415a;transition:border-color .15s, box-shadow .15s}',
        '.sc-node:hover{border-color:#5b6bd6}',
        '.sc-node.accent{background:#2a2f57;border-color:#4f46e5}',
        '.sc-node.active{border-color:#7c8cff;box-shadow:0 0 0 2px rgba(124,140,255,.35)}',
        '.sc-node.selected{border-color:#ffb86b;box-shadow:0 0 0 2px rgba(255,184,107,.35)}',
        '.sc-name{font-weight:600;color:#fff;margin-bottom:2px}',
        '.sc-role{font-size:12px;color:#98a0b5;line-height:1.3}',
        '.sc-badge{position:absolute;top:-8px;right:-6px;min-width:20px;text-align:center;padding:2px 6px;',
        'border-radius:999px;background:#4f46e5;color:#fff;font-size:11px;font-weight:600}',
        '.sc-card{margin-top:14px;padding:12px 14px;border-radius:12px;background:#1a2030;border:1px solid #2a3350}',
        '.sc-card h4{margin:0 0 6px;font-size:15px;color:#fff}',
        '.sc-card .muted{color:#8b93a7;font-size:12px}',
        '.sc-task{padding:6px 8px;border-radius:8px;background:#151a23;border:1px solid #232a3a;margin-top:6px;font-size:13px}',
        '.sc-note{margin-top:10px;color:#8b93a7;font-size:12px}'
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
            } else if (key === 'style') {
                node.setAttribute('style', attrs[key]);
            } else {
                node.setAttribute(key, attrs[key]);
            }
        });
        if (text !== undefined && text !== null) {
            node.textContent = text;
        }
        return node;
    }

    function byId(id) {
        for (var i = 0; i < AGENTS.length; i++) {
            if (AGENTS[i].id === id) {
                return AGENTS[i];
            }
        }
        return null;
    }

    function arrows() {
        var parts = ['<svg width="' + SCENE_W + '" height="' + SCENE_H + '" style="position:absolute;left:0;top:0;pointer-events:none">',
            '<defs><marker id="scArrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">',
            '<path d="M 0 0 L 10 5 L 0 10 z" fill="#7c8cff"/></marker></defs>'];
        EDGES.forEach(function (edge) {
            var from = byId(edge[0]);
            var to = byId(edge[1]);
            if (!from || !to) {
                return;
            }
            var x1 = from.x + NODE_W;
            var y1 = from.y + NODE_H / 2;
            var x2 = to.x;
            var y2 = to.y + NODE_H / 2;
            var midX = (x1 + x2) / 2;
            var path = 'M ' + x1 + ' ' + y1 + ' L ' + midX + ' ' + y1 + ' L ' + midX + ' ' + y2 + ' L ' + x2 + ' ' + y2;
            parts.push('<path d="' + path + '" fill="none" stroke="#7c8cff" stroke-width="1.6" opacity="0.7" marker-end="url(#scArrow)"/>');
        });
        parts.push('</svg>');
        return parts.join('');
    }

    function renderScene(stage) {
        stage.innerHTML = arrows();
        AGENTS.forEach(function (agent) {
            var active = (state.byAgent[agent.id] || 0) > 0;
            var node = h('div', {
                class: 'sc-node' + (agent.accent ? ' accent' : '') + (active ? ' active' : '') + (state.selected === agent.id ? ' selected' : ''),
                style: 'left:' + agent.x + 'px;top:' + agent.y + 'px;width:' + NODE_W + 'px;height:' + NODE_H + 'px',
                'data-agent': agent.id
            });
            node.appendChild(h('div', {class: 'sc-name'}, agent.name));
            node.appendChild(h('div', {class: 'sc-role'}, agent.role));
            if (active) {
                node.appendChild(h('div', {class: 'sc-badge'}, String(state.byAgent[agent.id])));
            }
            node.addEventListener('click', function () {
                state.selected = state.selected === agent.id ? null : agent.id;
                renderScene(stage);
                renderCard();
            });
            stage.appendChild(node);
        });
    }

    function renderCard() {
        var card = document.getElementById('scCard');
        if (!card) {
            return;
        }
        card.innerHTML = '';
        if (!state.selected) {
            card.appendChild(h('div', {class: 'muted'}, 'Нажми на специалиста — покажу, что он делает и какие у него задачи.'));
            return;
        }
        var agent = byId(state.selected);
        card.appendChild(h('h4', {}, agent.name));
        card.appendChild(h('div', {class: 'sc-role'}, agent.role));

        var tasks = state.tasks.filter(function (task) {
            return String(task.agent || '').toLowerCase() === agent.id;
        });
        if (!tasks.length) {
            card.appendChild(h('div', {class: 'muted', style: 'margin-top:6px'},
                'Задач в канбане нет — значит, сейчас этот специалист свободен.'));
            return;
        }
        tasks.slice(0, 5).forEach(function (task) {
            var column = task.column_id || task.status || '';
            card.appendChild(h('div', {class: 'sc-task'},
                (task.title || 'задача без названия') + (column ? '  ·  ' + column : '')));
        });
        if (tasks.length > 5) {
            card.appendChild(h('div', {class: 'muted'}, 'и ещё ' + (tasks.length - 5) + '…'));
        }
    }

    function refresh() {
        fetch('/api/kanban/tasks')
            .then(function (response) {
                return response.ok ? response.json() : {tasks: []};
            })
            .then(function (data) {
                state.tasks = data.tasks || [];
                var counts = {};
                state.tasks.forEach(function (task) {
                    var agent = String(task.agent || '').toLowerCase();
                    counts[agent] = (counts[agent] || 0) + 1;
                });
                state.byAgent = counts;
                var stage = document.getElementById('scStage');
                if (stage) {
                    renderScene(stage);
                }
                renderCard();
            })
            .catch(function () {
                /* канбан недоступен — сцена остаётся рабочей, просто без счётчиков */
            });
    }

    function build() {
        if (document.getElementById('sceneFab')) {
            return;
        }
        style();

        var fab = h('button', {id: 'sceneFab', title: 'Сцена: кто что делает'}, '🎬 Сцена');
        var panel = h('div', {id: 'scenePanel'});

        var head = h('div', {class: 'sc-head'});
        head.appendChild(h('div', {class: 'sc-title'}, 'Сцена: команда и её работа'));
        var close = h('button', {class: 'sc-close', title: 'Закрыть'}, '×');
        head.appendChild(close);
        panel.appendChild(head);

        var body = h('div', {class: 'sc-body'});
        var holder = h('div', {style: 'width:100%;overflow:auto'});
        var stage = h('div', {class: 'sc-stage', id: 'scStage'});
        holder.appendChild(stage);
        body.appendChild(holder);

        var card = h('div', {class: 'sc-card', id: 'scCard'});
        body.appendChild(card);
        body.appendChild(h('div', {class: 'sc-note'},
            'Счётчики — из канбана, обновление раз в 6 секунд. Поток событий в реальном времени подключим, когда сцена станет частью чата.'));

        panel.appendChild(body);
        document.body.appendChild(fab);
        document.body.appendChild(panel);

        function toggle(open) {
            state.open = open === undefined ? !state.open : open;
            panel.classList.toggle('open', state.open);
            if (state.open) {
                refresh();
                if (!state.timer) {
                    state.timer = setInterval(refresh, REFRESH_MS);
                }
            } else if (state.timer) {
                clearInterval(state.timer);
                state.timer = null;
            }
        }

        fab.addEventListener('click', function () {
            toggle();
        });
        close.addEventListener('click', function () {
            toggle(false);
        });
        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                toggle(false);
            }
        });

        renderScene(stage);
        renderCard();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', build);
    } else {
        build();
    }
})();
