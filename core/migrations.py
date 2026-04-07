"""
Auto Migrations - Генерация миграций при изменении моделей
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class MigrationGenerator:
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.migrations_dir = project_path / "migrations"
    
    def generate_from_models(self, models_content: Dict[str, str]) -> List[str]:
        """Генерация миграций из моделей"""
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        
        created = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for model_name, model_code in models_content.items():
            migration = self._create_migration(model_name, model_code, timestamp)
            if migration:
                created.append(migration)
        
        return created
    
    def _create_migration(self, model_name: str, model_code: str, timestamp: str) -> Optional[str]:
        """Создание одной миграции"""
        fields = self._parse_model_fields(model_code)
        if not fields:
            return None
        
        table_name = model_name.lower() + "s"
        migration_name = f"create_{table_name}"
        filename = f"{timestamp}_{migration_name}.py"
        migration_path = self.migrations_dir / filename
        
        content = self._generate_migration_code(table_name, fields, migration_name)
        migration_path.write_text(content)
        
        return str(migration_path.relative_to(self.project_path))
    
    def _parse_model_fields(self, model_code: str) -> List[Dict[str, Any]]:
        """Парсинг полей модели"""
        fields = []
        
        column_pattern = r"(\w+)\s*=\s*Column\((\w+)"
        matches = re.findall(column_pattern, model_code)
        
        for name, col_type in matches:
            field_info = {
                "name": name,
                "type": self._map_column_type(col_type),
                "primary_key": "primary_key" in model_code.split(name)[1].split("=")[0] if name in model_code else False,
                "nullable": "nullable=False" not in model_code.split(name)[1].split(")")[0] if name in model_code else True
            }
            fields.append(field_info)
        
        return fields
    
    def _map_column_type(self, col_type: str) -> str:
        """Маппинг типов SQLAlchemy на SQL"""
        type_map = {
            "Integer": "INTEGER",
            "String": "VARCHAR(255)",
            "Text": "TEXT",
            "Boolean": "BOOLEAN",
            "DateTime": "TIMESTAMP",
            "Float": "FLOAT",
            "BigInteger": "BIGINT"
        }
        return type_map.get(col_type, "TEXT")
    
    def _generate_migration_code(self, table_name: str, fields: List[Dict], migration_name: str) -> str:
        """Генерация кода миграции"""
        columns = []
        for f in fields:
            col = f"    sa.Column('{f['name']}', sa.{f['type']}"
            if f.get("primary_key"):
                col += ", primary_key=True"
            if not f.get("nullable") and not f.get("primary_key"):
                col += ", nullable=False"
            col += ")"
            columns.append(col)
        
        columns_str = ",\n".join(columns)
        
        return f'''"""{migration_name}

Revision ID: {migration_name}
Revises: 
Create Date: {datetime.now().isoformat()}
"""
from alembic import op
import sqlalchemy as sa

revision = '{migration_name}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        '{table_name}',
{columns_str}
    )


def downgrade():
    op.drop_table('{table_name}')
'''
