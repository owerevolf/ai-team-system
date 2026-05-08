"""
CoderChat Agent — диалоговый агент для написания кода.

Как Claude Code:
- Полноценный диалог с пользователем
- Читает и пишет файлы проекта
- Показывает структуру проекта
- Объясняет решения
- Показывает diff изменений
"""

import os
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


@dataclass
class FileAction:
    """Действие с файлом"""
    action: str  # create, edit, delete, read
    path: str
    content: str = ""
    description: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ChatMessage:
    """Сообщение в чате"""
    role: str  # user, assistant, system
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    file_actions: List[FileAction] = field(default_factory=list)


@dataclass
class ProjectContext:
    """Контекст проекта для агента"""
    project_path: str
    project_name: str
    file_tree: List[str] = field(default_factory=list)
    recent_files: List[str] = field(default_factory=list)
    tech_stack: List[str] = field(default_factory=list)


class FileTools:
    """Инструменты для работы с файлами проекта"""
    
    def __init__(self, project_path: str, allowed_extensions: List[str] = None):
        self.project_path = Path(project_path)
        self.allowed_extensions = allowed_extensions or [
            '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss',
            '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.env',
            '.md', '.txt', '.sh', '.bash', '.sql', '.graphql',
            '.vue', '.svelte', '.astro', '.php', '.rb', '.go', '.rs',
            '.java', '.kt', '.swift', '.c', '.cpp', '.h',
            '.dockerfile', '.gitignore', '.dockerignore', 'Makefile',
        ]
        self._actions_log: List[FileAction] = []
    
    def is_allowed(self, path: str) -> bool:
        """Проверка разрешённого расширения"""
        p = Path(path)
        if p.suffix.lower() in self.allowed_extensions:
            return True
        if p.name in self.allowed_extensions:
            return True
        return False
    
    def get_file_tree(self, max_depth: int = 3, exclude_dirs: List[str] = None) -> List[str]:
        """Получить дерево файлов проекта"""
        exclude = set(exclude_dirs or [
            '__pycache__', 'node_modules', '.git', '.venv', 'venv',
            '.idea', '.vscode', 'dist', 'build', '.next', '.nuxt',
            'coverage', '.pytest_cache', '.mypy_cache', '.tox',
        ])
        tree = []
        
        def _walk(path: Path, prefix: str = "", depth: int = 0):
            if depth >= max_depth:
                return
            try:
                entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name))
                for entry in entries:
                    if entry.name in exclude:
                        continue
                    if entry.name.startswith('.') and entry.name not in ['.env', '.gitignore', '.dockerignore']:
                        continue
                    rel_path = str(entry.relative_to(self.project_path))
                    if entry.is_dir():
                        tree.append(f"{prefix}📁 {entry.name}/")
                        _walk(entry, prefix + "  ", depth + 1)
                    else:
                        size = entry.stat().st_size
                        size_str = f"{size}B" if size < 1024 else f"{size//1024}KB"
                        tree.append(f"{prefix}📄 {entry.name} ({size_str})")
            except PermissionError:
                pass
        
        _walk(self.project_path)
        return tree
    
    def read_file(self, path: str) -> Optional[str]:
        """Прочитать файл"""
        full_path = self.project_path / path
        if not full_path.exists():
            return None
        if not self.is_allowed(path):
            logger.warning(f"Attempted to read disallowed file: {path}")
            return None
        try:
            content = full_path.read_text(encoding='utf-8')
            self._actions_log.append(FileAction(action="read", path=path))
            return content
        except Exception as e:
            logger.error(f"Failed to read {path}: {e}")
            return None
    
    def write_file(self, path: str, content: str, create_dirs: bool = True) -> Tuple[bool, str]:
        """Создать или перезаписать файл"""
        if not self.is_allowed(path):
            return False, f"File type not allowed: {path}"
        
        full_path = self.project_path / path
        
        # Safety check: don't write outside project
        try:
            full_path.relative_to(self.project_path.resolve())
        except ValueError:
            return False, "Path traversal detected"
        
        exists = full_path.exists()
        old_content = full_path.read_text(encoding='utf-8') if exists else ""
        
        try:
            if create_dirs:
                full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding='utf-8')
            
            action = "edit" if exists else "create"
            self._actions_log.append(FileAction(
                action=action, path=path, content=content,
                description=f"{'Modified' if exists else 'Created'} {path}"
            ))
            
            # Generate diff for edits
            if exists:
                diff = self._generate_diff(old_content, content, path)
                return True, diff
            return True, f"📄 Created: {path}"
        except Exception as e:
            logger.error(f"Failed to write {path}: {e}")
            return False, str(e)
    
    def delete_file(self, path: str) -> Tuple[bool, str]:
        """Удалить файл"""
        full_path = self.project_path / path
        if not full_path.exists():
            return False, f"File not found: {path}"
        
        try:
            full_path.unlink()
            self._actions_log.append(FileAction(
                action="delete", path=path, description=f"Deleted {path}"
            ))
            return True, f"🗑 Deleted: {path}"
        except Exception as e:
            return False, str(e)
    
    def list_directory(self, path: str = ".") -> List[str]:
        """Список файлов в директории"""
        full_path = self.project_path / path
        if not full_path.is_dir():
            return []
        try:
            return sorted([str(p.relative_to(self.project_path)) for p in full_path.iterdir()])
        except Exception:
            return []
    
    def _generate_diff(self, old: str, new: str, path: str) -> str:
        """Простой diff для отображения"""
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        
        diff_lines = []
        max_lines = min(len(old_lines), len(new_lines))
        
        changes = 0
        for i in range(max_lines):
            if old_lines[i] != new_lines[i]:
                changes += 1
        
        if len(new_lines) > len(old_lines):
            changes += len(new_lines) - len(old_lines)
        
        if changes == 0:
            return f"📝 No changes in {path}"
        
        # Show first few changed lines
        for i in range(min(10, max_lines)):
            if old_lines[i] != new_lines[i]:
                diff_lines.append(f"  - {old_lines[i].rstrip()[:80]}")
                diff_lines.append(f"  + {new_lines[i].rstrip()[:80]}")
        
        summary = f"📝 Modified {path} ({changes} line{'s' if changes > 1 else ''} changed)"
        if diff_lines:
            summary += "\n" + "\n".join(diff_lines[:6])
            if changes > 3:
                summary += f"\n  ... and {changes - 3} more changes"
        
        return summary
    
    def get_actions_log(self) -> List[FileAction]:
        """Получить лог действий с файлами"""
        return self._actions_log.copy()
    
    def clear_actions_log(self):
        """Очистить лог действий"""
        self._actions_log.clear()


