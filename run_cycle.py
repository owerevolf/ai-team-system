#!/usr/bin/env python3
"""
RUN_CYCLE — Полный цикл автотестирования: test → fix → retest
Максимум 3 итерации пока агент не начнёт СЛЫШАТЬ пользователя
"""
import subprocess
import sys
import json
import os
import time
import logging
from datetime import datetime
from pathlib import Path

# Логирование
LOG_FILE = Path(__file__).parent / "auto_test.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent
MAX_ITERATIONS = 3


def run_python(script, args=None):
    """Запускает Python скрипт и возвращает код выхода"""
    cmd = [
        str(PROJECT_DIR / 'venv' / 'bin' / 'python'),
        str(PROJECT_DIR / script)
    ]
    if args:
        cmd.extend(args)
    
    logger.info(f'▶️ Запускаю: {script} {" ".join(args or [])}')
    result = subprocess.run(cmd, cwd=PROJECT_DIR)
    return result.returncode


def check_vision_token():
    """Проверяет токен перед стартом"""
    from github_vision import validate_token
    return validate_token()


def read_test_report():
    """Читает TEST_REPORT.json"""
    path = PROJECT_DIR / 'TEST_REPORT.json'
    if not path.exists():
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_final_report(all_iterations):
    """Создаёт финальный RESULT.md"""
    md = f"""# 📊 РЕЗУЛЬТАТ АВТОМАТИЧЕСКОГО ТЕСТИРОВАНИЯ
**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Итераций выполнено:** {len(all_iterations)} из {MAX_ITERATIONS}

## 📈 ОБЩАЯ СТАТИСТИКА
| Метрика | Значение |
|---------|----------|
| Итераций | {len(all_iterations)} |
| Vision запросов всего | {sum(it.get('vision_queries_used', 0) for it in all_iterations)} |
| Финальный статус | {all_iterations[-1].get('summary', {}).get('status', 'НЕИЗВЕСТНО') if all_iterations else 'НЕ ЗАПУЩЕНО'} |

## 🔄 ХОД ИТЕРАЦИЙ
"""

    for i, iteration in enumerate(all_iterations, 1):
        summary = iteration.get('summary', {})
        hearing = iteration.get('agent_hearing', {})
        md += f"\n### Итерация #{i}\n"
        md += f"- Тестов: {summary.get('total_tests', 0)}\n"
        md += f"- Пройдено: {summary.get('passed', 0)} ✅\n"
        md += f"- Провалено: {summary.get('failed', 0)} ❌\n"
        md += f"- Vision запросов: {summary.get('vision_queries_used', 0)}\n"
        md += f"- Агент слышит: {summary.get('agent_hears', 0)}/{summary.get('agent_total', 0)}\n"
        
        for scenario, status in hearing.items():
            icon = '✅' if status == 'СЛЫШИТ' else '❌'
            md += f"  - {icon} {scenario}: {status}\n"

        screenshots = iteration.get('screenshots', [])
        if screenshots:
            md += f"- Скриншоты:\n"
            for ss in screenshots[:3]:
                md += f"  - `{ss}`\n"

    md += f"""
## 🔧 ИСПРАВЛЕНИЯ
"""
    
    # Читаем лог fix_agents если есть
    fix_log = PROJECT_DIR / 'fix_agents.log'
    if fix_log.exists():
        content = fix_log.read_text(encoding='utf-8')
        if content.strip():
            for line in content.split('\n'):
                if line.strip():
                    md += f"- {line}\n"
        else:
            md += "- Исправлений не потребовалось\n"
    else:
        md += "- fix_agents.py не запускался\n"

    # Проверяем финальный статус
    if all_iterations:
        final = all_iterations[-1]
        hears_all = all(
            v == 'СЛЫШИТ' 
            for v in final.get('agent_hearing', {}).values()
        )
        if hears_all and final.get('summary', {}).get('failed', 999) == 0:
            md += "\n## ✅ ИТОГ: Всё работает! Агент слышит пользователя! 🎉\n"
        else:
            md += "\n## ⚠️ ИТОГ: Требуется доработка\n"
            hearing = final.get('agent_hearing', {})
            for scenario, status in hearing.items():
                if status != 'СЛЫШИТ':
                    md += f"- ❌ {scenario}: агент НЕ СЛЫШИТ\n"

    result_path = PROJECT_DIR / 'RESULT.md'
    result_path.write_text(md, encoding='utf-8')
    logger.info(f'\n📄 RESULT.md сохранён: {result_path}')
    return result_path


