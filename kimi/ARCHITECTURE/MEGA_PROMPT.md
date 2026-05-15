# MEGA PROMPT: ProjectManager + Repo Mode Implementation
## For Local AI (Qwen 2.5 Coder 7B, 30K context)

---

## YOUR TASK

Implement ProjectManager and Repo Mode for the existing AI Team System project.

The project is at: https://github.com/owerevolf/ai-team-system

You have already been given 13 files. Your job is to:
1. Understand the existing codebase
2. Integrate the new files
3. Make minimal, safe changes to existing code
4. Ensure everything works together

---

## EXISTING PROJECT STRUCTURE (what you must NOT break)

```
ai-team-system/
├── core/                          # CORE MODULE
│   ├── __init__.py
│   ├── main.py                    # Orchestrator (4 phases)
│   ├── model_router.py            # Multi-provider routing
│   ├── agent_manager.py           # 7 agents + tool calling
│   ├── agent_skills.py            # Skill mapping
│   ├── model_registry.py          # Free model parsing
│   ├── project_context.py         # Shared context
│   ├── coder_chat.py              # Dialog agent
│   ├── prompt_architect.py        # Prompt teacher
│   ├── memory.py                  # Agent memory
│   ├── database.py                # SQLite
│   ├── code_validator.py          # Code validation
│   ├── system_scanner.py          # Hardware scan
│   ├── hardware_detector.py       # GPU/RAM detect
│   ├── analytics.py               # Usage metrics
│   ├── i18n.py                    # Translations
│   ├── webhooks.py                # GitHub/GitLab webhooks
│   ├── mcp_server.py              # MCP servers
│   ├── export_lesson.py           # Lesson export
│   ├── learning_mode.py           # Learning mode
│   └── skills/                    # LVL99 skill prompts
│       ├── TEAMLEAD_SKILL.md
│       ├── ARCHITECT_SKILL.md
│       ├── BACKEND_SKILL.md
│       ├── FRONTEND_SKILL.md
│       ├── DEVOPS_SKILL.md
│       ├── TESTER_SKILL.md
│       ├── DOCUMENTALIST_SKILL.md
│       └── PROMPT_ARCHITECT_SKILL.md
├── prompts/                       # AGENT PROMPTS
│   └── roles/
│       ├── teamlead.md
│       ├── teamlead_zero.md
│       ├── teamlead_beginner.md
│       ├── architect.md
│       ├── backend.md
│       ├── frontend.md
│       ├── devops.md
│       ├── tester.md
│       └── documentalist.md
├── config/                        # CONFIGURATION
│   ├── agents.yaml
│   ├── agent_models.json
│   └── mcp_servers.json
├── web_ui/                        # WEB UI (FastAPI)
│   ├── app.py                     # All API endpoints
│   ├── static/
│   └── templates/
├── docs/                          # DOCUMENTATION
├── scripts/                       # Setup scripts
└── templates/                     # Project templates
```

---

## WHAT ALREADY EXISTS (do not recreate)

### Orchestrator (core/main.py)
- 4 phases: planning -> architecture -> development -> documentation
- create_project() method
- SSE streaming to frontend
- Project path management

### Agent Manager (core/agent_manager.py)
- run_agent() method
- Tool calling: create_file, read_file, list_directory, run_command
- Skill loading from .md files
- Context building for agents
- Safety: whitelist commands, path traversal protection

### Model Router (core/model_router.py)
- Multi-provider: Ollama -> OpenRouter -> OmniRoute -> Google -> Anthropic -> OpenAI
- Dynamic provider selection per agent
- Free model filtering
- Quality/speed/availability testing at startup

### Web UI (web_ui/app.py)
- FastAPI with SSE streaming
- Endpoints: create_project, agent_query, coderchat, promptarchitect
- Tour/lesson system
- Kanban board
- Hardware profiles

---

## WHAT YOU MUST CREATE (new files)

