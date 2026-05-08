"""
Database - Работа с SQLite базой данных
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import threading


class Database:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path.home() / ".ai_team" / "ai_team.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """Инициализация таблиц"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    profile TEXT,
                    requirements TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    name TEXT NOT NULL,
                    role TEXT,
                    status TEXT DEFAULT 'idle',
                    started_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    agent TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'medium',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    result TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    agent TEXT,
                    level TEXT,
                    message TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kanban_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    agent TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'todo',
                    priority TEXT DEFAULT 'medium',
                    column_id TEXT DEFAULT 'todo',
                    position INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            
            conn.commit()
            conn.close()
    
    def create_project(self, name: str, path: str, profile: str, requirements: str) -> int:
        """Создание нового проекта"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO projects (name, path, created_at, profile, requirements)
                VALUES (?, ?, ?, ?, ?)
            """, (name, path, datetime.now().isoformat(), profile, requirements))
            
            project_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return project_id
    
    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Получение проекта по ID"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._row_to_dict(cursor, row, "projects")
            return None
    
    def update_project_status(self, project_id: int, status: str):
        """Обновление статуса проекта"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE projects SET status = ? WHERE id = ?", (status, project_id))
            conn.commit()
            conn.close()
    
    def create_task(self, project_id: int, agent: str, title: str, 
                   description: str = None, priority: str = "medium") -> int:
        """Создание задачи"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO tasks (project_id, agent, title, description, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (project_id, agent, title, description, priority, datetime.now().isoformat()))
            
            task_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return task_id
    
    def update_task_status(self, task_id: int, status: str, result: str = None):
        """Обновление статуса задачи"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if status == "in_progress":
                cursor.execute(
                    "UPDATE tasks SET status = ?, started_at = ? WHERE id = ?",
                    (status, datetime.now().isoformat(), task_id)
                )
            elif status == "completed":
                cursor.execute(
                    "UPDATE tasks SET status = ?, completed_at = ?, result = ? WHERE id = ?",
                    (status, datetime.now().isoformat(), result, task_id)
                )
            else:
                cursor.execute(
                    "UPDATE tasks SET status = ? WHERE id = ?",
                    (status, task_id)
                )
            
            conn.commit()
            conn.close()
    
    def get_tasks(self, project_id: int, agent: str = None) -> List[Dict]:
        """Получение задач проекта"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if agent:
                cursor.execute(
                    "SELECT * FROM tasks WHERE project_id = ? AND agent = ? ORDER BY priority",
                    (project_id, agent)
                )
            else:
                cursor.execute(
                    "SELECT * FROM tasks WHERE project_id = ? ORDER BY priority",
                    (project_id,)
                )
            
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_dict(cursor, row, "tasks") for row in rows]
    
    def log(self, project_id: int, agent: str, level: str, message: str):
        """Логирование события"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO logs (project_id, agent, level, message, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (project_id, agent, level, message, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
    
    def get_logs(self, project_id: int, limit: int = 100) -> List[Dict]:
        """Получение логов проекта"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM logs WHERE project_id = ? 
                ORDER BY created_at DESC LIMIT ?
            """, (project_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_dict(cursor, row, "logs") for row in rows]
    
    def _row_to_dict(self, cursor, row, table: str) -> Dict:
        """Конвертация строки в словарь"""
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    
    # ══════════════════════════════════════
    #  KANBAN TASKS
    # ══════════════════════════════════════
    
    def create_kanban_task(self, agent: str, title: str, description: str = None,
                          priority: str = "medium", column_id: str = "todo",
                          project_id: int = None) -> int:
        """Создание задачи канбан"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO kanban_tasks (project_id, agent, title, description, status, priority, column_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (project_id, agent, title, description, column_id, priority, column_id,
                  datetime.now().isoformat()))
            task_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return task_id
    
    def get_kanban_tasks(self, project_id: int = None, column_id: str = None) -> List[Dict]:
        """Получение задач канбан"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            query = "SELECT * FROM kanban_tasks"
            params = []
            if project_id:
                query += " WHERE project_id = ?"
                params.append(project_id)
            if column_id:
                query += " AND column_id = ?" if "WHERE" in query else " WHERE column_id = ?"
                params.append(column_id)
            query += " ORDER BY position, created_at DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            return [self._row_to_dict(cursor, row, "kanban_tasks") for row in rows]
    
    def update_kanban_task(self, task_id: int, **kwargs) -> bool:
        """Обновление задачи канбан"""
        allowed = {"title", "description", "status", "priority", "column_id", "position"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        updates["updated_at"] = datetime.now().isoformat()
        # Synchronize status with column_id if column_id changed
        if "column_id" in updates and "status" not in updates:
            updates["status"] = updates["column_id"]
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [task_id]
            cursor.execute(f"UPDATE kanban_tasks SET {set_clause} WHERE id = ?", values)
            conn.commit()
            conn.close()
            return True
    
    def delete_kanban_task(self, task_id: int) -> bool:
        """Удаление задачи канбан"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM kanban_tasks WHERE id = ?", (task_id,))
            conn.commit()
            conn.close()
            return True
    
    def close(self):
        """Закрытие соединения"""
        pass
