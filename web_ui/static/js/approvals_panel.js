/**
 * Панель подтверждений: человек решает, применять ли правку.
 *
 * Работает с существующими роутами Developer Mode:
 *   GET  /api/developer/approvals        — очередь запросов
 *   POST /api/developer/approvals/action — {request_id, action: 'approve'|'reject', comments}
 *
 * Виджет самодостаточный: сам создаёт кнопку и панель, стили внутри.
 * Правило проекта: изменения применяются только после решения человека.
 */
(function () {
    'use strict';

    var REFRESH_MS = 5000;
    var state = {open: false, timer: null, items: [], busy: false};

    var CSS = [
        '#approvalsFab{position:fixed;right:300px;bottom:22px;z-index:9998;border:none;cursor:pointer;',
        'padding:12px 18px;border-radius:999px;font:600 14px Segoe UI,system-ui,sans-serif;',
        'background:#1f3d2b;color:#d7ffe6;box-shadow:0 8px 24px rgba(0,0,0,.4)}',
        '#approvalsFab:hover{background:#2a5238}',
        '#approvalsFab.has-items{background:#2f7d4f;color:#fff}',
        '#approvalsPanel{position:fixed;right:22px;bottom:78px;z-index:9999;width:460px;max-width:calc(100vw - 44px);',
        'max-height:70vh;display:none;flex-direction:column;background:#151a23;color:#e6e8ef;',
        'border:1px solid #262d3d;border-radius:14px;box-shadow:0 18px 48px rgba(0,0,0,.55);',
        'font:14px/1.45 Segoe UI,system-ui,sans-serif;overflow:hidden}',
        '#approvalsPanel.open{display:flex}',
        '.ap-head{display:flex;align-items:center;justify-content:space-between;padding:12px 14px;border-bottom:1px solid #262d3d}',
        '.ap-close{background:none;border:none;color:#8b93a7;font-size:18px;cursor:pointer;line-height:1}',
        '.ap-body{padding:12px 14px;overflow:auto}',
        '.ap-item{border:1px solid #2a3350;border-radius:10px;padding:10px 12px;margin-bottom:10px;background:#1a2030}',
        '.ap-title{font-weight:600;color:#fff;margin-bottom:4px}',
        '.ap-note{font-size:12px;color:#d9b26a;margin-bottom:6px}',
        '.ap-meta{font-size:12px;color:#8b93a7;margin-bottom:8px}',
        '.ap-actions{display:flex;gap:8px}',
        '.ap-btn{flex:1;padding:8px 10px;border:none;border-radius:8px;cursor:pointer;font-weight:600;font-size:13px}',
        '.ap-approve{background:#2f7d4f;color:#fff}',
        '.ap-reject{background:#5a2733;color:#ffd9df}',
        '.ap-empty{padding:12px;border-radius:9px;background:#1a2030;color:#8b93a7;font-size:13px}',
        '.ap-status{margin-top:8px;font-size:12px;color:#7c8cff}'
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
            } else {
                node.setAttribute(key, attrs[key]);
            }
        });
        if (text !== undefined && text !== null) {
            node.textContent = text;
        }
        return node;
    }

    function fetchJson(url, options) {
        return fetch(url, options).then(function (response) {
            return response.json().then(function (data) {
                return {ok: response.ok, data: data};
            });
        });
    }

    function describe(item) {
        return item.description || item.summary || item.title || item.patch_id || 'правка без описания';
    }

    function formatTime(value) {
        // Сервер отдаёт время в UTC: показываем в местном, чтобы было понятно,
        // когда именно появилась правка.
        const date = new Date(value);
        if (isNaN(date.getTime())) return String(value);
        return date.toLocaleString('ru-RU', {
            day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
        });
    }

    function render(body) {
        body.innerHTML = '';

        if (state.busy) {
            body.appendChild(h('div', {class: 'ap-empty'}, 'Отправляю решение…'));
            return;
        }
        if (!state.items.length) {
            body.appendChild(h('div', {class: 'ap-empty'},
                'Ожидающих подтверждений нет. Когда агент предложит правку, она появится здесь — и применится только после твоего решения.'));
            return;
        }

        state.items.forEach(function (item) {
            var card = h('div', {class: 'ap-item'});
            card.appendChild(h('div', {class: 'ap-title'}, describe(item)));
            // Замена версии должна быть видна: иначе Frontend-овский файл
            // исчезает из очереди и никто об этом не узнаёт.
            if (item.note) {
                card.appendChild(h('div', {class: 'ap-note'}, item.note));
            }

            var meta = [];
            if (item.agent_id) {
                meta.push('автор: ' + item.agent_id);
            }
            if (item.risk_level) {
                if (item.created_at) {
                    meta.push('создан: ' + formatTime(item.created_at));
                }
                meta.push('риск: ' + item.risk_level);
            }
            if (item.patch_id) {
                meta.push('патч: ' + item.patch_id);
            }
            if (item.status) {
                meta.push('статус: ' + item.status);
            }
            if (meta.length) {
                card.appendChild(h('div', {class: 'ap-meta'}, meta.join('  ·  ')));
            }

            var actions = h('div', {class: 'ap-actions'});
            var approve = h('button', {class: 'ap-btn ap-approve'}, 'Применить');
            var reject = h('button', {class: 'ap-btn ap-reject'}, 'Отклонить');
            actions.appendChild(approve);
            actions.appendChild(reject);
            card.appendChild(actions);

            approve.addEventListener('click', function () {
                decide(item, 'approve');
            });
            reject.addEventListener('click', function () {
                decide(item, 'reject');
            });

            body.appendChild(card);
        });
    }

    function decide(item, action) {
        if (state.busy) {
            return;
        }
        state.busy = true;
        refresh();

        fetchJson('/api/developer/approvals/action', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                request_id: item.request_id,
                action: action,
                comments: action === 'approve' ? 'применено из интерфейса' : 'отклонено из интерфейса'
            })
        }).then(function (result) {
            state.busy = false;
            state.status = action === 'approve'
                ? (result.data.success ? 'Правка применена.' : 'Применить не удалось — патч не прошёл проверку.')
                : (result.data.success ? 'Правка отклонена.' : 'Отклонить не удалось.');
            if (action === 'approve' && result.data.success) {
                // Соседняя панель кода обновляется сама: сообщаем ей, что появилась правка.
                document.dispatchEvent(new CustomEvent('aiteam:applied'));
            }
            return refresh();
        }).catch(function (error) {
            state.busy = false;
            state.status = 'Ошибка запроса: ' + error.message;
            refresh();
        });
    }

    function refresh() {
        var body = document.getElementById('approvalsBody');
        var fab = document.getElementById('approvalsFab');
        if (!body) {
            return;
        }
        render(body);

        return fetchJson('/api/developer/approvals').then(function (result) {
            state.items = (result.data && result.data.pending) || [];
            render(body);
            if (state.status) {
                body.appendChild(h('div', {class: 'ap-status'}, state.status));
            }
            if (fab) {
                fab.classList.toggle('has-items', state.items.length > 0);
                fab.textContent = state.items.length
                    ? '✅ Подтверждения: ' + state.items.length
                    : '✅ Подтверждения';
            }
        }).catch(function () {
            state.items = [];
            render(body);
        });
    }

    function build() {
        if (document.getElementById('approvalsFab')) {
            return;
        }
        style();

        var fab = h('button', {id: 'approvalsFab', title: 'Очередь подтверждений'}, '✅ Подтверждения');
        var panel = h('div', {id: 'approvalsPanel'});

        var head = h('div', {class: 'ap-head'});
        head.appendChild(h('div', {class: 'ap-title'}, 'Подтверждения изменений'));
        var close = h('button', {class: 'ap-close', title: 'Закрыть'}, '×');
        head.appendChild(close);
        panel.appendChild(head);

        var body = h('div', {class: 'ap-body', id: 'approvalsBody'});
        panel.appendChild(body);

        document.body.appendChild(fab);
        document.body.appendChild(panel);

        function toggle(open) {
            state.open = open === undefined ? !state.open : open;
            panel.classList.toggle('open', state.open);
            if (state.open && !state.timer) {
                state.timer = setInterval(refresh, REFRESH_MS);
                refresh();
            } else if (!state.open && state.timer) {
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
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', build);
    } else {
        build();
    }
})();