### Core Module (core/)
1. **project_manager.py** — Single source of truth
   - FileIndex: all files with metadata
   - SymbolIndex: classes, functions, variables
   - DependencyGraph: who imports whom
   - DecisionLog: why things were decided
   - ErrorLog: what broke and how fixed
   - query(agent, question, max_tokens) -> relevant context
   - update(agent, action, result) -> update indexes
   - validate(agent, proposal) -> (is_valid, reason)
   - index_project() -> full scan
   - reindex_file(path) -> update single file
   - create_snapshot() / rollback()

2. **repo_explorer.py** — File discovery
   - discover_files() -> list of relevant files
   - get_tree_display() -> visual tree
   - get_directory_stats() -> file counts
   - find_files_by_pattern() -> search
   - get_largest_files() -> biggest files
   - SKIP_DIRS: __pycache__, node_modules, .git, etc.
   - CODE_EXTENSIONS: .py, .js, .ts, etc.

3. **symbol_extractor.py** — Code analysis
   - extract(content, language) -> list of symbols
   - Support: Python, JS, TS, Go, Rust, Java, PHP
   - Patterns: class, function, method, variable, interface, struct
   - Extract docstrings/comments
   - No AST parser — regex only (faster, no dependencies)

4. **knowledge_base.py** — Persistent storage
   - save_index() -> JSON file in .agents/pm/
   - load_index() -> restore from JSON
   - append_decision() -> JSONL log
   - load_decisions() -> recent decisions
   - append_error() -> JSONL log
   - load_errors() -> recent errors
   - save_snapshot() / load_snapshot()
   - clear_all() -> wipe everything

5. **context_compressor.py** — Token economy
   - compress(text, max_chars) -> compressed text
   - Strategies: remove whitespace, truncate lines, remove comments, progressive truncation
   - Keep: headers, structure, first/last N lines
   - Remove: middle sections with "... (N lines omitted) ..."
   - estimate_tokens(text) -> approximate count

6. **repo_validator.py** — Safety checks
   - validate(proposal, files, dependencies) -> (bool, str)
   - Checks: file existence, duplicate symbols, import integrity, breaking changes, syntax
   - _is_external_import() -> skip stdlib packages
   - No code execution — static analysis only

### Skill Prompt (core/skills/)
7. **PROJECT_MANAGER_SKILL.md** — LVL99 prompt
   - Role definition
   - Core rules (5 rules)
   - Query response format
   - Validation checklist
   - Error handling
   - Self-improvement protocol
   - Tech stack detection rules
   - Context priority order
   - Example interactions

### Agent Prompts (prompts/roles/)
8. **repo_explorer.md** — Main explorer prompt
   - Role: friendly guide
   - Capabilities: overview, architecture, code reading, tech stack
   - How to work with PM
   - Response format
   - Level-specific instructions
   - Example responses
   - Rules (6 rules)

9. **repo_explorer_zero.md** — Absolute beginner
   - Simple words, emojis, analogies
   - Project = House, Code = Recipe, Database = Filing Cabinet
   - Encouragement phrases
   - ELI5 mode
   - Technical terms with explanations
   - Never modify code

10. **repo_explorer_beginner.md** — Beginner level
    - Correct terms with first-use explanations
    - Show code snippets with comments
    - Explain WHY, not just WHAT
    - Trade-offs and alternatives
    - Connect to documentation
    - Explanation depth levels (1-4)

### Web UI (web_ui/)
11. **repo_endpoints.py** — API endpoints
    - POST /api/repo/open -> open project
    - GET /api/repo/status -> indexing status
    - POST /api/repo/explore -> answer questions
    - POST /api/repo/modify -> plan modifications
    - POST /api/repo/modify/confirm -> execute plan
    - POST /api/repo/rollback -> rollback changes
    - GET /api/repo/tree -> file tree
    - GET /api/repo/file/{path} -> file content
    - GET /api/repo/search -> symbol search
    - WebSocket /api/repo/ws -> real-time updates

---

## WHAT YOU MUST MODIFY (existing files)

### 1. core/agent_manager.py

Add import:
```python
from typing import Optional
from .project_manager import ProjectManager
```

Add to __init__:
```python
self.project_manager: Optional[ProjectManager] = None
```

