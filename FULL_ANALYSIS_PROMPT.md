# 🔬 ПОЛНЫЙ ПРОМПТ ДЛЯ АНАЛИЗА — СКОПИРУЙ И ВСТАВЬ В ЛЮБУЮ МОДЕЛЬ

---

## PROJECT CONTEXT

Репозиторий: https://github.com/owerevolf/ai-team-system

Это мультиагентная система разработки ПО на Python. Система использует AI агентов (TeamLead, Architect, Backend, Frontend, DevOps, Tester, Documentalist) для автоматической генерации кода проектов.

### Current Stack
- Python 3.10+
- Flask (Web UI)
- SQLite (Database)
- Ollama (Local LLMs)
- Optional: OpenAI/Anthropic API

### Project Structure
```
ai-team-system/
├── core/
│   ├── main.py          # Orchestrator
│   ├── agent_manager.py # Agent management
│   ├── model_router.py  # LLM routing
│   ├── database.py      # SQLite
│   └── system_scanner.py
├── prompts/roles/       # Agent prompts
├── web_ui/              # Flask app
└── config/              # YAML profiles
```

---

## YOUR TASK

Проанализируй этот код как Senior Software Architect.

### ANALYZE

1. **Architecture** (30%)
   - Multi-agent system design
   - Orchestration flow
   - Error handling
   - Scalability

2. **Code Quality** (30%)
   - Python best practices
   - Type hints, docstrings
   - Security
   - Testing

3. **AI/ML Aspects** (25%)
   - Prompt engineering quality
   - Agent autonomy level
   - Tool use / function calling
   - Output parsing

4. **Production Readiness** (15%)
   - Deployment
   - Monitoring
   - Cost efficiency

---

## RESPONSE FORMAT

### Overall: X/10

### Critical Issues (blocking bugs)
```
1. ...
2. ...
```

### Major Improvements (high priority)
```
1. [File] - What to change
   Before: ...
   After: ...
2. ...
```

### Minor Improvements (nice to have)
```
1. ...
```

### New Features (suggested)
```
Priority 1:
- Feature name - description

Priority 2:
- ...
```

### Code Examples

Provide concrete code snippets for major improvements.

---

## RULES

1. Be honest - don't praise without reason
2. Be specific - reference exact files/lines
3. Be practical - focus on changes that matter
4. Consider local deployment (Ollama) as priority

---

## CONTEXT FOR YOUR ANALYSIS

Think about:
- Can this actually work in production?
- What's missing for autonomous code generation?
- How would you improve the agent prompts?
- What would break at scale?

End with: "Most important next step:" - one concrete action.

---

**END OF PROMPT**
