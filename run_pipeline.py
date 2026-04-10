#!/usr/bin/env python3
"""
PIPELINE RUNNER — Полный цикл: test → fix → retest → RESULT.md
"""
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent
AUTO_TESTER = PROJECT_DIR / 'auto_tester.py'
FIX_AGENTS = PROJECT_DIR / 'fix_agents.py'
REPORT_PATH = PROJECT_DIR / 'TEST_REPORT.json'
RESULT_PATH = PROJECT_DIR / 'RESULT.md'

MAX_ITERATIONS = 3


def run_script(script_path, iteration):
    """Запустить скрипт и вернуть exit code"""
    logger.info(f'\n{"="*60}')
    logger.info(f'ИТЕРАЦИЯ {iteration}: {script_path.name}')
    logger.info(f'{"="*60}')
    
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=PROJECT_DIR,
        capture_output=False,
        timeout=600
    )
    return result.returncode


def load_report():
    """Загрузить отчёт"""
    if not REPORT_PATH.exists():
        return None
    with open(REPORT_PATH) as f:
        return json.load(f)


def check_if_fixed(report_before, report_after):
    """Проверить что исправления помогли"""
    before_failed = report_before.get('summary', {}).get('failed', 999)
    after_failed = report_after.get('summary', {}).get('failed', 999)
    
    return after_failed < before_failed


def main():
    logger.info('╔' + '═' * 58 + '╗')
    logger.info('║' + ' ' * 10 + 'PIPELINE: TEST → FIX → RETEST' + ' ' * 17 + '║')
    logger.info('╚' + '═' * 58 + '╝')
    logger.info(f'Начало: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    logger.info(f'Максимум итераций: {MAX_ITERATIONS}')
    
    # ===== ШАГ 1: Первичный тест =====
    logger.info('\n' + '█' * 60)
    logger.info('█' + ' ' * 58 + '█')
    logger.info('█  ШАГ 1: ПЕРВИЧНОЕ ТЕСТИРОВАНИЕ' + ' ' * 27 + '█')
    logger.info('█' + ' ' * 58 + '█')
    logger.info('█' * 60)
    
    exit_code = run_script(AUTO_TESTER, 1)
    report_before = load_report()
    
    if not report_before:
        logger.error('❌ Не удалось загрузить отчёт')
        sys.exit(1)
    
    initial_failed = report_before.get('summary', {}).get('failed', 0)
    logger.info(f'\n📊 Первичный результат: {initial_failed} проваленных тестов')
    
    if initial_failed == 0:
        logger.info('✅ Все тесты пройдены с первого раза! Исправления не нужны.')
        # Генерируем RESULT.md
        from fix_agents import generate_result_md
        generate_result_md(report_before)
        sys.exit(0)
    
    # ===== ШАГ 2-4: Цикл fix → retest =====
    for iteration in range(1, MAX_ITERATIONS + 1):
        logger.info('\n' + '█' * 60)
        logger.info(f'█  ШАГ {iteration + 1}: ИТЕРАЦИЯ ИСПРАВЛЕНИЯ #{iteration}' + ' ' * (20 - len(str(iteration))) + '█')
        logger.info('█' * 60)
        
        # Fix
        run_script(FIX_AGENTS, iteration)
        
        # Retest
        run_script(AUTO_TESTER, iteration + 1)
        report_after = load_report()
        
        if not report_after:
            logger.error('❌ Не удалось загрузить отчёт после исправления')
            break
        
        after_failed = report_after.get('summary', {}).get('failed', 0)
        logger.info(f'\n📊 После итерации #{iteration}: {after_failed} проваленных тестов')
        
        if after_failed == 0:
            logger.info('✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!')
            break
        
        if not check_if_fixed(report_before, report_after):
            logger.info('⚠️ Исправления не помогли — останавливаю цикл')
            break
        
        report_before = report_after
    
    # ===== ФИНАЛЬНЫЙ ОТЧЁТ =====
    logger.info('\n' + '█' * 60)
    logger.info('█  ФИНАЛЬНЫЙ ОТЧЁТ' + ' ' * 39 + '█')
    logger.info('█' * 60)
    
    from fix_agents import generate_result_md, FIXES_LOG
    final_report = load_report()
    generate_result_md(final_report)
    
    summary = final_report.get('summary', {})
    logger.info(f'\n📈 ИТОГО:')
    logger.info(f'  Тестов: {summary.get("total_tests", 0)}')
    logger.info(f'  Пройдено: {summary.get("passed", 0)} ✅')
    logger.info(f'  Провалено: {summary.get("failed", 0)} ❌')
    logger.info(f'  Статус: {summary.get("status", "НЕИЗВЕСТНО")}')
    logger.info(f'\n📄 Отчёты:')
    logger.info(f'  TEST_REPORT.json: {REPORT_PATH}')
    logger.info(f'  RESULT.md: {RESULT_PATH}')
    logger.info(f'  auto_test.log: {PROJECT_DIR / "auto_test.log"}')
    logger.info(f'  screenshots/: {PROJECT_DIR / "screenshots"}')


if __name__ == '__main__':
    main()