Add method:
```python
def set_project_manager(self, pm: ProjectManager):
    self.project_manager = pm
```

Modify run_agent():

Find this section (around line where agent_context is built):
```python
agent_context = {}
if self.context:
    agent_context = self.context.get_context_for_agent(agent_name)
```

Replace with:
```python
agent_context = {}
if self.context:
    agent_context = self.context.get_context_for_agent(agent_name)

# NEW: Query ProjectManager for relevant context
pm_context = ""
if self.project_manager:
    pm_context = self.project_manager.query(
        agent=agent_name,
        question=task,
        max_tokens=8000
    )

# Combine contexts
combined_context = {
    "pm_knowledge": pm_context,
    "project_context": agent_context
}
```

Then replace usage of agent_context with combined_context in full_prompt.

Add after result is returned:
```python
# NEW: Report result to ProjectManager
if self.project_manager and result.get("status") == "success":
    self.project_manager.update(
        agent=agent_name,
        action="agent_completed",
        result=result
    )
```

### 2. core/main.py (Orchestrator)

Add import:
```python
from .project_manager import ProjectManager
```

Add to __init__:
```python
self.project_manager: Optional[ProjectManager] = None
```

Modify create_project():

After project folder is created and agent_manager is set up, ADD:
```python
# Initialize ProjectManager for new project
self.project_manager = ProjectManager(self.project_path)
self.agent_manager.set_project_manager(self.project_manager)

# Index initial structure
self.project_manager.index_project()
```

Add new method open_project():
```python
def open_project(self, project_path: str) -> dict:
    """Open existing project for exploration or modification."""
    path = Path(project_path)
    if not path.exists():
        raise ValueError(f"Project not found: {project_path}")

    self.project_path = path
    self.agent_manager.set_project_path(path)

    # Initialize ProjectManager
    self.project_manager = ProjectManager(path)
    self.agent_manager.set_project_manager(self.project_manager)

    # Full indexing
    self.console.print("[bold cyan]Indexing project...[/bold cyan]")
    stats = self.project_manager.index_project()

    self.console.print("[green]Indexed:[/green]")
    self.console.print(f"  Files: {stats['total_files']}")
    self.console.print(f"  Symbols: {stats['total_symbols']}")
    self.console.print(f"  Dependencies: {stats['total_dependencies']}")

    return {
        "project_path": str(path),
        "stats": stats,
        "status": "opened"
    }
```

### 3. core/project_context.py

Add method:
```python
def get_pm_context(self) -> Dict:
    """Get context for ProjectManager."""
    return {
        "project_name": self.project_name,
        "phase": self.phase,
        "agents_completed": list(self.agent_results.keys()),
        "files_created": self.get_all_files(),
        "architecture": self.architecture
    }
```

### 4. web_ui/app.py

Add import:
```python
from .repo_endpoints import router as repo_router, set_orchestrator
```

After app = FastAPI(...), ADD:
```python
app.include_router(repo_router)
```

Where orchestrator is initialized (in startup event or main), ADD:
```python
set_orchestrator(ai_team_system)
```

### 5. config/agents.yaml

Add entry:
```yaml
repo_explorer:
  name: "Repo Explorer"
  role: "Explains existing projects to users"
  icon: "🔍"
  color: "#9C27B0"
  model_requirements:
    context: 32000
    temperature: 0.7
    skills: ["exploration", "teaching", "architecture"]
```

### 6. config/agent_models.json

Add entry:
```json
{
  "repo_explorer": {
    "provider": "auto",
    "model": "auto",
    "context": 32000,
    "temperature": 0.7
  }
}
```

---

## INTEGRATION RULES (CRITICAL)

1. **NEVER break existing functionality**
   - All changes are ADDITIVE
   - Existing endpoints must work exactly as before
   - Existing agent flow must not change

2. **PM is OPTIONAL**
   - If PM is not initialized, system works as before
   - Check `if self.project_manager:` before using
   - No hard dependencies on PM

3. **Lazy initialization**
   - PM is created only when needed (open_project or create_project)
   - No overhead if user never uses repo mode

