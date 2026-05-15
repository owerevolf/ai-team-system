# ARCHITECTURE: ProjectManager + Repo Mode Integration
## Version: 1.0 | For local AI (30K context)

---

## GOAL

Implement **ProjectManager (PM)** — single source of truth for the entire project.
PM stores ALL context, agents query it for clarifications.
This solves:
- Agent hallucinations
- Infinite loops
- Context loss in 30K
- Ability to open existing projects (Repo Mode)

---

## NEW ARCHITECTURE

```
+-------------------------------------------------------------+
|                      USER                                   |
|  [Tour] [Prompt Architect] [Create Project] [Open Project]  |
+-------------------------------------------------------------+
                              |
+-------------------------------------------------------------+
|                 PROJECT MANAGER (CORE)                      |
|  +-------------+  +-------------+  +---------------------+  |
|  | File Index  |  | Symbol Map  |  | Decision Log        |  |
|  | (all files) |  | (classes,   |  | (why decided so)    |  |
|  |             |  |  functions) |  |                     |  |
|  +-------------+  +-------------+  +---------------------+  |
|  +-------------+  +-------------+  +---------------------+  |
|  | Dependency  |  | API Contract|  | Error Log           |  |
|  | Graph       |  | (endpoints) |  | (what broke)        |  |
|  +-------------+  +-------------+  +---------------------+  |
+-------------------------------------------------------------+
          |           |           |           |
    +---------+ +---------+ +---------+ +---------+
    |TeamLead | |Architect| | Backend | | Frontend| ...
    +---------+ +---------+ +---------+ +---------+
         ^           ^           ^           ^
    [Query PM for context, do not remember themselves]
```

---

## NEW FILES (create)

### Core (core/)
1. core/project_manager.py — Main PM class
2. core/repo_explorer.py — Repository scanning and indexing
3. core/symbol_extractor.py — Symbol extraction (classes, functions)
4. core/knowledge_base.py — Structured memory
5. core/context_compressor.py — Context compression for agents
6. core/repo_validator.py — Change validation
7. core/skills/PROJECT_MANAGER_SKILL.md — LVL99 prompt for PM

### Web UI (web_ui/)
8. Add endpoints to web_ui/app.py:
   - POST /api/repo/open — Open project
   - GET /api/repo/explore — Explore structure
   - POST /api/repo/modify — Modify project
   - GET /api/repo/status — Indexing status

### Prompts (prompts/roles/)
9. prompts/roles/repo_explorer.md — Explorer agent prompt
10. prompts/roles/repo_explorer_zero.md — For beginners
11. prompts/roles/repo_explorer_beginner.md

---

## CHANGES TO EXISTING FILES

### 1. core/agent_manager.py

ADD:
```python
from .project_manager import ProjectManager

class AgentManager:
    def __init__(self, model_router: ModelRouter):
        # ... existing code ...
        self.project_manager: Optional[ProjectManager] = None

    def set_project_manager(self, pm: ProjectManager):
        self.project_manager = pm

    def run_agent(self, agent_name: str, task: str, context: Dict = None, level: str = "advanced") -> Dict:
        # ... existing code before full_prompt formation ...

        # NEW: Query PM for context
        pm_context = ""
        if self.project_manager:
            pm_context = self.project_manager.query(
                agent=agent_name,
                question=task,
                max_tokens=8000  # limit for economy
            )

        # Replace static context with dynamic from PM
        agent_context = {}
        if self.context:
            agent_context = self.context.get_context_for_agent(agent_name)

        # Combine: PM context + standard context
        combined_context = {
            "pm_knowledge": pm_context,
            "project_context": agent_context
        }

        # ... rest of code ...

        # NEW: After execution — report result to PM
        result = {...}  # existing result

        if self.project_manager and result.get("status") == "success":
            self.project_manager.update(
                agent=agent_name,
                action="agent_completed",
                result=result
            )

        return result
```

### 2. core/main.py (Orchestrator)

