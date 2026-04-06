"""
Git Manager - Работа с Git коммитами
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class GitManager:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.git_dir = self.repo_path / ".git"
    
    def init(self) -> bool:
        """Инициализация репозитория"""
        try:
            result = self.run_command("git init")
            if result["success"]:
                self.run_command('git config user.email "ai-team@system.local"')
                self.run_command('git config user.name "AI Team System"')
            return result["success"]
        except Exception as e:
            return False
    
    def add_all(self) -> bool:
        """Добавление всех файлов"""
        result = self.run_command("git add -A")
        return result["success"]
    
    def commit(self, message: str) -> Optional[str]:
        """Создание коммита"""
        result = self.run_command(f'git commit -m "{message}"')
        if result["success"]:
            return self.get_last_commit_hash()
        return None
    
    def get_last_commit_hash(self, short: bool = True) -> Optional[str]:
        """Получение хеша последнего коммита"""
        flag = "--short" if short else ""
        result = self.run_command(f"git rev-parse {flag} HEAD")
        if result["success"]:
            return result["stdout"].strip()
        return None
    
    def get_commit_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """Получение истории коммитов"""
        result = self.run_command(
            f"git log --oneline --format='%h|%s|%an|%ad' --date=iso -n {limit}"
        )
        
        if not result["success"]:
            return []
        
        commits = []
        for line in result["stdout"].strip().split("\n"):
            if "|" in line:
                parts = line.split("|")
                if len(parts) >= 4:
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1],
                        "author": parts[2],
                        "date": parts[3]
                    })
        
        return commits
    
    def get_status(self) -> Dict[str, List[str]]:
        """Получение статуса репозитория"""
        result = self.run_command("git status --porcelain")
        
        if not result["success"]:
            return {"modified": [], "untracked": [], "staged": []}
        
        modified = []
        untracked = []
        staged = []
        
        for line in result["stdout"].strip().split("\n"):
            if not line:
                continue
            
            status = line[:2]
            filename = line[3:]
            
            if status == "??":
                untracked.append(filename)
            elif status[0] in ["M", "A", "D", "R"]:
                staged.append(filename)
            if status[1] == "M":
                modified.append(filename)
        
        return {
            "modified": modified,
            "untracked": untracked,
            "staged": staged
        }
    
    def create_branch(self, branch_name: str) -> bool:
        """Создание ветки"""
        result = self.run_command(f"git checkout -b {branch_name}")
        return result["success"]
    
    def checkout(self, branch: str) -> bool:
        """Переключение на ветку"""
        result = self.run_command(f"git checkout {branch}")
        return result["success"]
    
    def get_branches(self) -> List[str]:
        """Получение списка веток"""
        result = self.run_command("git branch")
        if result["success"]:
            return [b.strip().replace("* ", "") for b in result["stdout"].strip().split("\n")]
        return []
    
    def diff(self, file: str = None) -> str:
        """Получение изменений"""
        cmd = "git diff"
        if file:
            cmd += f" -- {file}"
        
        result = self.run_command(cmd)
        return result["stdout"] if result["success"] else ""
    
    def is_repo(self) -> bool:
        """Проверка наличия репозитория"""
        return self.git_dir.exists() and self.git_dir.is_dir()
    
    def run_command(self, command: str) -> Dict[str, Any]:
        """Выполнение git команды"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command timeout",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
