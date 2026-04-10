#!/usr/bin/env python3
"""
AUTO_TESTER v2.0 — Автоматическое тестирование AI Team System
Использует Playwright для браузера + GitHub Models GPT-4o для vision анализа
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
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)
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
    'iteration': 1,
    'tests': [],
    'vision_analyses': [],
    'screenshots': [],
    'console_errors': [],
    'page_errors': [],
    'agent_hearing': {},
    'summary': {}
}

BASE_URL = 'http://localhost:8000'
VISION_QUERIES_USED = 0


def ensure_server_running():
    """Проверяет что сервер работает, запускает если нет"""
    import requests
    try:
        r = requests.get(f'{BASE_URL}/api/health', timeout=5)
        if r.status_code == 200:
            logger.info('✅ Сервер уже запущен')
            return True
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
    
    # Ждём пока поднимется
    for i in range(20):
        time.sleep(1)
        try:
            r = requests.get(f'{BASE_URL}/api/health', timeout=5)
            if r.status_code == 200:
                logger.info(f'✅ Сервер запущен (попытка {i+1})')
                return True
        except:
            continue
    
    logger.error('❌ Не удалось запустить сервер за 20 секунд')
    return False


def vision_screenshot(image_path, question):
    """Делает анализ скриншота через GitHub Models Vision"""
    global VISION_QUERIES_USED
    
    try:
        from github_vision import analyze_screenshot
        result = analyze_screenshot(image_path, question)
        VISION_QUERIES_USED += 1
        
        if result:
            logger.info(f'👁️ Vision анализ ({Path(image_path).name}):')
            for line in result.split('\n')[:5]:
                logger.info(f'   {line[:120]}')
        else:
            result = "⚠️ Ошибка анализа (лимит или токен)"
            logger.warning(f'⚠️ Vision анализ не удался для {image_path}')
        
        REPORT['vision_analyses'].append({
            'screenshot': str(image_path),
            'question': question,
            'answer': result,
            'vision_queries_used': VISION_QUERIES_USED
        })
        return result
    except ImportError:
        logger.warning('⚠️ github_vision.py не найден — пропускаю vision анализ')
        return "⚠️ Vision не доступен"
    except Exception as e:
        logger.error(f'❌ Ошибка vision: {e}')
        return f"❌ Ошибка: {e}"


def check_agent_hearing_via_vision(image_path, user_message):
    """Проверяет слышит ли агент пользователя"""
    question = (
        f"Пользователь написал в чат: '{user_message}'. "
        f"Посмотри на ответ AI-агента на скриншоте. "
        f"Агент ответил КОНКРЕТНО по теме '{user_message}' или это общий скрипт? "
        f"Ответь строго: СЛЫШИТ или НЕ СЛЫШИТ. Потом кратко объясни почему."
    )
    
    result = vision_screenshot(image_path, question)
    
    # Извлекаем ключевое слово
    if result and "СЛЫШИТ" in result.upper() and "НЕ СЛЫШИТ" not in result.upper():
        return "СЛЫШИТ"
    elif result and "НЕ СЛЫШИТ" in result.upper():
        return "НЕ СЛЫШИТ"
    elif result and "всё чисто" in result.lower():
        return "OK"
    return "НЕ СЛЫШИТ"


async def run_tests(iteration=1):
    """Запуск всех тестов"""
    from playwright.async_api import async_playwright

    global VISION_QUERIES_USED
    VISION_QUERIES_USED = 0
    
    logger.info('\n' + '=' * 60)
    logger.info(f'НАЧИНАЮ ТЕСТИРОВАНИЕ — Итерация #{iteration}')
    logger.info('=' * 60)

    REPORT['iteration'] = iteration
    REPORT['vision_analyses'] = []
    REPORT['agent_hearing'] = {}

    if not ensure_server_running():
        return None

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

        # ===== ТЕСТ 1: Главная страница + Vision =====
        logger.info('\n[ТЕСТ 1] Главная страница')
        await page.goto(BASE_URL, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)

        screenshot1 = str(SCREENSHOTS_DIR / f'01_start_{int(time.time())}.png')
        await page.screenshot(path=screenshot1, full_page=True)
        REPORT['screenshots'].append(screenshot1)

        # Vision анализ главной
        vision_main = vision_screenshot(
            screenshot1,
            "Это интерфейс AI Team System. Опиши что видишь. "
            "Есть ли ошибки или сломанные элементы UI? Всё ли отображается корректно?"
        )
        
        title = await page.title()
        checks = {
            'has_title': await page.locator('h1, h2, h3').first.count() > 0,
            'has_chat_area': await page.locator('#chat-area, .chat-area, [class*="chat"], [class*="message"]').first.count() > 0,
            'has_input': await page.locator('textarea, input[type="text"]').first.count() > 0,
            'has_send_button': await page.locator('button[type="submit"], button[class*="send"], button[id*="send"]').first.count() > 0,
        }

        test1_result = {
            'name': 'Главная страница',
            'passed': all(checks.values()),
            'checks': checks,
            'vision_analysis': vision_main,
            'screenshot': screenshot1
        }
        REPORT['tests'].append(test1_result)

        for name, passed in checks.items():
            icon = '✅' if passed else '❌'
            logger.info(f'  {icon} {name}: {passed}')

        # ===== ТЕСТ 2: Отправка "Калькулятор" + Vision =====
        logger.info('\n[ТЕСТ 2] Отправка: Калькулятор')
        
        # Закрываем welcome overlay если он есть
        try:
            overlay = page.locator('#welcome-overlay')
            if await overlay.count() > 0 and await overlay.is_visible():
                logger.info('  Закрываю welcome overlay...')
                # Нажимаем кнопку "Сразу создать проект" чтобы перейти в фазу idea
                skip_btn = page.locator('button.btn-ghost').first
                if await skip_btn.count() > 0:
                    await skip_btn.click()
                    await page.wait_for_timeout(2000)
                    logger.info('  ✅ Нажал "Сразу создать проект"')
                else:
                    # Фоллбэк — Escape
                    await page.keyboard.press('Escape')
                    await page.wait_for_timeout(1000)
                    await page.evaluate("""() => {
                        const o = document.getElementById('welcome-overlay');
                        if (o) { o.style.display = 'none'; o.style.opacity = '0'; }
                        state.phase = 'idea';
                    }""")
                    await page.wait_for_timeout(500)
                logger.info('  ✅ Overlay закрыт')
        except Exception as e:
            logger.warning(f'  ⚠️ Не удалось закрыть overlay: {e}')
        
        input_el = page.locator('textarea, input[type="text"]').first
        try:
            # Ждём что input будет доступен (overlay закрыт)
            await input_el.wait_for(state='visible', timeout=10000)
            await input_el.click()
            await input_el.fill('Калькулятор')
            await page.wait_for_timeout(1000)
        except Exception as e:
            logger.warning(f'  ⚠️ Не удалось ввести текст: {e}')

        # Нажать Enter или кнопку
        try:
            await input_el.press('Enter')
            await page.wait_for_timeout(1500)
        except:
            pass

        # Ждём ответа
        await page.wait_for_timeout(8000)

        screenshot2 = str(SCREENSHOTS_DIR / f'02_calculator_{int(time.time())}.png')
        await page.screenshot(path=screenshot2, full_page=True)
        REPORT['screenshots'].append(screenshot2)

        # Проверяет ли агент СЛЫШИТ
        hearing_calc = check_agent_hearing_via_vision(screenshot2, "Калькулятор")
        REPORT['agent_hearing']['calculator'] = hearing_calc
        logger.info(f'  🎯 Калькулятор: {hearing_calc}')

        test2_result = {
            'name': 'Отправка: Калькулятор',
            'passed': hearing_calc == 'СЛЫШИТ',
            'agent_hearing': hearing_calc,
            'screenshot': screenshot2
        }
        REPORT['tests'].append(test2_result)

        # ===== ТЕСТ 3: Отправка "тренажёр печати" + Vision =====
        logger.info('\n[ТЕСТ 3] Отправка: тренажёр печати')
        
        # Убеждаемся что overlay закрыт
        try:
            await page.evaluate("""() => {
                const o = document.getElementById('welcome-overlay');
                if (o) { o.style.display = 'none'; }
            }""")
        except:
            pass
        
        try:
            await input_el.click(timeout=10000)
            await input_el.fill('тренажёр печати')
            await page.wait_for_timeout(1000)
            await input_el.press('Enter')
            await page.wait_for_timeout(1500)
        except Exception as e:
            logger.warning(f'  ⚠️ Не удалось ввести текст: {e}')

        await page.wait_for_timeout(8000)

        screenshot3 = str(SCREENSHOTS_DIR / f'03_typing_{int(time.time())}.png')
        await page.screenshot(path=screenshot3, full_page=True)
        REPORT['screenshots'].append(screenshot3)

        hearing_type = check_agent_hearing_via_vision(screenshot3, "тренажёр печати")
        REPORT['agent_hearing']['typing_trainer'] = hearing_type
        logger.info(f'  🎯 Тренажёр печати: {hearing_type}')

        test3_result = {
            'name': 'Отправка: тренажёр печати',
            'passed': hearing_type == 'СЛЫШИТ',
            'agent_hearing': hearing_type,
            'screenshot': screenshot3
        }
        REPORT['tests'].append(test3_result)

        # ===== ТЕСТ 4: JS функции =====
        logger.info('\n[ТЕСТ 4] JS функции')
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
            logger.info(f'  JS: {json.dumps(js_check, ensure_ascii=False)}')
            
            test4_result = {
                'name': 'JS функции',
                'passed': all(js_check.values()),
                'checks': js_check
            }
        except Exception as e:
            logger.warning(f'  ⚠️ JS проверка: {e}')
            test4_result = {
                'name': 'JS функции',
                'passed': False,
                'error': str(e)
            }
        REPORT['tests'].append(test4_result)

        # ===== ТЕСТ 5: API эндпоинты =====
        logger.info('\n[ТЕСТ 5] API эндпоинты')
        import requests

        api_tests = {}
        endpoints = ['/api/health', '/api/hardware']
        for ep in endpoints:
            try:
                r = requests.get(f'{BASE_URL}{ep}', timeout=5)
                api_tests[ep] = r.status_code == 200
            except:
                api_tests[ep] = False

        test5_result = {
            'name': 'API эндпоинты',
            'passed': all(api_tests.values()),
            'checks': api_tests
        }
        REPORT['tests'].append(test5_result)

        for ep, passed in api_tests.items():
            icon = '✅' if passed else '❌'
            logger.info(f'  {icon} {ep}: {passed}')

        # ===== ТЕСТ 6: Промпты агентов =====
        logger.info('\n[ТЕСТ 6] Промпты агентов')
        prompts_dir = Path(__file__).parent / 'prompts' / 'roles'
        prompt_files = list(prompts_dir.glob('*_zero.md')) if prompts_dir.exists() else []

        prompt_checks = {}
        for pf in prompt_files:
            content = pf.read_text()
            has_tool = '{"tool"' in content or 'tool_call' in content
            has_wait = 'жди' in content.lower() or 'ждёт' in content.lower()
            prompt_checks[pf.name] = {
                'exists': True,
                'has_tool_call_forbidden': not has_tool,
                'has_wait_instruction': has_wait
            }

        test6_result = {
            'name': 'Промпты агентов',
            'passed': len(prompt_files) >= 7,
            'files_found': len(prompt_files),
            'checks': prompt_checks
        }
        REPORT['tests'].append(test6_result)
        logger.info(f'  {"✅" if len(prompt_files) >= 7 else "❌"} Промптов: {len(prompt_files)}')

        # ===== Финальный скриншот =====
        screenshot_final = str(SCREENSHOTS_DIR / f'99_final_{int(time.time())}.png')
        await page.screenshot(path=screenshot_final, full_page=True)
        REPORT['screenshots'].append(screenshot_final)

        REPORT['console_errors'] = errors[:20]
        await browser.close()

    # ===== ИТОГОВАЯ СВОДКА =====
    total = len(REPORT['tests'])
    passed = sum(1 for t in REPORT['tests'] if t.get('passed'))
    failed = total - passed
    
    hearing_results = REPORT.get('agent_hearing', {})
    hears_count = sum(1 for v in hearing_results.values() if v == 'СЛЫШИТ')

    REPORT['summary'] = {
        'total_tests': total,
        'passed': passed,
        'failed': failed,
        'console_errors': len(errors),
        'screenshots_taken': len(REPORT['screenshots']),
        'vision_queries_used': VISION_QUERIES_USED,
        'agent_hears': hears_count,
        'agent_total': len(hearing_results),
        'status': '✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ' if failed == 0 else f'❌ ЕСТЬ ПРОБЛЕМЫ ({failed} из {total})'
    }

    logger.info('\n' + '=' * 60)
    logger.info('ИТОГО:')
    logger.info(f'  Тестов: {total}')
    logger.info(f'  Пройдено: {passed} ✅')
    logger.info(f'  Провалено: {failed} ❌')
    logger.info(f'  Vision запросов: {VISION_QUERIES_USED}')
    logger.info(f'  Агент слышит: {hears_count}/{len(hearing_results)}')
    logger.info(f'  Статус: {REPORT["summary"]["status"]}')
    logger.info('=' * 60)

    return REPORT


def save_report():
    """Сохранить отчёт"""
    report_path = Path(__file__).parent / 'TEST_REPORT.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(REPORT, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f'\n📄 Отчёт сохранён: {report_path}')
    return report_path


if __name__ == '__main__':
    logger.info('🚀 Auto Tester v2.0 с GitHub Models Vision')
    logger.info(f'📅 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    logger.info(f'🌐 {BASE_URL}')
    
    # Проверка токена
    try:
        from github_vision import validate_token
        if not validate_token():
            logger.error('❌ Остановлено — нет валидного GITHUB_TOKEN')
            sys.exit(1)
    except ImportError:
        logger.warning('⚠️ github_vision.py не найден — vision анализ отключён')

    iteration = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    result = asyncio.run(run_tests(iteration))
    save_report()

    if result:
        failed = result['summary'].get('failed', 999)
        sys.exit(1 if failed > 0 else 0)
    else:
        sys.exit(1)
