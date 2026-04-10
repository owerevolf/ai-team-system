#!/usr/bin/env python3
"""
FIX_AGENTS v2.0 — Автоматическое исправление промптов на основе отчёта тестов
Исправляет промпты чтобы агенты РЕАГИРОВАЛИ на содержание ответа пользователя
"""
import json
import re
import sys
import logging
from pathlib import Path
from datetime import datetime

# Логирование в отдельный файл
LOG_FILE = Path(__file__).parent / 'fix_agents.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / 'prompts' / 'roles'
REPORT_PATH = Path(__file__).parent / 'TEST_REPORT.json'
FIXES_LOG = []


def load_report():
    """Загрузить отчёт тестов"""
    if not REPORT_PATH.exists():
        logger.error('❌ TEST_REPORT.json не найден — запусти сначала auto_tester.py')
        return None
    with open(REPORT_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_agent_files(agent_name):
    """Найти все файлы промптов для агента"""
    patterns = [
        PROMPTS_DIR / f'{agent_name}_zero.md',
        PROMPTS_DIR / f'{agent_name}_beginner.md',
        PROMPTS_DIR / f'{agent_name}.md',
        PROMPTS_DIR / f'{agent_name}_advanced.md',
    ]
    return [p for p in patterns if p.exists()]


def fix_hearing_issue(agent_name, filepath):
    """
    Исправить промпт чтобы агент СЛЫШАЛ пользователя.
    Возвращает True если изменения применлены.
    """
    content = filepath.read_text(encoding='utf-8')
    original = content
    changes_made = []

    # 1. Проверяем что есть инструкция реагировать на содержание
    if not any(phrase in content.lower() for phrase in [
        'реагируй на содержание', 'анализируй ответ', 'конкретно по теме',
        'не используй шаблон', 'не общий скрипт'
    ]):
        content += '\n\n'
        content += '## ═══════════════════════════════════════\n'
        content += '## ВАЖНО: СЛЫШЬ ПОЛЬЗОВАТЕЛЯ\n'
        content += '## ═══════════════════════════════════════\n'
        content += 'Ты ДОЛЖЕН реагировать конкретно на то что написал пользователь.\n'
        content += 'НЕ отвечай общим скриптом приветствия.\n'
        content += 'НЕ повторяй одну и ту же фразу.\n'
        content += 'Проанализируй СОДЕРЖАНИЕ ответа и отвечай по теме.\n'
        content += 'Если пользователь написал "калькулятор" — говори о калькуляторе.\n'
        content += 'Если написал "тренажёр печати" — говори о тренажёре печати.\n'
        changes_made.append('Добавлена инструкция "слышь пользователя"')

    # 2. Убираем запрет на tool_call если он мешает (для zero режима)
    # Оставляем но делаем мягче
    
    # 3. Добавляем персональный стиль для каждого агента
    style_additions = {
        'teamlead': (
            '\n## СТИЛЬ: Ты TeamLead — сначала пойми что хочет пользователь, '
            'потом дай чёткий план. Говори конкретно по теме.\n'
        ),
        'architect': (
            '\n## СТИЛЬ: Ты Architect — анализируй запрос и предлагай '
            'структуру КОНКРЕТНО под то что просит пользователь.\n'
        ),
        'backend': (
            '\n## СТИЛЬ: Ты Backend Dev — пиши код КОНКРЕТНО под задачу '
            'пользователя, не абстрактные примеры.\n'
        ),
        'frontend': (
            '\n## СТИЛЬ: Ты Frontend Dev — делай UI КОНКРЕТНО под то что '
            'просит пользователь, не шаблонные страницы.\n'
        ),
        'devops': (
            '\n## СТИЛЬ: Ты DevOps — настраивай инфраструктуру КОНКРЕТНО '
            'под проект пользователя.\n'
        ),
        'tester': (
            '\n## СТИЛЬ: Ты Tester — тестируй КОНКРЕТНО то что написал '
            'пользователь, не абстрактные сценарии.\n'
        ),
        'documentalist': (
            '\n## СТИЛЬ: Ты Documentalist — документируй КОНКРЕТНО проект '
            'пользователя, не общую теорию.\n'
        ),
    }

    for agent, style_text in style_additions.items():
        if agent in agent_name.lower():
            if style_text.strip() not in content:
                content += style_text
                changes_made.append(f'Добавлен стиль агента {agent}')
            break

    if content != original:
        filepath.write_text(content, encoding='utf-8')
        FIXES_LOG.extend(changes_made)
        logger.info(f'  ✅ {filepath.name}: {", ".join(changes_made)}')
        return True
    
    logger.info(f'  ⏭️ {filepath.name}: без изменений')
    return False


def analyze_and_fix(report, iteration=1):
    """Анализировать отчёт и применить исправления"""
    logger.info('=' * 60)
    logger.info(f'АНАЛИЗ ОТЧЁТА И ИСПРАВЛЕНИЕ — Итерация #{iteration}')
    logger.info('=' * 60)

    hearing = report.get('agent_hearing', {})
    fixes_applied = 0

    # Проверяем какие сценарии НЕ СЛЫШАТ
    not_hearing = [k for k, v in hearing.items() if v == 'НЕ СЛЫШИТ']
    
    if not not_hearing:
        logger.info('✅ Агент СЛЫШИТ пользователя во всех сценариях!')
        return False

    logger.warning(f'⚠️ НЕ СЛЫШИТ в сценариях: {not_hearing}')

    # Исправляем ВСЕ agent промпты (teamlead, architect, backend, frontend и т.д.)
    agents = ['teamlead', 'architect', 'backend', 'frontend', 'devops', 'tester', 'documentalist']
    
    for agent in agents:
        files = get_agent_files(agent)
        for filepath in files:
            # Для zero режима — максимальные исправления
            if 'zero' in filepath.name or 'beginner' in filepath.name:
                if fix_hearing_issue(agent, filepath):
                    fixes_applied += 1
            else:
                # Для основных — только стиль
                content = filepath.read_text(encoding='utf-8')
                if 'реагируй на содержание' not in content.lower():
                    content += (
                        f'\n\n## ВАЖНО: Реагируй конкретно на запрос пользователя. '
                        f'Не используй шаблонные ответы.\n'
                    )
                    filepath.write_text(content, encoding='utf-8')
                    fixes_applied += 1
                    FIXES_LOG.append(f'{filepath.name}: добавлена конкретика')
                    logger.info(f'  ✅ {filepath.name}: конкретика')

    # Дополнительно: проверяем welcome.html на проблемы с отправкой сообщений
    welcome_file = Path(__file__).parent / 'web_ui' / 'templates' / 'welcome.html'
    if welcome_file.exists():
        content = welcome_file.read_text()
        # Проверяем что отправка сообщений работает корректно
        if 'sendMessage' in content or 'send_msg' in content:
            # Проверяем что текст сообщения передаётся в API
            if 'state.projectIdea' in content or 'state.userMessage' in content:
                logger.info('  ✅ welcome.html: отправка сообщений корректна')
            else:
                logger.warning('  ⚠️ welcome.html: возможно проблема с передачей сообщения')

    logger.info('\n' + '=' * 60)
    logger.info(f'ИСПРАВЛЕНИЙ ПРИМЕНЕНО: {fixes_applied}')
    for fix in FIXES_LOG:
        logger.info(f'  → {fix}')
    logger.info('=' * 60)

    return fixes_applied > 0


if __name__ == '__main__':
    logger.info('🔧 Fix Agents v2.0')
    
    iteration = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    report = load_report()
    if not report:
        sys.exit(1)

    fixed = analyze_and_fix(report, iteration)
    
    if fixed:
        logger.info('\n✅ Промпты исправлены! Перезапусти сервер и проверь снова.')
    else:
        logger.info('\n✅ Исправлений не потребовалось!')
    
    sys.exit(0 if not fixed else 0)
