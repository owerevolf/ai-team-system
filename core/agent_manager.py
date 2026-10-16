"""
Agent Manager - Управление AI агентами с Tool Calling
"""

import os
import json
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass, field

from .model_router import ModelRouter
from .database import Database
from .memory import AgentMemory, MemoryEntry
from .logger import setup_logger


ALLOWED_COMMANDS = {
    "python", "python3", "pip", "pip3", "pip install",
    "node", "npm", "npx",
    "git", "git add", "git commit", "git status", "git clone", "git pull", "git push",
    "pytest", "pytest tests/", "python -m pytest",
    "mkdir", "ls", "ls -la", "pwd", "cd",
    "uvicorn", "flask", "fastapi",
    "docker", "docker-compose",
    "curl", "wget",
    "cat", "head", "tail", "grep",
    "chmod", "chown",
    "echo"
}

ALLOWED_PATTERNS = [
    r"^python.*",
    r"^pip install.*",
    r"^git .*",
    r"^pytest.*",
    r"^mkdir.*",
    r"^ls.*",
    r"^cd .* && .*",
]


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable = None


@dataclass
class AgentTask:
    id: str
    agent: str
    task: str
    context: Dict = field(default_factory=dict)
    result: Any = None
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)


class AgentManager:
    def __init__(self, model_router: ModelRouter):
        self.model_router = model_router
        self.db = Database()
        self.logger = setup_logger("agent_manager")
        self.prompts_dir = Path(__file__).parent.parent / "prompts" / "roles"
        self.tools = self._register_tools()
        self.project_path: Optional[Path] = None
        self.context = None
        self.event_callback: Optional[Callable] = None
        self.memory = AgentMemory()
        self._self_improvement_enabled = True
        # ProjectManager integration (optional, passive)
        self.project_manager = None
    
    def set_self_improvement(self, enabled: bool):
        """Включить/выключить self-improvement агентов"""
        self._self_improvement_enabled = enabled

    def set_project_path(self, path) -> None:
        """
        Задаёт папку проекта, в которой агенты создают файлы.

        Метод вызывался из web_ui/app.py и core/main.py, но не был определён:
        кнопка «Создать проект» падала с AttributeError сразу после старта.
        Путь сразу разрешается — дальше все записи проверяются на выход за него.
        """
        self.project_path = Path(path).resolve()
    
    def set_context(self, context):
        self.context = context
    
    def set_event_callback(self, callback: Callable):
        self.event_callback = callback

    def set_project_manager(self, pm) -> None:
        """Set ProjectManager instance (optional, passive observer)."""
        self.project_manager = pm

    def emit_event(self, event_type: str, data: Dict[str, Any]):
        if self.event_callback:
            self.event_callback(event_type, data)
        self.logger.info(f"Event: {event_type} - {data.get('agent', 'system')}")
    
    def _is_command_allowed(self, command: str) -> bool:
        """Проверка команды по whitelist"""
        command_lower = command.lower().strip()
        
        if command_lower in ALLOWED_COMMANDS:
            return True
        
        for pattern in ALLOWED_PATTERNS:
            if re.match(pattern, command_lower):
                return True
        
        first_word = command_lower.split()[0] if command_lower.split() else ""
        if first_word in ALLOWED_COMMANDS:
            return True
        
        return False
    
    def _register_tools(self) -> Dict[str, Tool]:
        return {
            "create_file": Tool(
                name="create_file",
                description="Создать файл. Безопасная операция.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "description": {"type": "string"},
                        "overwrite": {
                            "type": "boolean",
                            "description": "Перезаписать существующий файл. Старая версия уйдёт в .ai-team/backups."
                        }
                    },
                    "required": ["path", "content"]
                },
                handler=self._create_file
            ),
            "read_file": Tool(
                name="read_file", 
                description="Прочитать файл.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                },
                handler=self._read_file
            ),
            "list_directory": Tool(
                name="list_directory",
                description="Показать файлы в директории.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    }
                },
                handler=self._list_directory
            ),
            "run_command": Tool(
                name="run_command",
                description="Выполнить безопасную команду. Разрешены только: python, pip, git, pytest, npm, mkdir, ls",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "cwd": {"type": "string"}
                    },
                    "required": ["command"]
                },
                handler=self._run_command
            ),
            "create_directory": Tool(
                name="create_directory",
                description="Создать директорию.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                },
                handler=self._create_directory
            ),
            "write_to_file": Tool(
                name="write_to_file",
                description="Добавить в конец файла.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["path", "content"]
                },
                handler=self._append_to_file
            )
        }
    
    def get_tools_for_prompt(self) -> str:
        tools_desc = []
        for name, tool in self.tools.items():
            params = json.dumps(tool.parameters, indent=2)
            tools_desc.append(f"## {tool.name}\n{tool.description}\nParameters: {params}")
        return "\n\n".join(tools_desc)
    
    # Порядок уровней: от максимального объяснения к минимальному
    LEVEL_ORDER = ("zero", "beginner", "standard", "advanced")

    def get_agent_prompt(self, agent_name: str, level: str = "advanced", lang: Optional[str] = None) -> str:
        """
        Загружает промпт агента с учётом уровня пользователя.

        Компетенция роли и стиль объяснения разделены:
        * компетенция — `prompts/roles/<роль>_<уровень>.md`, иначе `core/skills/<РОЛЬ>_SKILL.md`,
          иначе `prompts/roles/<роль>.md`;
        * стиль — надстройка `prompts/levels/<уровень>.md`, добавляемая к компетенции.

        Так четыре уровня дают четыре разных промпта. Раньше `standard` совпадал с `advanced`,
        а файлы `<роль>_advanced.md` не загружались вообще.
        level: zero | beginner | standard | advanced
        """
        level = str(level or "advanced").strip().lower()
        if level not in self.LEVEL_ORDER:
            level = "advanced"

        base = self._load_role_prompt(agent_name, level)
        overlay = self._load_level_overlay(level, lang)
        if overlay:
            return f"{base}\n\n---\n\n{overlay}"
        return base

    def _load_role_prompt(self, agent_name: str, level: str) -> str:
        """Компетенция роли: уровень-специфичный файл → скилл роли → базовый промпт."""
        if level in ("zero", "beginner"):
            level_file = self.prompts_dir / f"{agent_name}_{level}.md"
            if level_file.exists():
                return level_file.read_text(encoding='utf-8')

        # Для standard/advanced используем LVL99 skill-промпты из core/skills/
        skills_dir = Path(__file__).parent / "skills"
        skill_file = skills_dir / f"{agent_name.upper()}_SKILL.md"
        if skill_file.exists():
            return skill_file.read_text(encoding='utf-8')

        # Fallback на обычный промпт из prompts/roles/
        prompt_file = self.prompts_dir / f"{agent_name}.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding='utf-8')

        self.logger.warning(f"Промпт для {agent_name} не найден")
        return self._get_default_prompt(agent_name)

    def _load_level_overlay(self, level: str, lang: Optional[str] = None) -> str:
        """
        Стиль объяснения уровня: prompts/levels[/<язык>]/<уровень>.md.

        Сначала ищется файл языка (`prompts/levels/en/zero.md`), потом общий
        (`prompts/levels/zero.md`). Так добавляется новый язык: папка + файлы,
        без правок кода.
        """
        levels_dir = self.prompts_dir.parent / "levels"
        candidates = []
        if lang:
            candidates.append(levels_dir / str(lang).strip().lower() / f"{level}.md")
        candidates.append(levels_dir / f"{level}.md")

        for overlay_file in candidates:
            if overlay_file.exists():
                return overlay_file.read_text(encoding='utf-8')
        return ""
    def _get_default_prompt(self, agent_name: str) -> str:
        return f"""Ты - {agent_name} agent в AI Team System.
Создавай РЕАЛЬНЫЙ рабочий код.
Используй инструменты для создания файлов."""
    
    def run_agent(self, agent_name: str, task: str, context: Dict = None, level: str = "advanced") -> Dict[str, Any]:
        self.logger.info(f"Запуск агента: {agent_name} (level={level})")
        self.emit_event("agent_start", {"agent": agent_name})

        prompt_template = self.get_agent_prompt(agent_name, level)
        tools_description = self.get_tools_for_prompt()
        
        # MCP tools description
        mcp_tools_description = ""
        try:
            from .mcp_server import mcp_manager
            mcp_tools_description = mcp_manager.get_tools_description()
        except Exception as e:
            self.logger.debug(f"MCP tools not available: {e}")

        # Добавляем скиллы из agent_skills
        try:
            from .agent_skills import get_agent_skill_addon, get_agent_config
            skill_addon = get_agent_skill_addon(agent_name)
            agent_cfg = get_agent_config(agent_name)
            agent_cfg.get("temperature", 0.7)
        except Exception as e:
            self.logger.warning(f"Не удалось загрузить скиллы для {agent_name}: {e}")
            skill_addon = ""
        
        # Self-improvement: загружаем уроки из памяти
        lessons_from_memory = ""
        if self._self_improvement_enabled:
            try:
                lessons = self.memory.get_lessons_for_agent(agent_name, limit=3)
                if lessons:
                    lessons_from_memory = "\n".join([f"- {lesson}" for lesson in lessons])
                else:
                    lessons_from_memory = "Нет прошлых уроков. Ты первый раз выполняешь эту задачу."
            except Exception as e:
                self.logger.debug(f"Memory lessons load failed: {e}")
                lessons_from_memory = ""

        agent_context = {}
        if self.context:
            agent_context = self.context.get_context_for_agent(agent_name)

        # PM context (passive observer, optional)
        pm_context = ""
        if self.project_manager and self.project_manager.is_indexed:
            try:
                pm_context = self.project_manager.query(
                    agent=agent_name,
                    question=task,
                    max_tokens=2000,
                )
            except Exception as e:
                self.logger.debug(f"PM query failed: {e}")
                pm_context = ""

        # TeamLead - координатор, НЕ получает инструкции создавать файлы
        is_coordinator = (agent_name == 'teamlead')

        if is_coordinator:
            full_prompt = f"""{prompt_template}

{skill_addon}

## ЗАДАНИЕ
{task}

## CONTEXT
{json.dumps(context or agent_context, indent=2, ensure_ascii=False) if (context or agent_context) else 'Нет контекста'}

## PROJECT STATE (from ProjectManager)
{pm_context if pm_context else 'ProjectManager не инициализирован'}

## ИНСТРУКЦИИ
1. Реагируй КОНКРЕТНО на то что написал пользователь в ЗАДАНИИ выше
2. НЕ задавай вопросов если пользователь уже дал конкретику
3. Составляй план
4. ОТВЕЧАЙ ТЕКСТОМ - НЕ создавай файлы и НЕ используй инструменты

Начни работу!
"""
            created_files = []
        else:
            # Для остальных агентов тоже добавляем скиллы
            full_prompt = f"""{prompt_template}

{skill_addon}

## PROJECT PATH: {self.project_path or 'Не указан'}

## AVAILABLE TOOLS
{tools_description}
{mcp_tools_description}

## ALLOWED COMMANDS (whitelist)
python, pip, git, pytest, npm, mkdir, ls, docker, docker-compose

## ЗАДАНИЕ
{task}

## LESSONS FROM PAST PROJECTS (Self-Improvement)
{lessons_from_memory}

## CONTEXT (от других агентов)
{json.dumps(context or agent_context, indent=2, ensure_ascii=False) if (context or agent_context) else 'Нет контекста'}

## PROJECT STATE (from ProjectManager)
{pm_context if pm_context else 'ProjectManager не инициализирован'}

## ИНСТРУКЦИИ
1. Проанализируй задачу
2. Используй create_file для создания кода
3. Создавай РЕАЛЬНЫЙ рабочий код
4. После завершения верни JSON:
{{"status": "success", "files_created": ["file1.py"], "summary": "что сделано"}}

## TOOL CALL FORMAT

Правило размера: один файл — не больше 60 строк. Если код больше, раздели его на
несколько файлов и вызывай инструмент отдельно для каждого. Длинный ответ обрывается
на лимите длины у модели — и тогда не создаётся вообще ничего.
<tool_call>
{{"tool": "create_file", "path": "file.py", "content": "# код"}}
</tool_call>

Начни работу!
"""

        created_files = []
        try:
            response = self.model_router.generate(
                prompt=full_prompt,
                agent=agent_name
            )

            if not is_coordinator:
                created_files = self._extract_and_create_files(response)

                # Агент, который только рассказал, но не вызвал инструмент, — самая
                # частая потеря: снаружи работа выглядит сделанной, а файлов нет.
                # Даём ровно одну попытку с прямым требованием формата.
                if not created_files:
                    retry_prompt = (
                        full_prompt
                        + "\n\nВАЖНО: в прошлый раз ты описал работу словами, но не вызвал инструмент. "
                        "Сейчас верни ТОЛЬКО вызов в формате ＜tool_call＞…＜/tool_call＞, "
                        "без рассуждений и пояснений. Если файлы действительно не нужны — напиши об этом одной строкой."
                    )
                    retry_response = self.model_router.generate(
                        prompt=retry_prompt,
                        agent=agent_name,
                    )
                    retry_files = self._extract_and_create_files(retry_response)
                    if retry_files:
                        created_files = retry_files
                        response = retry_response
                    else:
                        self.logger.warning(
                            f"{agent_name}: после повторной попытки вызов инструмента так и не пришёл"
                        )
            
            result = {
            "agent": agent_name,
            "status": "success",
            "response": response,  # полный ответ — не обрезаем
            "files_created": created_files,
            "summary": f"Создано файлов: {len(created_files)}. " + (", ".join(created_files) if created_files else "Нет файлов."),
            "timestamp": datetime.now().isoformat()
            }
            
            self.emit_event("agent_complete", {"agent": agent_name, "files": created_files})
            self.logger.info(f"Агент {agent_name} завершил. Файлов: {len(created_files)}")

            # Report to ProjectManager (passive observer)
            if self.project_manager:
                try:
                    self.project_manager.update(
                        agent=agent_name,
                        action="task_completed",
                        result={
                            "status": "success",
                            "files": created_files,
                            "summary": result.get("summary", ""),
                        }
                    )
                except Exception as e:
                    self.logger.debug(f"PM update failed: {e}")

            # Self-improvement: сохраняем результат в память
            if self._self_improvement_enabled:
                try:
                    self.memory.add(MemoryEntry(
                        project_name=self.context.project_name if self.context else "unknown",
                        agent=agent_name,
                        action="build",
                        result=response[:500],
                        files_created=created_files,
                        errors=[]
                    ))
                except Exception as e:
                    self.logger.debug(f"Memory save failed: {e}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка {agent_name}: {e}")
            self.emit_event("agent_error", {"agent": agent_name, "error": str(e)})
            
            # Self-improvement: сохраняем ошибку в память
            if self._self_improvement_enabled:
                try:
                    self.memory.add(MemoryEntry(
                        project_name=self.context.project_name if self.context else "unknown",
                        agent=agent_name,
                        action="build",
                        result="",
                        files_created=[],
                        errors=[str(e)]
                    ))
                except Exception:
                    pass
            
            return {
                "agent": agent_name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    @staticmethod
    @staticmethod
    def _json_candidates(text: str) -> List[str]:
        """Куски текста, похожие на JSON-объекты: скобки считаются с учётом строк и экранирования."""
        candidates: List[str] = []
        start = depth = 0
        in_string = escaped = False

        for index, char in enumerate(text or ""):
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                if depth == 0:
                    start = index
                depth += 1
            elif char == "}" and depth:
                depth -= 1
                if depth == 0:
                    candidates.append(text[start : index + 1])

        return candidates

    @staticmethod
    def _parse_tool_call(raw: str):
        """Разбирает вызов инструмента из ответа модели.

        Сначала честный JSON. Если модель не заэкранировала кавычки внутри кода —
        частая беда локальных моделей — поля достраиваются по известной схеме,
        чтобы правка не терялась молча. Содержимое всё равно проверяют движок
        патчей и человек в панели «Подтверждения».
        """
        try:
            return json.loads(raw, strict=False)
        except json.JSONDecodeError:
            pass

        found = {}
        for key in ("tool", "path"):
            item = re.search(rf'"{key}"\s*:\s*"([^"]*)"', raw)
            if item:
                found[key] = item.group(1)

        content = re.search(r'"content"\s*:\s*"(.*)"', raw, re.S)
        if not content or not found.get("path"):
            return None

        text = content.group(1)
        for escaped, plain in (('\\"', '"'), ("\\n", "\n"), ("\\t", "\t"), ("\\\\", "\\")):
            text = text.replace(escaped, plain)
        found["content"] = text
        found.setdefault("tool", "create_file")
        return found

    @staticmethod
    def _reply_language_rule() -> str:
        """Строка про язык ответа: русский по умолчанию, английский — если так выбрал человек.

        Роли агентов написаны по-английски, и без этой строки модель уходила
        в английский посреди русского диалога.
        """
        try:
            settings = Path(__file__).resolve().parent.parent / ".cache" / "ui_settings.json"
            language = str(json.loads(settings.read_text(encoding="utf-8")).get("language", "ru"))
        except Exception:  # noqa: BLE001 — нет файла или испорчен: считаем русский
            language = "ru"

        if language.lower().startswith("en"):
            return "ANSWER LANGUAGE: answer in English. Code and identifiers stay as code.\n\n"
        return (
            "ЯЗЫК ОТВЕТА: отвечай по-русски. "
            "Код, имена файлов и команд остаются как есть.\n\n"
        )

    def _extract_and_create_files(self, response: str) -> List[str]:
        created = []
        tool_pattern = r'<tool_call>\s*(.*?)\s*</tool_call>'
        # Одни модели отдают вызов в широких скобках (U+FF1C/U+FF1E), другие — в обычных:
        # раньше распознавалась только широкая форма, и готовые вызовы молча пропадали.
        open_mark = "[" + "\uff1c" + "<]"
        close_mark = "[" + "\uff1e" + ">]"
        tool_pattern = (
            open_mark + r"\s*tool_call\s*" + close_mark + r"\s*(.*?)\s*"
            + open_mark + r"\s*/\s*tool_call\s*" + close_mark
        )
        matches = re.findall(tool_pattern, response, re.DOTALL)

        if not matches:
            # Модель часто отдаёт вызов вообще без обёртки — просто JSON-объект.
            # Раньше такой ответ пропадал целиком, хотя правка в нём была готова.
            matches = [
                candidate
                for candidate in self._json_candidates(response)
                if '"content"' in candidate and ('"path"' in candidate or '"file"' in candidate)
            ]
        
        for match in matches:
            if not match.rstrip().endswith("}"):
                # Самая частая причина потери правки: модель упёрлась в лимит длины ответа.
                self.logger.warning(
                    f"Вызов обрезан лимитом модели ({len(match)} симв.) — правку не применить, "
                    f"нужен файл короче"
                )
            try:
                # strict=False: модели пишут код с настоящими переносами строк внутри JSON-строк,
                # и строгий разбор на них падает — вызов инструмента молча терялся.
                # Разбор вызова: сначала честный JSON, потом терпимый — см. _parse_tool_call.
                tool_data = self._parse_tool_call(match)
                if tool_data is None:
                    raise json.JSONDecodeError("вызов инструмента не разобран", match, 0)
                tool_name = tool_data.get("tool", "create_file")
                
                if tool_name in self.tools and self.tools[tool_name].handler:
                    result = self.tools[tool_name].handler(tool_data)
                    if result.get("success"):
                        created.append(result.get("path", "unknown"))
                        
            except json.JSONDecodeError as exc:
                # В журнал — причина и хвост: без них непонятно, обрезан ответ или испорчен разбор.
                self.logger.warning(
                    f"Bad tool_call ({exc}, {len(match)} симв., начало {match[:90]!r}, хвост …{match[-70:]!r})"
                )
        
        if not created and self.project_path:
            code_blocks = re.findall(r'```(?:\w+)?\s*(.*?)```', response, re.DOTALL)
            for i, code in enumerate(code_blocks):
                path = f"code/generated_{len(created)}_{i}.py"
                success = self._create_file({"path": path, "content": code.strip()})
                if success.get("success"):
                    created.append(path)
        
        return created
    
    def _create_file(self, params: Dict) -> Dict[str, Any]:
        """
        Создаёт файл внутри папки проекта.

        Две защиты, которых не было раньше:
        * путь не может выйти за пределы project_path (`..`, абсолютный путь, симлинк);
        * существующий файл не затирается молча: без флага `overwrite` запись
          отклоняется, а при `overwrite=true` старая версия уходит в бэкап.
        """
        try:
            if not self.project_path:
                return {"success": False, "error": "project_path not set"}

            raw_path = str(params.get("path") or "").strip()
            if not raw_path:
                return {"success": False, "error": "path is empty"}

            project_root = Path(self.project_path).resolve()
            candidate = Path(raw_path.replace("\\", "/"))

            if candidate.is_absolute() or ".." in candidate.parts:
                self.logger.warning(f"Отклонён путь вне проекта: {raw_path}")
                return {"success": False, "error": f"path escapes project root: {raw_path}"}

            file_path = (project_root / candidate).resolve()
            if file_path != project_root and project_root not in file_path.parents:
                self.logger.warning(f"Отклонён путь вне проекта: {raw_path}")
                return {"success": False, "error": f"path escapes project root: {raw_path}"}

            if file_path.is_dir():
                return {"success": False, "error": f"path is a directory: {raw_path}"}

            backup = None
            if file_path.exists():
                if not params.get("overwrite"):
                    self.logger.info(f"Файл уже существует, запись отклонена: {file_path}")
                    return {
                        "success": False,
                        "error": "file exists; pass overwrite=true to replace it (старая версия сохранится в .ai-team/backups)",
                        "path": str(file_path.relative_to(project_root)),
                    }
                backup = self._backup_file(file_path, project_root)

            # Если подключён движок патчей — правка идёт через него и ждёт подтверждения
            sink = getattr(self, "_patch_sink", None)
            if sink is not None:
                try:
                    routed = sink(file_path, params["content"])
                except Exception as exc:  # noqa: BLE001 — сломанный сток не должен ломать запись
                    self.logger.warning(
                        f"Очередь подтверждений не приняла правку, сохраняю напрямую: {exc}"
                    )
                    routed = False
                if routed:
                    return {
                        "success": False,
                        "pending": True,
                        "error": "изменение отправлено на подтверждение",
                        "path": str(file_path.relative_to(project_root)),
                    }

            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(params["content"], encoding='utf-8')
            self._journal_write(project_root, file_path, backup)

            self.logger.info(f"Создан: {file_path}" + (f" (бэкап: {backup})" if backup else ""))
            result: Dict[str, Any] = {"success": True, "path": str(file_path.relative_to(project_root))}
            if backup:
                result["backup"] = backup
            return result
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            return {"success": False, "error": str(e)}

    def _backup_file(self, file_path: Path, project_root: Path) -> str:
        """Сохраняет текущую версию файла в .ai-team/backups/<дата>/ внутри проекта."""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        relative = file_path.relative_to(project_root)
        backup_path = project_root / ".ai-team" / "backups" / stamp / relative
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_bytes(file_path.read_bytes())
        return str(backup_path.relative_to(project_root))

    def _journal_write(self, project_root: Path, file_path: Path, backup: Optional[str]) -> None:
        """Ведёт журнал записей, чтобы действия агентов были проверяемы."""
        try:
            log_dir = project_root / ".ai-team"
            log_dir.mkdir(parents=True, exist_ok=True)
            entry = {
                "at": datetime.now().isoformat(timespec="seconds"),
                "path": str(file_path.relative_to(project_root)),
                "bytes": file_path.stat().st_size,
                "backup": backup,
            }
            with (log_dir / "writes.log").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.warning(f"Журнал записей недоступен: {e}")
    
    def _read_file(self, params: Dict) -> Dict[str, Any]:
        try:
            if not self.project_path:
                return {"success": False, "error": "project_path not set"}
            
            file_path = self.project_path / params["path"]
            if not file_path.exists():
                return {"success": False, "error": "File not found"}
            
            content = file_path.read_text(encoding='utf-8')
            return {"success": True, "content": content[:5000]}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _list_directory(self, params: Dict) -> Dict[str, Any]:
        try:
            if not self.project_path:
                return {"success": False, "error": "project_path not set"}
            
            dir_path = self.project_path / params.get("path", ".")
            if not dir_path.exists():
                return {"success": False, "error": "Directory not found"}
            
            files = [str(p.relative_to(self.project_path)) for p in dir_path.rglob("*") if p.is_file()]
            return {"success": True, "files": files}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _run_command(self, params: Dict) -> Dict[str, Any]:
        command = params.get("command", "")
        
        if not self._is_command_allowed(command):
            self.logger.warning(f"Blocked command: {command}")
            return {
                "success": False,
                "error": f"Command not allowed: {command[:50]}",
                "blocked": True
            }
        
        try:
            cwd = params.get("cwd", str(self.project_path) if self.project_path else None)
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:1000],
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timeout (120s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_directory(self, params: Dict) -> Dict[str, Any]:
        try:
            if not self.project_path:
                return {"success": False, "error": "project_path not set"}
            
            dir_path = self.project_path / params["path"]
            dir_path.mkdir(parents=True, exist_ok=True)
            
            return {"success": True, "path": str(dir_path.relative_to(self.project_path))}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _append_to_file(self, params: Dict) -> Dict[str, Any]:
        try:
            if not self.project_path:
                return {"success": False, "error": "project_path not set"}
            
            file_path = self.project_path / params["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "a", encoding='utf-8') as f:
                f.write(params["content"])
            
            return {"success": True, "path": str(file_path.relative_to(self.project_path))}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_parallel(self, tasks: Dict[str, str], callback: Callable = None) -> Dict[str, Any]:
        """Параллельный запуск агентов"""
        import concurrent.futures
        
        results = {}
        
        def run_with_callback(agent, task):
            result = self.run_agent(agent, task)
            if callback:
                callback(agent, result)
            return agent, result
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(run_with_callback, agent, task): agent 
                for agent, task in tasks.items()
            }
            
            for future in concurrent.futures.as_completed(futures):
                agent = futures[future]
                try:
                    _, result = future.result()
                    results[agent] = result
                except Exception as e:
                    results[agent] = {"agent": agent, "status": "error", "error": str(e)}
        
        return results
