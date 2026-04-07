/* ═══════════════════════════════════════════════════════════════
   AI Team System — Клиентский JavaScript
   ═══════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    const STORAGE_KEY = "ai-team-tour-completed";
    const LEVEL_KEY = "ai-team-user-level";

    const TOUR_STEPS = [
        {
            title: "👋 Что такое AI Team System?",
            description: "Это команда из 7 AI-агентов, которые работают вместе над твоим проектом. Каждый агент — специалист в своей области: от архитектуры до тестирования.",
            visual: "🤖 × 7",
            hint: "Представь, что у тебя есть целая команда разработчиков, но вместо людей — умные AI-ассистенты."
        },
        {
            title: "👑 TeamLead — главный координатор",
            description: "TeamLead первым получает твою задачу. Он разбирает её на части и распределяет между остальными агентами. Как настоящий руководитель проекта.",
            visual: "👑 → 📋",
            hint: "TeamLead решает кто, что и в каком порядке делает. Без него — хаос."
        },
        {
            title: "⚙️ Разработка — Backend, Frontend, DevOps",
            description: "Три агента работают параллельно: Backend пишет серверную часть, Frontend создаёт интерфейс, DevOps настраивает инфраструктуру (Docker, деплой).",
            visual: "⚙️ 🎨 🚀",
            hint: "Параллельная работа — это как три повара готовят разные блюда одновременно. Быстрее!"
        },
        {
            title: "🧪 Тестирование и документация",
            description: "Tester проверяет код на ошибки, а Documentalist пишет понятную документацию. Так проект будет работать правильно и его поймут другие.",
            visual: "🧪 ✅ 📝",
            hint: "Без тестов код может сломаться. Без документации — никто не поймёт как им пользоваться."
        },
        {
            title: "🎉 Результат — готовый проект!",
            description: "Все агенты завершили работу. Ты получаешь готовый проект с кодом, тестами, документацией и пошаговым уроком в формате Markdown.",
            visual: "🎉 📦 ✨",
            hint: "Каждый урок сохраняется. Ты можешь вернуться к нему в любой момент."
        }
    ];

    let currentStep = 0;
    let sessionId = "";
    let userLevel = "beginner";

    function showScreen(id) {
        document.querySelectorAll(".screen").forEach(function (s) {
            s.classList.remove("active");
        });
        var screen = document.getElementById(id);
        if (screen) screen.classList.add("active");
    }

    function loadHardwareInfo() {
        fetch("/api/hardware")
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var el = document.getElementById("hardware-info");
                if (el && data.profile) {
                    var vram = data.vram_gb || "—";
                    var ram = data.ram_gb || "—";
                    el.textContent = "Профиль: " + data.profile + " | VRAM: " + vram + " ГБ | RAM: " + ram + " ГБ";
                }
            })
            .catch(function () {});
    }

    function startTour() {
        userLevel = "beginner";
        localStorage.setItem(LEVEL_KEY, userLevel);
        currentStep = 0;
        renderStep();
        showScreen("tour-screen");

        fetch("/api/start?user_level=" + userLevel)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                sessionId = data.session_id;
            })
            .catch(function () {});
    }

    function skipTour() {
        userLevel = localStorage.getItem(LEVEL_KEY) || "intermediate";
        fetch("/api/start?user_level=" + userLevel)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                sessionId = data.session_id;
                showScreen("project-screen");
            })
            .catch(function () {
                showScreen("project-screen");
            });
    }

    function renderStep() {
        var step = TOUR_STEPS[currentStep];
        if (!step) return;

        document.getElementById("step-title").textContent = step.title;
        document.getElementById("step-description").textContent = step.description;
        document.getElementById("step-visual").textContent = step.visual;
        document.getElementById("step-hint").textContent = "💡 " + step.hint;
        document.getElementById("step-counter").textContent = "Шаг " + (currentStep + 1) + " из " + TOUR_STEPS.length;

        var pct = ((currentStep + 1) / TOUR_STEPS.length) * 100;
        document.getElementById("progress-fill").style.width = pct + "%";

        document.getElementById("btn-prev").disabled = currentStep === 0;
        document.getElementById("btn-next").textContent = currentStep === TOUR_STEPS.length - 1 ? "🚀 Создать проект" : "Далее →";
    }

    function nextStep() {
        if (currentStep < TOUR_STEPS.length - 1) {
            currentStep++;
            renderStep();
        } else {
            localStorage.setItem(STORAGE_KEY, "true");
            showScreen("project-screen");
        }
    }

    function prevStep() {
        if (currentStep > 0) {
            currentStep--;
            renderStep();
        }
    }

    function submitProject(e) {
        e.preventDefault();
        var name = document.getElementById("project-name").value.trim();
        var desc = document.getElementById("project-desc").value.trim();
        if (!name || !desc) return;

        var resultBox = document.getElementById("project-result");
        resultBox.style.display = "block";
        resultBox.textContent = "⏳ Агенты работают...";

        fetch("/api/agent/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                query: "Создай проект '" + name + "': " + desc,
                agent_role: "teamlead",
                user_level: userLevel,
                session_id: sessionId
            })
        })
        .then(function (r) {
            if (!r.ok) {
                return r.json().then(function (err) { throw new Error(err.detail || r.statusText); });
            }
            return r.json();
        })
        .then(function (data) {
            resultBox.innerHTML = "✅ Проект создан!<br><br>" + data.response.substring(0, 500) + "...";
            showLesson(data.response, name);
        })
        .catch(function (err) {
            resultBox.textContent = "❌ Ошибка: " + err.message;
        });
    }

    function showLesson(content, title) {
        document.getElementById("lesson-content").textContent = "# " + title + "\n\n" + content;
        showScreen("lesson-screen");

        fetch("/api/export", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId, title: title })
        }).catch(function () {});
    }

    function downloadLesson() {
        var content = document.getElementById("lesson-content").textContent;
        var blob = new Blob([content], { type: "text/markdown" });
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url;
        a.download = "lesson.md";
        a.click();
        URL.revokeObjectURL(url);
    }

    function newProject() {
        showScreen("project-screen");
        document.getElementById("project-name").value = "";
        document.getElementById("project-desc").value = "";
        document.getElementById("project-result").style.display = "none";
    }

    document.addEventListener("DOMContentLoaded", function () {
        loadHardwareInfo();

        var savedLevel = localStorage.getItem(LEVEL_KEY);
        if (savedLevel) {
            userLevel = savedLevel;
        }

        document.getElementById("btn-tour").addEventListener("click", startTour);
        document.getElementById("btn-skip").addEventListener("click", skipTour);
        document.getElementById("btn-next").addEventListener("click", nextStep);
        document.getElementById("btn-prev").addEventListener("click", prevStep);
        document.getElementById("project-form").addEventListener("submit", submitProject);
        document.getElementById("btn-download").addEventListener("click", downloadLesson);
        document.getElementById("btn-new-project").addEventListener("click", newProject);
    });
})();