class CoderChatAgent:
    """
    Диалоговый агент для написания кода.
    
    Возможности:
    - Полноценный диалог с контекстом
    - Чтение/запись файлов
    - Показ структуры проекта
    - Diff изменений
    - Объяснение решений
    """
    
    AGENT_NAME = "coderchat"
    
    def __init__(self, model_router=None, profile: str = "medium"):
        self.model_router = model_router
        self.profile = profile
        self.messages: List[ChatMessage] = []
        self.file_tools: Optional[FileTools] = None
        self.project: Optional[ProjectContext] = None
        self._conversation_id = f"chat_{int(time.time())}"
    
    def init_project(self, project_path: str, project_name: str = None):
        """Инициализировать проект"""
        path = Path(project_path)
        path.mkdir(parents=True, exist_ok=True)
        
        self.file_tools = FileTools(str(path))
        self.project = ProjectContext(
            project_path=str(path),
            project_name=project_name or path.name,
            file_tree=self.file_tools.get_file_tree(),
        )
        
        # Detect tech stack
        self._detect_tech_stack()
        
        logger.info(f"CoderChat initialized: {self.project.project_name} ({path})")
    
    def _detect_tech_stack(self):
        """Автоопределение стека технологий"""
        if not self.file_tools:
            return
        
        stack = []
        tree = self.project.file_tree
        
        tech_indicators = {
            'pyproject.toml': 'Python (Poetry)',
            'requirements.txt': 'Python (pip)',
            'setup.py': 'Python (setuptools)',
            'Pipfile': 'Python (Pipenv)',
            'package.json': 'Node.js',
            'tsconfig.json': 'TypeScript',
            'Cargo.toml': 'Rust',
            'go.mod': 'Go',
            'pom.xml': 'Java (Maven)',
            'build.gradle': 'Java (Gradle)',
            'Gemfile': 'Ruby',
            'composer.json': 'PHP',
            'Dockerfile': 'Docker',
            'docker-compose.yml': 'Docker Compose',
            '.eslintrc': 'ESLint',
            'vite.config.js': 'Vite',
            'vite.config.ts': 'Vite',
            'next.config.js': 'Next.js',
            'nuxt.config.js': 'Nuxt',
            'tailwind.config.js': 'Tailwind CSS',
            'webpack.config.js': 'Webpack',
        }
        
        for file_pattern, tech in tech_indicators.items():
            for entry in tree:
                if file_pattern in entry.lower():
                    stack.append(tech)
                    break
        
        # Check for frameworks
        if any('react' in e.lower() for e in tree):
            stack.append('React')
        if any('vue' in e.lower() for e in tree):
            stack.append('Vue')
        if any('angular' in e.lower() for e in tree):
            stack.append('Angular')
        if any('fastapi' in e.lower() or 'flask' in e.lower() for e in tree):
            stack.append('Python Web')
        if any('django' in e.lower() for e in tree):
            stack.append('Django')
        
        self.project.tech_stack = list(set(stack))
    
    def get_system_prompt(self) -> str:
        """Получить system prompt для агента"""
        project_info = ""
        if self.project:
            tech = ', '.join(self.project.tech_stack) if self.project.tech_stack else 'Unknown'
            project_info = f"""
## Project Context
- Name: {self.project.project_name}
- Path: {self.project.project_path}
- Tech Stack: {tech}
"""
            if self.project.file_tree:
                tree_preview = '\n'.join(self.project.file_tree[:30])
                tree_note = f"\n(... and {len(self.project.file_tree) - 30} more files)" if len(self.project.file_tree) > 30 else ""
                project_info += f"""
## File Structure (first 30 entries)
```
{tree_preview}{tree_note}
```
"""
        
        return f"""You are CoderChat — an AI code assistant integrated into AI Team System.

## Who You Are
- Expert software developer with deep knowledge of all programming languages
- You help users build software through conversation
- You write REAL, WORKING code — not pseudocode or examples
- You explain your decisions and show what you changed

## Your Capabilities
- **Write files**: Create new files or modify existing ones
- **Read files**: Examine project structure and existing code
- **Edit code**: Make targeted changes with clear diffs
- **Run commands**: Execute terminal commands (with user permission)
- **Search**: Find patterns across the codebase
- **Explain**: Describe how code works and why you made changes

## How You Write Code
1. Always write COMPLETE, WORKING code
2. Include all necessary imports
3. Follow the project's existing conventions and style
4. Add comments for complex logic
5. Handle errors and edge cases
6. Use the project's tech stack and libraries

## File Operations Format
When you need to create or modify files, use this format:

```file
path/to/file.py
file content here...
```

Or for editing specific parts:

```file
path/to/file.py
<<< SEARCH
old code to replace
=== 
new replacement code
>>> REPLACE
```

## Response Format
- Start with a brief explanation of what you're doing
- Show code in proper markdown blocks
- Use ```file blocks for files you create/modify
- End with a summary of changes made
- Ask if the user wants you to do anything else

## Communication Style
- Be concise but thorough
- Explain WHY, not just WHAT
- Show diffs when modifying files
- Proactively suggest improvements
- Ask clarifying questions when requirements are unclear
- Use Russian if user writes in Russian, otherwise English

## Safety
- NEVER delete files without asking
- NEVER modify .env or secrets files
- ALWAYS confirm before running destructive commands
- Show what you're about to change before doing it

## Context
{project_info}

Ready to help! 🚀"""
    
    def add_message(self, role: str, content: str, file_actions: List[FileAction] = None):
        """Добавить сообщение в историю"""
        msg = ChatMessage(role=role, content=content, file_actions=file_actions or [])
        self.messages.append(msg)
        return msg
    
    def get_conversation_history(self, max_messages: int = 20) -> List[Dict]:
        """Получить историю для отправки в LLM"""
        recent = self.messages[-max_messages:]
        result = []
        for msg in recent:
            result.append({
                "role": msg.role,
                "content": msg.content,
            })
        return result
    
    def extract_file_actions(self, text: str) -> List[Tuple[str, str]]:
        """Извлечь file actions из ответа агента"""
        actions = []
        
        # Pattern: ```file\npath\ncontent```
        pattern = r'```file\n([^\n]+)\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for path, content in matches:
            path = path.strip()
            content = content.strip()
            if path and content:
                actions.append((path, content))
        
        return actions
    
    def format_diff_message(self, actions_results: List[Tuple[str, bool, str]]) -> str:
        """Форматировать сообщение с diff"""
        lines = []
        for path, success, detail in actions_results:
            icon = "✅" if success else "❌"
            lines.append(f"{icon} {detail}")
        return "\n".join(lines)
    
    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Обработать сообщение пользователя.
        
        Returns:
            Dict с полями: response, file_actions, success
        """
        if not self.model_router:
            return {"error": "Model router not configured", "response": "⚠️ Model router not initialized"}
        
        # Add user message
        self.add_message("user", user_message)
        
        # Build prompt
        system_prompt = self.get_system_prompt()
        history = self.get_conversation_history()
        
        # Construct full prompt
        prompt = f"{system_prompt}\n\n"
        for msg in history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            prompt += f"{role_label}: {msg['content']}\n\n"
        prompt += "Assistant: "
        
        try:
            # Generate response
            start_time = time.time()
            response = await asyncio.to_thread(
                lambda: self.model_router.generate(prompt=prompt, agent=self.AGENT_NAME)
            )
            duration = time.time() - start_time
            
            # Extract and execute file actions
            file_actions = self.extract_file_actions(response)
            action_results = []
            executed_actions = []
            
            if file_actions and self.file_tools:
                for path, content in file_actions:
                    success, detail = self.file_tools.write_file(path, content)
                    action_results.append((path, success, detail))
                    executed_actions.append(FileAction(
                        action="create" if "Created" in detail else "edit",
                        path=path, content=content, description=detail
                    ))
            
            # Add assistant message
            self.add_message("assistant", response, executed_actions)
            
            # Build response with diff
            result = {
                "response": response,
                "file_actions": [a.__dict__ for a in executed_actions],
                "file_results": action_results,
                "success": True,
                "duration": duration,
                "conversation_id": self._conversation_id,
            }
            
            if action_results:
                result["diff_message"] = self.format_diff_message(action_results)
            
            return result
            
        except Exception as e:
            logger.error(f"CoderChat error: {e}")
            return {
                "response": f"⚠️ Error: {str(e)}",
                "success": False,
                "error": str(e),
            }
    
    def get_file_tree_display(self) -> str:
        """Получить дерево файлов для отображения"""
        if not self.file_tools:
            return "No project initialized"
        return '\n'.join(self.file_tools.get_file_tree())
    
    def read_project_file(self, path: str) -> Optional[str]:
        """Прочитать файл проекта"""
        if not self.file_tools:
            return None
        return self.file_tools.read_file(path)
    
    def get_stats(self) -> Dict:
        """Статистика сессии"""
        return {
            "conversation_id": self._conversation_id,
            "message_count": len(self.messages),
            "user_messages": sum(1 for m in self.messages if m.role == "user"),
            "assistant_messages": sum(1 for m in self.messages if m.role == "assistant"),
            "file_actions": len(self.file_tools._actions_log) if self.file_tools else 0,
            "project": self.project.project_name if self.project else None,
        }


import asyncio
