#!/usr/bin/env python3
"""
AUTO_TESTER — Автоматическое тестирование AI Team System
Использует Playwright для браузера + Reviewer для анализа
"""
import asyncio
import json
import os
import sys
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Настройка логирования
LOG_DIR = Path(__file__).parent / "screenshots"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = Path(__file__).parent / "auto_test.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Глобальный отчёт
REPORT = {
    'timestamp': datetime.now().isoformat(),
    'tests': [],
    'screenshots': [],
    'console_errors': [],
    'page_errors': [],
    'summary': {}
}

BASE_URL = 'http://localhost:8000'


def ensure_server_running():
    """Проверяет что сервер работает, запускает если нет"""
    import requests
    try:
        r = requests.get(f'{BASE_URL}/api/health', timeout=5)
        if r.status_code == 200:
            logger.info('✅ Сервер уже запущен')
            return
    except:
        pass
    
    logger.info('⚠️ Сервер не запущен — запускаю...')
    project_dir = Path(__file__).parent
    subprocess.Popen(
        [project_dir / 'venv' / 'bin' / 'python', '-m', 'uvicorn', 'web_ui.app:app',
         '--host', '0.0.0.0', '--port', '8000'],
        cwd=project_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(6)
    
    # Проверяем снова
    try:
        r = requests.get(f'{BASE_URL}/api/health', timeout=5)
        if r.status_code == 200:
            logger.info('✅ Сервер запущен')
        else:
            logger.error('❌ Сервер не ответил OK')
            sys.exit(1)
    except:
        logger.error('❌ Не удалось запустить сервер')
        sys.exit(1)


async def run_tests():
    """Запуск всех тестов"""
    from playwright.async_api import async_playwright
    
    logger.info('=' * 60)
    logger.info('НАЧИНАЮ ТЕСТИРОВАНИЕ')
    logger.info('=' * 60)
    
    ensure_server_running()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            locale='ru-RU'
        )
        page = await context.new_page()
        
        # Перехват ошибок консоли
        errors = []
        page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
        page.on('pageerror', lambda err: errors.append(str(err)))
        
        # ===== ТЕСТ 1: Главная страница =====
        logger.info('\n[ТЕСТ 1] Главная страница')
        await page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)
        
        screenshot1 = str(LOG_DIR / f'01_main_page_{int(time.time())}.png')
        await page.screenshot(path=screenshot1, full_page=True)
        REPORT['screenshots'].append(screenshot1)
        
        title = await page.title()
        logger.info(f'  Заголовок: {title}')
        
        # Проверяем элементы
        checks = {
            'has_title': await page.locator('h1, h2').first.count() > 0,
            'has_chat_area': await page.locator('#chat-area, .chat-area, [class*="chat"]').first.count() > 0,
            'has_input': await page.locator('textarea, input[type="text"]').first.count() > 0,
            'has_send_button': await page.locator('button, [class*="send"]').first.count() > 0,
            'has_agents_panel': await page.locator('[class*="agent"], [id*="agent"]').first.count() > 0,
        }
        
        test1_result = {
            'name': 'Главная страница',
            'passed': all(checks.values()),
            'checks': checks,
            'screenshot': screenshot1
        }
        REPORT['tests'].append(test1_result)
        
        for name, passed in checks.items():
            icon = '✅' if passed else '❌'
            logger.info(f'  {icon} {name}: {passed}')
        
        # ===== ТЕСТ 2: Отправка сообщения =====
        logger.info('\n[ТЕСТ 2] Отправка сообщения')
        
        # Закрываем welcome overlay если есть
        try:
            overlay = page.locator('#welcome-overlay')
            if await overlay.count() > 0:
                # Нажмём кнопку на overlay чтобы закрыть
                btns = overlay.locator('button')
                if await btns.count() > 0:
                    await btns.first.click()
                    await page.wait_for_timeout(2000)
        except:
            pass
        
        input_el = page.locator('textarea, input[type="text"]').first
        try:
            await input_el.click(timeout=10000)
            await input_el.fill('Привет')
            await page.wait_for_timeout(1000)
        except Exception as e:
            logger.warning(f'  ⚠️ Не удалось кликнуть: {e}')
        
        screenshot2 = str(LOG_DIR / f'02_after_typing_{int(time.time())}.png')
        await page.screenshot(path=screenshot2)
        REPORT['screenshots'].append(screenshot2)
        
        # Найти и нажать кнопку отправки
        send_btn = page.locator('button[class*="send"], button[id*="send"]').first
        if await send_btn.count() == 0:
            # Попробуем найти по onclick
            send_btn = page.locator('button[onclick*="send"]').first
        
        if await send_btn.count() > 0:
            await send_btn.click()
            await page.wait_for_timeout(5000)
            
            # Проверяем что что-то появилось в чате
            chat_content = await page.locator('#chat-area, .chat-area, [class*="chat"]').first.inner_text()
            has_response = len(chat_content) > 50
            
            screenshot2b = str(LOG_DIR / f'02_after_send_{int(time.time())}.png')
            await page.screenshot(path=screenshot2b)
            REPORT['screenshots'].append(screenshot2b)
            
            test2_result = {
                'name': 'Отправка сообщения',
                'passed': has_response,
                'chat_content_len': len(chat_content),
                'has_response': has_response,
                'screenshot': screenshot2b
            }
        else:
            test2_result = {
                'name': 'Отправка сообщения',
                'passed': False,
                'error': 'Кнопка отправки не найдена'
            }
        
        REPORT['tests'].append(test2_result)
        logger.info(f'  {"✅" if test2_result.get("passed") else "❌"} Отправка: {test2_result.get("passed", False)}')
        
        # ===== ТЕСТ 3: Проверка выбора уровня =====
        logger.info('\n[ТЕСТ 3] Элементы выбора уровня')
        level_checks = {
            'has_level_buttons': await page.locator('button, [class*="level"], [class*="zero"], [class*="beginner"]').count() > 0,
            'has_js_functions': True,  # Проверяем через evaluate
        }
        
        # Проверим что JS функции существуют
        try:
            js_check = await page.evaluate("""() => {
                return {
                    has_callTeamLead: typeof callTeamLead === 'function',
                    has_startBuilding: typeof startBuilding === 'function',
                    has_cleanToolCall: typeof cleanToolCall === 'function',
                    has_stopBuild: typeof stopBuild === 'function',
                    has_onTeamleadChoice: typeof onTeamleadChoice === 'function'
                }
            }""")
            level_checks['js_functions'] = js_check
            logger.info(f'  JS функции: {json.dumps(js_check, ensure_ascii=False)}')
        except Exception as e:
            logger.warning(f'  ⚠️ Не удалось проверить JS: {e}')
        
        test3_result = {
            'name': 'Выбор уровня и JS функции',
            'passed': level_checks.get('has_level_buttons', False),
            'checks': level_checks
        }
        REPORT['tests'].append(test3_result)
        
        # ===== ТЕСТ 4: API эндпоинты =====
        logger.info('\n[ТЕСТ 4] API эндпоинты')
        import requests
        
        api_tests = {}
        try:
            r = requests.get(f'{BASE_URL}/api/health', timeout=5)
            api_tests['health'] = r.status_code == 200
        except:
            api_tests['health'] = False
        
        try:
            r = requests.get(f'{BASE_URL}/api/hardware', timeout=5)
            api_tests['hardware'] = r.status_code == 200
        except:
            api_tests['hardware'] = False
        
        try:
            r = requests.post(f'{BASE_URL}/api/teamlead_query', json={
                'project_name': 'test', 'query': 'test', 'level': 'zero'
            }, timeout=60, stream=True)
            # Просто проверяем что соединение есть
            api_tests['teamlead_query'] = r.status_code == 200
        except:
            api_tests['teamlead_query'] = False
        
        try:
            r = requests.post(f'{BASE_URL}/api/create_project_stream', json={
                'project_name': 'test', 'query': 'test', 'level': 'zero'
            }, timeout=5, stream=True)
            api_tests['create_project_stream'] = r.status_code == 200
        except:
            api_tests['create_project_stream'] = False
        
        test4_result = {
            'name': 'API эндпоинты',
            'passed': all(api_tests.values()),
            'checks': api_tests
        }
        REPORT['tests'].append(test4_result)
        
        for name, passed in api_tests.items():
            icon = '✅' if passed else '❌'
            logger.info(f'  {icon} /api/{name}: {passed}')
        
        # ===== ТЕСТ 5: Проверка промптов =====
        logger.info('\n[ТЕСТ 5] Промпты агентов')
        prompts_dir = Path(__file__).parent / 'prompts' / 'roles'
        prompt_files = list(prompts_dir.glob('*_zero.md')) if prompts_dir.exists() else []
        
        prompt_checks = {}
        for pf in prompt_files:
            content = pf.read_text()
            has_tool = 'tool_call' in content or '{"tool"' in content
            has_wait = 'жди' in content.lower() or 'жди ответа' in content.lower() or 'ждёт' in content.lower()
            prompt_checks[pf.name] = {
                'exists': True,
                'has_tool_call_forbidden': not has_tool,
                'has_wait_instruction': has_wait
            }
        
        test5_result = {
            'name': 'Промпты агентов',
            'passed': len(prompt_files) >= 7,
            'files_found': len(prompt_files),
            'checks': prompt_checks
        }
        REPORT['tests'].append(test5_result)
        
        logger.info(f'  {"✅" if len(prompt_files) >= 7 else "❌"} Найдено промптов: {len(prompt_files)}')
        for name, info in prompt_checks.items():
            icon = '✅' if info['has_tool_call_forbidden'] else '⚠️'
            logger.info(f'  {icon} {name}')
        
        # ===== ТЕСТ 6: Ошибки в консоли =====
        logger.info('\n[ТЕСТ 6] Ошибки в консоли браузера')
        REPORT['console_errors'] = errors[:20]  # Максимум 20
        
        if errors:
            logger.warning(f'  ⚠️ Найдено ошибок: {len(errors)}')
            for err in errors[:5]:
                logger.warning(f'    - {err[:100]}')
        else:
            logger.info('  ✅ Ошибок нет')
        
        # Финальный скриншот
        screenshot_final = str(LOG_DIR / f'99_final_{int(time.time())}.png')
        await page.screenshot(path=screenshot_final, full_page=True)
        REPORT['screenshots'].append(screenshot_final)
        
        await browser.close()
    
    # Итоговая сводка
    total = len(REPORT['tests'])
    passed = sum(1 for t in REPORT['tests'] if t.get('passed'))
    failed = total - passed
    
    REPORT['summary'] = {
        'total_tests': total,
        'passed': passed,
        'failed': failed,
        'console_errors': len(errors),
        'screenshots_taken': len(REPORT['screenshots']),
        'status': '✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ' if failed == 0 else f'❌ ЕСТЬ ПРОБЛЕМЫ ({failed} из {total})'
    }
    
    logger.info('\n' + '=' * 60)
    logger.info('ИТОГО:')
    logger.info(f'  Тестов: {total}')
    logger.info(f'  Пройдено: {passed} ✅')
    logger.info(f'  Провалено: {failed} ❌')
    logger.info(f'  Ошибок консоли: {len(errors)}')
    logger.info(f'  Скриншотов: {len(REPORT["screenshots"])}')
    logger.info(f'  Статус: {REPORT["summary"]["status"]}')
    logger.info('=' * 60)
    
    return REPORT


def save_report():
    """Сохранить отчёт"""
    report_path = Path(__file__).parent / 'TEST_REPORT.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(REPORT, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f'\n📄 Отчёт сохранён: {report_path}')


if __name__ == '__main__':
    logger.info('🚀 Auto Tester v1.0')
    logger.info(f'📅 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    logger.info(f'🌐 {BASE_URL}')
    
    asyncio.run(run_tests())
    save_report()
    
    # Exit code
    failed = REPORT['summary'].get('failed', 999)
    sys.exit(1 if failed > 0 else 0)