ADD to AITeamSystem.__init__:
```python
from .project_manager import ProjectManager

def __init__(self, profile: str = "medium"):
    # ... existing code ...
    self.project_manager: Optional[ProjectManager] = None

def create_project(self, project_name: str, requirements_path: str) -> dict:
    # ... existing code ...

    # NEW: Initialize PM for new project
    self.project_manager = ProjectManager(self.project_path)
    self.agent_manager.set_project_manager(self.project_manager)

    # Index initial structure
    self.project_manager.index_project()

    return result

# NEW METHOD: Open existing project
def open_project(self, project_path: str) -> dict:
    path = Path(project_path)
    if not path.exists():
        raise ValueError(f"Project not found: {project_path}")

    self.project_path = path
    self.agent_manager.set_project_path(path)

    # Initialize PM
    self.project_manager = ProjectManager(path)
    self.agent_manager.set_project_manager(self.project_manager)

    # Full indexing of existing project
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

ADD method:
```python
def get_pm_context(self) -> Dict:
    return {
        "project_name": self.project_name,
        "phase": self.phase,
        "agents_completed": list(self.agent_results.keys()),
        "files_created": self.get_all_files(),
        "architecture": self.architecture
    }
```

---

## HOW PM WORKS (step by step)

### Scenario 1: Creating project from scratch

1. User: "Create REST API on Flask"
2. Orchestrator.create_project() -> creates folder
3. PM.index_project() -> indexes empty structure
4. TeamLead queries PM: "What exists?"
   PM: "Empty project. Requirements: REST API Flask"
5. TeamLead creates plan
6. PM.update() -> remembers plan
7. Architect queries: "What is the plan?"
   PM: "[plan from memory]"
8. Architect creates architecture
9. PM.update() -> remembers architecture + files
10. Backend queries: "What endpoints are needed?"
    PM: "[endpoints from architecture]"
11. Backend writes code
12. PM.update() -> indexes new files
13. Tester queries: "What needs testing?"
    PM: "[list of endpoints and functions]"

### Scenario 2: Open existing project (Repo Mode)

1. User: "Open ~/my-old-project"
2. Orchestrator.open_project() -> indexes ENTIRE project
3. PM.index_project():
   - Scans all files
   - Extracts symbols (classes, functions)
   - Builds dependency graph
   - Determines tech stack
   - Creates summaries for each file
4. User: "What is this project?"
5. Repo Explorer agent queries PM:
   "Describe project for a beginner"
6. PM gives structured answer:
   "This is a Flask app. Has auth, API, DB.
    Main file: app.py. Models: models.py..."
7. User: "Add Stripe subscription system"
8. PM checks: "Already has payment system?"
   No -> can add
9. TeamLead queries: "What is the architecture?"
   PM: "[architecture from index]"
10. TeamLead creates modification plan
11. PM.validate() -> "Plan does not break existing code"
12. Backend/Frontend modify
13. PM.update() -> indexes changes
14. PM makes git commit

---

## PM RULES (do not break)

1. PM is the single source of truth. Agents do not "remember" — they "ask".
2. PM does not generate code. Only stores, indexes, validates.
3. PM saves tokens. Gives agents only relevant context.
4. PM versions. Every change — log entry.
5. PM protects architecture. Prevents agents from breaking existing code.

---

## DEPLOYMENT ORDER

### Step 1: Create files (this package)
- core/project_manager.py
- core/repo_explorer.py
- core/symbol_extractor.py
- core/knowledge_base.py
- core/context_compressor.py
- core/repo_validator.py
- core/skills/PROJECT_MANAGER_SKILL.md

### Step 2: Modify existing
- core/agent_manager.py — add PM calls
- core/main.py — add open_project()
- core/project_context.py — add get_pm_context()

### Step 3: Web UI endpoints
- Add to web_ui/app.py

### Step 4: Testing
- Open existing project
- Check indexing
- Check agent queries to PM

---

## IMPORTANT

- Do not break existing code. All changes are additive.
- PM is optional. If PM not initialized — system works as before.
- 30K context. PM compresses context before sending to agents.
- Local AI. All files written without complex dependencies (no vector DB).