4. **Error handling**
   - If PM fails, log error and continue without PM
   - Agents should still work with standard context
   - Never crash the whole system because of PM

5. **Performance**
   - Indexing happens once per project
   - Query cache (5 min TTL) prevents re-processing
   - Context compression keeps token usage low
   - Reindex only changed files, not entire project

---

## TESTING CHECKLIST

After implementation, verify:

- [ ] Existing create_project flow works unchanged
- [ ] New open_project endpoint works
- [ ] Project indexing completes without errors
- [ ] PM query returns relevant context
- [ ] PM update indexes new files
- [ ] PM validate catches unsafe changes
- [ ] Agent manager uses PM context when available
- [ ] Repo Explorer agent responds correctly
- [ ] Web UI endpoints return proper JSON
- [ ] File tree endpoint works
- [ ] Rollback restores previous state
- [ ] No import errors on startup
- [ ] Free model filtering still works
- [ ] Hardware profiles still work

---

## COMMON MISTAKES TO AVOID

1. **Don't import heavy libraries**
   - No AST parser (ast module is OK, but tree-sitter is not)
   - No vector DB (use simple JSON files)
   - No external dependencies beyond existing ones

2. **Don't change agent prompts**
   - Existing agent prompts (teamlead.md, etc.) stay as-is
   - Only add new repo_explorer prompts

3. **Don't modify tool calling**
   - create_file, read_file, etc. stay as-is
   - PM uses them, doesn't replace them

4. **Don't break SSE streaming**
   - Frontend expects specific event format
   - Keep existing streaming logic

5. **Don't forget error handling**
   - Every PM method should handle exceptions
   - Log errors, don't crash

---

## EXAMPLE WORKFLOW

### User opens existing project:

```
User: "Open /home/user/my-flask-app"

System:
1. Orchestrator.open_project("/home/user/my-flask-app")
2. PM = ProjectManager(path)
3. PM.index_project()
   - Scans all files
   - Extracts symbols
   - Builds dependency graph
   - Detects tech stack: ["Python", "Flask", "SQLAlchemy"]
   - Finds entry points: ["app.py"]
4. Returns stats: {files: 47, symbols: 156, dependencies: 89}

User: "What does this project do?"

System:
1. Repo Explorer agent asks PM: "Give me project overview"
2. PM.query(agent="repo_explorer", question="overview")
3. PM returns compressed context:
   - Project: my-flask-app
   - Tech: Python, Flask, SQLAlchemy
   - Entry: app.py
   - Key files: models/, routes/, templates/
4. Repo Explorer formats response for user level
5. Returns: "This is a blog application built with Flask..."

User: "Add Stripe payments"

System:
1. TeamLead asks PM: "What is the architecture?"
2. PM returns: entry points, models, routes
3. TeamLead creates plan
4. PM.validate(plan) -> checks for conflicts
5. If valid: Backend modifies code, Frontend updates templates
6. PM.update() reindexes changed files
7. Tester runs tests
8. PM creates snapshot
9. Git commit
```

---

## FILES SUMMARY

You should create/modify these files:

NEW FILES (11):
- core/project_manager.py
- core/repo_explorer.py
- core/symbol_extractor.py
- core/knowledge_base.py
- core/context_compressor.py
- core/repo_validator.py
- core/skills/PROJECT_MANAGER_SKILL.md
- prompts/roles/repo_explorer.md
- prompts/roles/repo_explorer_zero.md
- prompts/roles/repo_explorer_beginner.md
- web_ui/repo_endpoints.py

MODIFIED FILES (6):
- core/agent_manager.py
- core/main.py
- core/project_context.py
- web_ui/app.py
- config/agents.yaml
- config/agent_models.json

TOTAL: 17 files

---

## FINAL CHECK

Before saying "done":
1. All new files created with correct content
2. All existing files modified safely
3. No syntax errors
4. Imports resolve correctly
5. No circular dependencies
6. Tests pass (manual check)
7. Documentation updated

Start implementing now. Work file by file. Test after each modification.
