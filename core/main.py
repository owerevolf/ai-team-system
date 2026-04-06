"""
AI Team System - Main Orchestrator
Главный скрипт для запуска системы
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table

from .agent_manager import AgentManager
from .model_router import ModelRouter
from .database import Database
from .logger import setup_logger
from .system_scanner import SystemScanner

console = Console()

class AITeamSystem:
    def __init__(self, profile: str = "medium"):
        self.profile = profile
        self.project_path = None
        self.console = console
        
        self.console.print(Panel.fit(
            "[bold cyan]AI Team System[/bold cyan]\n"
            "Мультиагентная система разработки ПО",
            border_style="cyan"
        ))
        
        self.logger = setup_logger("ai_team_system")
        self.db = Database()
        self.scanner = SystemScanner()
        self.model_router = ModelRouter(profile)
        self.agent_manager = AgentManager(self.model_router)
        
    def scan_hardware(self) -> dict:
        """Сканирование железа и выбор оптимального профиля"""
        info = self.scanner.get_info()
        
        table = Table(title="Информация о системе")
        table.add_column("Параметр", style="cyan")
        table.add_column("Значение", style="green")
        
        table.add_row("CPU", f"{info['cpu']['cores']} ядер")
        table.add_row("RAM", f"{info['ram']['total_gb']} GB")
        table.add_row("GPU", info['gpu']['name'] or "Нет")
        table.add_row("VRAM", f"{info['gpu']['vram_gb']} GB" if info['gpu']['vram_gb'] else "N/A")
        table.add_row("Ollama", "Доступна" if info['ollama']['available'] else "Недоступна")
        
        self.console.print(table)
        
        return info
    
    def create_project(self, project_name: str, requirements_path: str) -> dict:
        """Создание нового проекта"""
        self.console.print(f"\n[bold yellow]Создание проекта:[/bold yellow] {project_name}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = Path.home() / "projects" / f"{project_name}_{timestamp}"
        
        self.project_path = project_dir
        self.agent_manager.set_project_path(project_dir)
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "code" / "backend").mkdir(parents=True, exist_ok=True)
        (project_dir / "code" / "frontend").mkdir(parents=True, exist_ok=True)
        (project_dir / "code" / "shared").mkdir(parents=True, exist_ok=True)
        (project_dir / "tests" / "backend_tests").mkdir(parents=True, exist_ok=True)
        (project_dir / "tests" / "frontend_tests").mkdir(parents=True, exist_ok=True)
        (project_dir / "tests" / "integration_tests").mkdir(parents=True, exist_ok=True)
        (project_dir / "docs").mkdir(parents=True, exist_ok=True)
        (project_dir / ".agents").mkdir(parents=True, exist_ok=True)
        (project_dir / ".logs").mkdir(parents=True, exist_ok=True)
        
        with open(project_dir / "requirements.md", "w") as f:
            if Path(requirements_path).exists():
                f.write(Path(requirements_path).read_text())
            else:
                f.write(requirements_path)
        
        self.logger.info(f"Проект создан: {project_dir}")
        
        return {
            "project_name": project_name,
            "path": str(project_dir),
            "created_at": datetime.now().isoformat()
        }
    
    def run_planning_phase(self) -> dict:
        """Фаза планирования - TeamLead анализирует требования"""
        self.console.print("\n[bold cyan]=== ФАЗА 1: ПЛАНИРОВАНИЕ ===[/bold cyan]")
        
        if not self.project_path:
            raise RuntimeError("Проект не создан")
        
        requirements_file = self.project_path / "requirements.md"
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("TeamLead анализирует требования...", total=None)
            
            result = self.agent_manager.run_agent(
                "teamlead",
                f"Проанализируй requirements.md и создай план работ:\n{requirements_file.read_text()}"
            )
            
            progress.update(task, completed=True)
        
        return result
    
    def run_architecture_phase(self) -> dict:
        """Фаза проектирования - Architect создаёт архитектуру"""
        self.console.print("\n[bold cyan]=== ФАЗА 2: ПРОЕКТИРОВАНИЕ ===[/bold cyan]")
        
        requirements_file = self.project_path / "requirements.md"
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Architect проектирует архитектуру...", total=None)
            
            result = self.agent_manager.run_agent(
                "architect",
                f"Спроектируй архитектуру для проекта:\n{requirements_file.read_text()}"
            )
            
            progress.update(task, completed=True)
        
        return result
    
    def run_development_phase(self) -> dict:
        """Фаза разработки - параллельная работа агентов"""
        self.console.print("\n[bold cyan]=== ФАЗА 3: РАЗРАБОТКА ===[/bold cyan]")
        
        results = {}
        
        agents = ["backend", "frontend", "devops", "tester"]
        
        for agent in agents:
            self.console.print(f"[yellow]Запуск агента:[/yellow] {agent}")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task(f"{agent} работает...", total=None)
                
                result = self.agent_manager.run_agent(
                    agent,
                    f"Выполни свою часть работы в проекте {self.project_path}"
                )
                
                results[agent] = result
                progress.update(task, completed=True)
        
        return results
    
    def run_documentation_phase(self) -> dict:
        """Фаза документирования"""
        self.console.print("\n[bold cyan]=== ФАЗА 4: ДОКУМЕНТАЦИЯ ===[/bold cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Documentalist пишет документацию...", total=None)
            
            result = self.agent_manager.run_agent(
                "documentalist",
                f"Напиши документацию для проекта {self.project_path}"
            )
            
            progress.update(task, completed=True)
        
        return result
    
    def generate_report(self) -> dict:
        """Генерация финального отчёта"""
        self.console.print("\n[bold green]=== ФИНАЛЬНЫЙ ОТЧЁТ ===[/bold green]")
        
        report = {
            "project_name": self.project_path.name,
            "created_at": datetime.now().isoformat(),
            "path": str(self.project_path),
            "status": "success",
            "agents_worked": ["teamlead", "architect", "backend", "frontend", "devops", "tester", "documentalist"],
            "files_created": len(list(self.project_path.rglob("*"))),
        }
        
        report_file = self.project_path / "report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        self.console.print(Panel.fit(
            f"[bold green]Проект успешно создан![/bold green]\n\n"
            f"Путь: {self.project_path}\n"
            f"Файлов: {report['files_created']}",
            border_style="green"
        ))
        
        return report
    
    def run_full_pipeline(self, project_name: str, requirements_path: str) -> dict:
        """Запуск полного цикла разработки"""
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
            raise


def main():
    parser = argparse.ArgumentParser(description="AI Team System")
    parser.add_argument("--profile", choices=["light", "medium", "heavy"], 
                       default="medium", help="Профиль железа")
    parser.add_argument("--project-name", help="Имя проекта")
    parser.add_argument("--requirements", help="Путь к requirements.md или текст требований")
    
    args = parser.parse_args()
    
    system = AITeamSystem(profile=args.profile)
    system.scan_hardware()
    
    if args.project_name and args.requirements:
        system.run_full_pipeline(args.project_name, args.requirements)
    else:
        console.print("[yellow]Интерактивный режим пока не реализован.[/yellow]")
        console.print("Используйте: python core/main.py --project-name myapp --requirements requirements.md")


if __name__ == "__main__":
    main()