def main():
    logger.info('\n' + '=' * 70)
    logger.info('🚀 АВТОТЕСТИРОВАНИЕ AI TEAM SYSTEM v2.0')
    logger.info('Использую GitHub Models (GPT-4o) для анализа скриншотов')
    logger.info('Лимит: 50 запросов в день')
    logger.info('Максимум итераций: 3')
    logger.info('Слежу за прогрессом: tail -f auto_test.log')
    logger.info('=' * 70)

    # Проверка токена
    logger.info('\n[ШАГ 0] Проверка GitHub Models токена...')
    if not check_vision_token():
        logger.error('❌ GITHUB_TOKEN не валиден! Остановлено.')
        logger.info('Получи токен: github.com/settings/tokens → Generate new token (classic)')
        logger.info('Добавь в .env: GITHUB_TOKEN=ghp_xxxxx')
        sys.exit(1)
    
    logger.info('✅ Токен валиден!')

    all_iterations = []

    for iteration in range(1, MAX_ITERATIONS + 1):
        logger.info(f'\n{"=" * 70}')
        logger.info(f'📋 ИТЕРАЦИЯ #{iteration}')
        logger.info(f'{"=" * 70}')

        # Запуск тестов
        logger.info('\n[ШАГ 1] Запуск auto_tester.py...')
        test_code = run_python('auto_tester.py', [str(iteration)])
        
        if test_code != 0:
            logger.warning(f'⚠️ Тесты не прошли (exit code: {test_code})')
        
        # Читаем отчёт
        report = read_test_report()
        if not report:
            logger.error('❌ Не удалось прочитать TEST_REPORT.json')
            break
        
        all_iterations.append(report)
        
        # Проверяем слышит ли агент
        hearing = report.get('agent_hearing', {})
        all_hear = all(v == 'СЛЫШИТ' for v in hearing.values()) if hearing else False
        
        if all_hear:
            logger.info('\n🎉 Агент СЛЫШИТ пользователя во всех сценариях!')
            break
        
        # Если не последняя итерация — запускаем fix
        if iteration < MAX_ITERATIONS:
            logger.info(f'\n[ШАГ 2] Запуск fix_agents.py (итерация #{iteration})...')
            fix_code = run_python('fix_agents.py', [str(iteration)])
            
            if fix_code == 0:
                logger.info('✅ Исправления применены')
            else:
                logger.warning(f'⚠️ fix_agents.py вернул код {fix_code}')
            
            # Перезапуск сервера для применения изменений
            logger.info('🔄 Перезапуск сервера...')
            subprocess.run(['pkill', '-f', 'uvicorn.*web_ui'], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
        else:
            logger.info(f'\n⚠️ Достигнут максимум итераций ({MAX_ITERATIONS})')

    # Финальный отчёт
    logger.info(f'\n{"=" * 70}')
    logger.info('📝 ФОРМИРОВАНИЕ ОТЧЁТА')
    logger.info(f'{"=" * 70}')
    
    generate_final_report(all_iterations)
    
    # Итог
    if all_iterations:
        final = all_iterations[-1]
        summary = final.get('summary', {})
        logger.info(f'\n📊 ИТОГО:')
        logger.info(f'  Итераций: {len(all_iterations)}')
        logger.info(f'  Vision запросов: {summary.get("vision_queries_used", 0)}')
        logger.info(f'  Статус: {summary.get("status", "НЕИЗВЕСТНО")}')
        logger.info(f'  Отчёт: {PROJECT_DIR / "RESULT.md"}')


if __name__ == '__main__':
    main()
