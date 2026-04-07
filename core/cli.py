"""
Better CLI with Click
"""

import click
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .main import AITeamSystem
from .zip_export import ZipExporter
from .token_tracker import TokenTracker

console = Console()


@click.group()
@click.version_option(version="4.0.0")
def cli():
    """AI Team System — Мультиагентная система разработки ПО"""
    pass


@cli.command()
@click.option('--project-name', '-n', required=True, help='Имя проекта')
@click.option('--requirements', '-r', required=True, help='Описание или путь к файлу')
@click.option('--profile', '-p', default='medium', type=click.Choice(['light', 'medium', 'heavy']))
@click.option('--interactive', '-i', is_flag=True, help='Интерактивный режим')
@click.option('--dry-run', is_flag=True, help='Тест без вызова LLM')
def run(project_name, requirements, profile, interactive, dry_run):
    """Запустить создание проекта"""
    system = AITeamSystem(profile=profile)
    system.scan_hardware()
    
    if dry_run:
        console.print("[yellow]Dry-run режим — симуляция без LLM[/yellow]")
        from .dry_run import DryRunSimulator
        sim = DryRunSimulator(Path.home() / "projects" / f"{project_name}_dry")
        sim.simulate_agent("teamlead", "Планирование")
        sim.simulate_agent("architect", "Архитектура")
        sim.simulate_agent("backend", "Backend")
        sim.simulate_agent("frontend", "Frontend")
        sim.simulate_agent("devops", "DevOps")
        sim.simulate_agent("tester", "Тесты")
        sim.simulate_agent("documentalist", "Документация")
        sim.save_plan()
        plan = sim.get_plan()
        console.print(f"[green]✓ План создан: {plan['total_actions']} действий[/green]")
        return
    
    system.run_full_pipeline(project_name, requirements, interactive=interactive)


@cli.command()
@click.option('--project-name', '-n', required=True)
@click.option('--output', '-o', default=None, help='Путь к ZIP файлу')
def export(project_name, output):
    """Экспорт проекта в ZIP"""
    projects_dir = Path.home() / "projects"
    project_path = projects_dir / project_name
    
    if not project_path.exists():
        console.print(f"[red]Проект не найден: {project_name}[/red]")
        return
    
    exporter = ZipExporter(project_path)
    info = exporter.get_size_info()
    
    console.print(f"Проект: {project_name}")
    console.print(f"Файлов: {info['total_files']}")
    console.print(f"Размер: {info['total_size_mb']} MB")
    
    output_path = exporter.export(Path(output) if output else None)
    console.print(f"[green]✓ Экспортировано: {output_path}[/green]")


@cli.command()
@click.option('--project-name', '-n', required=True)
def stats(project_name):
    """Показать статистику проекта"""
    projects_dir = Path.home() / "projects"
    project_path = projects_dir / project_name
    
    if not project_path.exists():
        console.print(f"[red]Проект не найден: {project_name}[/red]")
        return
    
    tracker = TokenTracker(project_path)
    
    report_file = project_path / "token_usage.json"
    if report_file.exists():
        import json
        stats_data = json.loads(report_file.read_text())
        
        table = Table(title=f"Статистика: {project_name}")
        table.add_column("Метрика", style="cyan")
        table.add_column("Значение", style="green")
        
        table.add_row("Всего вызовов", str(stats_data.get("total_calls", 0)))
        table.add_row("Токенов", f"{stats_data.get('total_tokens', 0):,}")
        table.add_row("Стоимость", f"${stats_data.get('total_cost', 0):.4f}")
        table.add_row("Файлов", str(stats_data.get("total_files", 0)))
        
        console.print(table)
    else:
        console.print("[yellow]Статистика не найдена[/yellow]")


@cli.command()
def list_projects():
    """Список проектов"""
    projects_dir = Path.home() / "projects"
    
    if not projects_dir.exists():
        console.print("[yellow]Нет проектов[/yellow]")
        return
    
    table = Table(title="Проекты")
    table.add_column("Имя", style="cyan")
    table.add_column("Дата", style="green")
    table.add_column("Файлов", style="yellow")
    
    for p in sorted(projects_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_dir():
            files = len(list(p.rglob("*")))
            date = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            table.add_row(p.name, date, str(files))
    
    console.print(table)


@cli.command()
def providers():
    """Показать доступные провайдеры"""
    from .model_router import ModelRouter
    
    router = ModelRouter()
    status = router.get_status()
    
    table = Table(title="Провайдеры")
    table.add_column("Провайдер", style="cyan")
    table.add_column("Статус", style="green")
    table.add_column("Модели", style="yellow")
    
    models = router.list_models()
    for provider, enabled in router.providers.items():
        is_enabled = enabled if isinstance(enabled, bool) else enabled.get("enabled", False)
        status_text = "✓" if is_enabled else "✗"
        model_list = ", ".join(models.get(provider, [])[:3])
        table.add_row(provider, status_text, model_list)
    
    console.print(table)


if __name__ == "__main__":
    cli()
