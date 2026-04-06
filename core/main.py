"""
AI Team System - Main Orchestrator v2
"""

import os
import sys
import json
import argparse
import concurrent.futures
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Dict, Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table

from .agent_manager import AgentManager
from .model_router import ModelRouter
from .database import Database
from .logger import setup_logger
from .system_scanner import SystemScanner
from .project_context import ProjectContext, AgentResult


console = Console()


class AITeamSystem:
    def __init__(self, profile: str = "medium"):
        self.profile = profile
        self.project_path: Optional[Path] = None
        self.console = console
        self.project_id: Optional[int] = None
        self.context: Optional[ProjectContext] = None
        
        self.console.print(Panel.fit(
            "[bold cyan]AI Team System v2[/bold cyan]\n"
            "Мультиагентная система разработки ПО",
            border_style="cyan"
        ))
        
        self.logger = setup_logger("ai_team_system")
        self.db = Database()
        self.scanner = SystemScanner()
        self.model_router = ModelRouter(profile)
        self.agent_manager = AgentManager(self.model_router)
        self.events: list = []
    
    def on_event(self, event_type: str, data: Dict[str, Any]):
        """Callback для событий агентов"""
        self.events.append({"type": event_type, "data": data, "time": datetime.now().isoformat()})
        self.console.print(f"[dim]{event_type}:[/dim] {data.get('agent', 'system')}")
    
    def scan_hardware(self) -> dict:
        info = self.scanner.get_info()
        
        table = Table(title="Информация о системе")
        table.add_column("Параметр", style="cyan")
        table.add_column("Значение", style="green")
        
        table.add_row("CPU", f"{info['cpu']['cores']} ядер")
        table.add_row("RAM", f"{info['ram']['total_gb']} GB")
        table.add_row("GPU", info['gpu']['name'] or "Нет")
        table.add_row("VRAM", f"{info['gpu']['vram_gb']} GB" if info['gpu']['vram_gb'] else "N/A")
        table.add_row("Ollama", "✓ Доступна" if info['ollama']['available'] else "✗ Недоступна")
        
        self.console.print(table)
        return info
    
    def create_project(self, project_name: str, requirements_path: str) -> dict:
        self.console.print(f"\n[bold yellow]Создание проекта:[/bold yellow] {project_name}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = Path.home() / "projects" / f"{project_name}_{timestamp}"
        
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "code" / "backend").mkdir(parents=True, exist_ok=True)
        (project_dir / "code" / "frontend").mkdir(parents=True, exist_ok=True)
        (project_dir / "code" / "shared").mkdir(parents=True, exist_ok=True)
        (project_dir / "tests").mkdir(parents=True, exist_ok=True)
        (project_dir / "docs").mkdir(parents=True, exist_ok=True)
        (project_dir / ".agents").mkdir(parents=True, exist_ok=True)
        (project_dir / ".logs").mkdir(parents=True, exist_ok=True)
        
        requirements = requirements_path
        if Path(requirements_path).exists():
            requirements = Path(requirements_path).read_text()
        
        (project_dir / "requirements.md").write_text(requirements)
        
        self.project_path = project_dir
        self.agent_manager.set_project_path(project_dir)
        self.agent_manager.set_event_callback(self.on_event)
        
        project_id = self.db.create_project(
            name=project_name,
            path=str(project_dir),
            profile=self.profile,
            requirements=requirements
        )
        self.project_id = project_id
        
        self.context = ProjectContext(
            project_id=project_id,
            project_name=project_name,
            project_path=project_dir,
            requirements=requirements
        )
        self.agent_manager.set_context(self.context)
        
        self.logger.info(f"Проект создан: {project_dir}")
        
        return {
            "project_id": project_id,
            "project_name": project_name,
            "path": str(project_dir),
            "created_at": datetime.now().isoformat()
        }
    
    def run_planning_phase(self) -> dict:
        self.console.print("\n[bold cyan]═══ ФАЗА 1: ПЛАНИРОВАНИЕ ═══[/bold cyan]")
        
        requirements = (self.project_path / "requirements.md").read_text()
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
            task = progress.add_task("TeamLead работает...", total=None)
            result = self.agent_manager.run_agent("teamlead", f"Проанализируй требования и создай план:\n{requirements}")
            progress.update(task, completed=True)
        
        if result.get("status") == "success":
            self.context.add_result(AgentResult(
                agent="teamlead",
                status="success",
                files_created=result.get("files_created", [])
            ))
            self.db.update_task_status(self.project_id, "completed", json.dumps(result))
        
        return result
    
    def run_architecture_phase(self) -> dict:
        self.console.print("\n[bold cyan]═══ ФАЗА 2: АРХИТЕКТУРА ═══[/bold cyan]")
        
        requirements = (self.project_path / "requirements.md").read_text()
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
            task = progress.add_task("Architect работает...", total=None)
            result = self.agent_manager.run_agent("architect", f"Спроектируй архитектуру:\n{requirements}")
            progress.update(task, completed=True)
        
        if result.get("status") == "success":
            self.context.architecture = {"files": result.get("files_created", [])}
            self.context.add_result(AgentResult(
                agent="architect",
                status="success",
                files_created=result.get("files_created", [])
            ))
        
        return result
    
    def run_development_phase(self) -> dict:
        self.console.print("\n[bold cyan]═══ ФАЗА 3: РАЗРАБОТКА ═══[/bold cyan]")
        
        requirements = (self.project_path / "requirements.md").read_text()
        
        tasks = {
            "backend": f"Создай backend код:\n{requirements}",
            "frontend": f"Создай frontend код:\n{requirements}",
            "devops": f"Создай Docker и CI/CD:\n{requirements}"
        }
        
        results = {}
        
        def agent_callback(agent: str, result: dict):
            self.context.add_result(AgentResult(
                agent=agent,
                status=result.get("status", "unknown"),
                files_created=result.get("files_created", []),
                error=result.get("error")
            ))
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
            progress.add_task("[yellow]Параллельная работа агентов...[/yellow]", total=None)
            results = self.agent_manager.run_parallel(tasks, callback=agent_callback)
        
        self.console.print(f"[green]✓ Агенты завершили работу[/green]")
        
        tester_task = {
            "tester": f"Напиши тесты для созданного кода. Все созданные файлы: {self.context.get_all_files()}"
        }
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
            task = progress.add_task("Tester работает...", total=None)
            tester_result = self.agent_manager.run_agent("tester", tester_task["tester"])
            progress.update(task, completed=True)
            results["tester"] = tester_result
        
        if tester_result.get("status") == "success":
            self.context.add_result(AgentResult(
                agent="tester",
                status="success",
                files_created=tester_result.get("files_created", [])
            ))
        
        return results
    
    def run_documentation_phase(self) -> dict:
        self.console.print("\n[bold cyan]═══ ФАЗА 4: ДОКУМЕНТАЦИЯ ═══[/bold cyan]")
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
            task = progress.add_task("Documentalist работает...", total=None)
            result = self.agent_manager.run_agent(
                "documentalist",
                f"Напиши документацию для проекта. Созданные файлы: {self.context.get_all_files()}"
            )
            progress.update(task, completed=True)
        
        if result.get("status") == "success":
            self.context.add_result(AgentResult(
                agent="documentalist",
                status="success",
                files_created=result.get("files_created", [])
            ))
        
        return result
    
    def generate_report(self) -> dict:
        self.console.print("\n[bold green]═══ ФИНАЛЬНЫЙ ОТЧЁТ ═══[/bold green]")
        
        report = {
            "project_name": self.project_path.name,
            "created_at": datetime.now().isoformat(),
            "path": str(self.project_path),
            "status": "success" if all(r.status == "success" for r in self.context.agent_results.values()) else "partial",
            "agents_worked": list(self.context.agent_results.keys()),
            "total_files": len(self.context.get_all_files()),
            "files": self.context.get_all_files(),
            "events": self.events
        }
        
        (self.project_path / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
        self.db.update_project_status(self.project_id, "completed")
        
        self.console.print(Panel.fit(
            f"[bold green]✓ Проект создан![/bold green]\n\n"
            f"Путь: {self.project_path}\n"
            f"Файлов: {report['total_files']}\n"
            f"Агентов: {len(report['agents_worked'])}",
            border_style="green"
        ))
        
        return report
    
    def run_full_pipeline(self, project_name: str, requirements_path: str) -> dict:
        try:
            self.create_project(project_name, requirements_path)
            self.scan_hardware()
            
            self.run_planning_phase()
            self.run_architecture_phase()
            self.run_development_phase()
            self.run_documentation_phase()
            
            report = self.generate_report()
            
            self.console.print("\n[bold green]✓ Все фазы завершены![/bold green]")
            return report
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            self.console.print(f"[bold red]Ошибка:[/bold red] {e}")
            if self.project_id:
                self.db.update_project_status(self.project_id, "error")
            raise


def main():
    parser = argparse.ArgumentParser(description="AI Team System v2")
    parser.add_argument("--profile", choices=["light", "medium", "heavy"], 
                       default="medium", help="Профиль железа")
    parser.add_argument("--project-name", help="Имя проекта")
    parser.add_argument("--requirements", help="Путь к requirements.md или текст")
    
    args = parser.parse_args()
    
    system = AITeamSystem(profile=args.profile)
    system.scan_hardware()
    
    if args.project_name and args.requirements:
        system.run_full_pipeline(args.project_name, args.requirements)
    else:
        console.print("[yellow]Используйте:[/yellow]")
        console.print("  python -m core.main --project-name myapp --requirements 'описание'")
        console.print("  python -m core.main --project-name myapp --requirements requirements.md")


if __name__ == "__main__":
    main()
