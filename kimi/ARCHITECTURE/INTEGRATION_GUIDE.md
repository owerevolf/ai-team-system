# INTEGRATION GUIDE
## How to add ProjectManager + Repo Mode to existing AI Team System

---

## STEP 1: Copy New Files

Copy these files to your project:

```
core/project_manager.py          -> your_project/core/project_manager.py
core/repo_explorer.py            -> your_project/core/repo_explorer.py
core/symbol_extractor.py         -> your_project/core/symbol_extractor.py
core/knowledge_base.py           -> your_project/core/knowledge_base.py
core/context_compressor.py       -> your_project/core/context_compressor.py
core/repo_validator.py           -> your_project/core/repo_validator.py
core/skills/PROJECT_MANAGER_SKILL.md -> your_project/core/skills/PROJECT_MANAGER_SKILL.md
prompts/roles/repo_explorer.md   -> your_project/prompts/roles/repo_explorer.md
prompts/roles/repo_explorer_zero.md -> your_project/prompts/roles/repo_explorer_zero.md
prompts/roles/repo_explorer_beginner.md -> your_project/prompts/roles/repo_explorer_beginner.md
web_ui/repo_endpoints.py         -> your_project/web_ui/repo_endpoints.py
```

---

## STEP 2: Modify core/agent_manager.py

Add to imports:
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

Modify run_agent method (around line where full_prompt is built):

BEFORE:
```python
agent_context = {}
if self.context:
    agent_context = self.context.get_context_for_agent(agent_name)
```

AFTER:
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

Modify full_prompt to use combined_context instead of agent_context.

Add after agent execution (where result is returned):
```python
# NEW: Report result to ProjectManager
if self.project_manager and result.get("status") == "success":
    self.project_manager.update(
        agent=agent_name,
        action="agent_completed",
        result=result
    )
```

---

## STEP 3: Modify core/main.py (Orchestrator)

Add to imports:
```python
from .project_manager import ProjectManager
```

Add to __init__:
```python
self.project_manager: Optional[ProjectManager] = None
```

Modify create_project method:

AFTER project folder is created, ADD:
```python
# Initialize ProjectManager
self.project_manager = ProjectManager(self.project_path)
self.agent_manager.set_project_manager(self.project_manager)

# Index initial structure
self.project_manager.index_project()
```

Add new method open_project:
```python
def open_project(self, project_path: str) -> dict:
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

---

## STEP 4: Modify core/project_context.py

Add method:
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

## STEP 5: Modify web_ui/app.py

Add to imports:
```python
from .repo_endpoints import router as repo_router, set_orchestrator
```

After app is created, ADD:
```python
app.include_router(repo_router)
```

In startup event or where orchestrator is created:
```python
set_orchestrator(ai_team_system)
```

---

## STEP 6: Add Repo Explorer to Agent Config

Add to config/agents.yaml:
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

Add to config/agent_models.json:
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

## STEP 7: Test

1. Start your application
2. Open a project:
   ```bash
   curl -X POST http://localhost:8000/api/repo/open \
     -H "Content-Type: application/json" \
     -d '{"path": "/path/to/your/project", "level": "beginner"}'
   ```
3. Check status:
   ```bash
   curl http://localhost:8000/api/repo/status
   ```
4. Explore:
   ```bash
   curl -X POST http://localhost:8000/api/repo/explore \
     -H "Content-Type: application/json" \
     -d '{"question": "What does this project do?", "level": "beginner"}'
   ```

---

## STEP 8: Add Frontend UI (optional)

Add to your web UI:
- Button "Open Existing Project"
- File tree display
- Chat interface for Repo Explorer
- Diff viewer for modifications
- Confirmation dialog for changes

---

## TROUBLESHOOTING

### Import errors
Make sure all new files are in correct locations and __init__.py exists.

### PM not initialized
Check that set_project_manager() is called before running agents.

### Context too large
Reduce max_tokens in PM.query() calls. Default 8000, try 4000.

### Indexing slow
Large projects may take time. Add progress indicator in UI.

### Memory issues
PM stores file contents. For very large projects, implement lazy loading.

---

## NEXT STEPS

1. Implement GitHub clone functionality
2. Add WebSocket for real-time updates
3. Implement actual modification workflow
4. Add visual diff viewer
5. Add test runner integration
6. Add rollback UI
