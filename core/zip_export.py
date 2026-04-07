"""
ZIP Export - Экспорт проекта в архив
"""

import zipfile
import os
from pathlib import Path
from typing import Optional, List
from datetime import datetime


class ZipExporter:
    def __init__(self, project_path: Path):
        self.project_path = project_path
    
    def export(self, output_path: Optional[Path] = None, 
               exclude_dirs: Optional[List[str]] = None) -> Path:
        """Экспорт проекта в ZIP"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path.home() / f"{self.project_path.name}_{timestamp}.zip"
        
        exclude = set(exclude_dirs or [".git", "venv", "__pycache__", ".pytest_cache"])
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(self.project_path):
                # Исключаем директории
                dirs[:] = [d for d in dirs if d not in exclude]
                
                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix in ['.pyc', '.pyo', '.db']:
                        continue
                    
                    arcname = file_path.relative_to(self.project_path.parent)
                    zf.write(file_path, arcname)
        
        return output_path
    
    def get_size_info(self) -> dict:
        """Информация о размере проекта"""
        total_files = 0
        total_size = 0
        by_ext = {}
        
        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in ['.git', 'venv', '__pycache__']]
            
            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix or '(no ext)'
                size = file_path.stat().st_size
                
                total_files += 1
                total_size += size
                by_ext[ext] = by_ext.get(ext, 0) + 1
        
        return {
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_extension": by_ext
        }
