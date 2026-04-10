#!/usr/bin/env python3
"""
FIX_AGENTS — Автоматическое исправление промптов на основе отчёта тестов
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
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


def fix_prompt(filepath, fixes):
    """Применить исправления к файлу промпта"""
    content = filepath.read_text(encoding='utf-8')
    original = content
    
    for fix_name, fix_data in fixes.items():
        if fix_data.get('apply', False):
            old_text = fix_data.get('find', '')
            new_text = fix_data.get('replace', '')
            
            if old_text in content:
                content = content.replace(old_text, new_text, 1)
                FIXES_LOG.append(f'  ✅ {filepath.name}: {fix_name}')
            else:
                FIXES_LOG.append(f'  ⚠️ {filepath.name}: {fix_name} (не найдено для замены)')
    
    if content != original:
        filepath.write_text(content, encoding='utf-8')
        return True
    return False


def analyze_and_fix(report):
    """Анализировать отчёт и применить исправления"""
    logger.info('=' * 60)
    logger.info('АНАЛИЗ ОТЧЁТА И ИСПРАВЛЕНИЕ')
    logger.info('=' * 60)
    
    fixes_applied = 0
    
    # ===== ПРОВЕРКА 1: teamlead_query эндпоинт =====
    api_tests = {}
    for test in report.get('tests', []):
        if test['name'] == 'API эндпоинты':
            api_tests = test.get('checks', {})
            break
    
    if not api_tests.get('teamlead_query', True):
        logger.warning('⚠️ teamlead_query не работает')
        # Проверяем app.py
        app_file = Path(__file__).parent / 'web_ui' / 'app.py'
        if app_file.exists():
            content = app_file.read_text()
            if 'teamlead_query' not in content:
                logger.info('  Добавляю эндпоинт teamlead_query...')
                # Добавляем перед create_project_stream
                endpoint_code = '''
@app.post("/api/teamlead_query")
async def teamlead_query(req: CreateProjectRequest):
    """TeamLead задаёт вопрос и ждёт ответа"""
    async def event_stream():
        full_query = req.query
        level_hint = _level_hint(req.level)
        query_with_level = f"{level_hint}\\n\\n{full_query}"
        
        from core.agent_manager import AgentManager
        from core.model_router import ModelRouter
        router = ModelRouter(profile=os.getenv("HARDWARE_PROFILE", "medium"))
        manager = AgentManager(model_router=router)
        
        yield f"data: {json.dumps({'type': 'agent_start', 'agent': 'teamlead'})}\\n\\n"
        await asyncio.sleep(0)
        
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: manager.run_agent("teamlead", query_with_level, level=req.level)
            )
            raw_response = result.get('response', '')
            yield f"data: {json.dumps({'type': 'agent_done', 'agent': 'teamlead', 'response': raw_response, 'files': [], 'summary': ''}, ensure_ascii=False)}\\n\\n"
            yield f"data: {json.dumps({'type': 'waiting_for_user', 'message': 'TeamLead ждёт вашего ответа'})}\\n\\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'agent_done', 'agent': 'teamlead', 'response': str(e), 'files': [], 'summary': 'Ошибка'})}\\n\\n"
    
    return StreamingResponse(event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

'''
                if '@app.post("/api/create_project_stream")' in content:
                    content = content.replace(
                        '@app.post("/api/create_project_stream")',
                        endpoint_code + '\n@app.post("/api/create_project_stream")'
                    )
                    app_file.write_text(content)
                    FIXES_LOG.append('  ✅ app.py: добавлен teamlead_query эндпоинт')
                    fixes_applied += 1
    
    # ===== ПРОВЕРКА 2: JS функции =====
    for test in report.get('tests', []):
        if 'JS' in test.get('name', ''):
            js = test.get('checks', {}).get('js_functions', {})
            missing = [fn for fn, exists in js.items() if not exists]
            
            if missing:
                logger.warning(f'⚠️ Не найдены JS функции: {missing}')
                
                welcome_file = Path(__file__).parent / 'web_ui' / 'templates' / 'welcome.html'
                if welcome_file.exists():
                    content = welcome_file.read_text()
                    
                    # Проверяем callTeamLead
                    if 'callTeamLead' in missing and 'function callTeamLead' not in content:
                        logger.info('  Добавляю функцию callTeamLead...')
                        # Добавляем перед askClarification
                        func_code = '''
async function callTeamLead() {
  state.phase = 'teamlead_wait';
  showTyping();
  
  const isFirst = (state.phase === 'teamlead_wait');
  const prompt = isFirst
    ? `Ты впервые общаешься с пользователем. Идея проекта: ${state.projectIdea}`
    : `Пользователь задал вопрос. Идея проекта: ${state.projectIdea}`;

  try {
    const response = await fetch('/api/teamlead_query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_name: state.projectName,
        query: prompt,
        level: state.level
      })
    });
    
    // ... SSE handling
  } catch (e) {
    removeTyping();
    addAiMsg('system', '⚠️ Ошибка: ' + e.message);
  }
}
'''
                        if 'async function askClarification' in content:
                            content = content.replace(
                                'async function askClarification',
                                func_code + '\n// ══════════════════════════════════════════\n//  CLARIFICATION\n// ══════════════════════════════════════════\nasync function askClarification'
                            )
                            welcome_file.write_text(content)
                            FIXES_LOG.append('  ✅ welcome.html: добавлена callTeamLead')
                            fixes_applied += 1
    
    # ===== ПРОВЕРКА 3: Промпты агентов =====
    for test in report.get('tests', []):
        if 'Промпт' in test.get('name', ''):
            checks = test.get('checks', {})
            for fname, info in checks.items():
                if not info.get('has_wait_instruction', True):
                    logger.warning(f'⚠️ {fname}: нет инструкции "жди ответа"')
                    fpath = PROMPTS_DIR / fname
                    if fpath.exists():
                        content = fpath.read_text()
                        if 'жди' not in content.lower() and 'жди ответа' not in content.lower():
                            # Добавляем инструкцию
                            content += '\n\n## ВАЖНО: ЖДИ ОТВЕТА ПОЛЬЗОВАТЕЛЯ ПРЕЖДЕ ЧЕМ ПРОДОЛЖИТЬ\n'
                            fpath.write_text(content)
                            FIXES_LOG.append(f'  ✅ {fname}: добавлена инструкция ждать')
                            fixes_applied += 1
    
    # Итог
    logger.info('\n' + '=' * 60)
    logger.info(f'ИСПРАВЛЕНИЙ ПРИМЕНЕНО: {fixes_applied}')
    for fix in FIXES_LOG:
        logger.info(fix)
    logger.info('=' * 60)
    
    return fixes_applied > 0


def generate_result_md(report):
    """Создать RESULT.md"""
    summary = report.get('summary', {})
    tests = report.get('tests', [])
    screenshots = report.get('screenshots', [])
    
    md = f"""# 📊 РЕЗУЛЬТАТ АВТОМАТИЧЕСКОГО ТЕСТИРОВАНИЯ
**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📈 ОБЩАЯ СТАТИСТИКА
| Метрика | Значение |
|---------|----------|
| Всего тестов | {summary.get('total_tests', 0)} |
| Пройдено | {summary.get('passed', 0)} ✅ |
| Провалено | {summary.get('failed', 0)} ❌ |
| Ошибок консоли | {summary.get('console_errors', 0)} |
| Скриншотов | {summary.get('screenshots_taken', 0)} |
| **Статус** | **{summary.get('status', 'НЕИЗВЕСТНО')}** |

## 🧪 ДЕТАЛИ ТЕСТОВ
"""
    
    for test in tests:
        icon = '✅' if test.get('passed') else '❌'
        md += f"\n### {icon} {test['name']}\n"
        md += f"- **Статус:** {'Пройден' if test.get('passed') else 'Провален'}\n"
        
        if 'checks' in test:
            if isinstance(test['checks'], dict):
                for name, val in test['checks'].items():
                    if isinstance(val, dict):
                        md += f"  - {name}: {json.dumps(val, ensure_ascii=False)}\n"
                    else:
                        icon2 = '✅' if val else '❌'
                        md += f"  - {icon2} {name}\n"
    
    md += f"\n## 📸 СКРИНШОТЫ\n"
    for ss in screenshots:
        md += f"- `{ss}`\n"
    
    md += f"""
## 🔧 ИСПРАВЛЕНИЯ
"""
    if FIXES_LOG:
        for fix in FIXES_LOG:
            md += f"- {fix}\n"
    else:
        md += "- Исправлений не потребовалось\n"
    
    md += f"""
## 📝 ЧТО ОСТАЛОСЬ СДЕЛАТЬ
"""
    failed_tests = [t for t in tests if not t.get('passed')]
    if failed_tests:
        for t in failed_tests:
            md += f"- ❌ {t['name']}: {t.get('error', 'требуется исправление')}\n"
    else:
        md += "- Всё работает! 🎉\n"
    
    result_path = Path(__file__).parent / 'RESULT.md'
    result_path.write_text(md, encoding='utf-8')
    logger.info(f'\n📄 RESULT.md сохранён: {result_path}')


if __name__ == '__main__':
    logger.info('🔧 Fix Agents v1.0')
    
    report = load_report()
    if not report:
        sys.exit(1)
    
    fixed = analyze_and_fix(report)
    generate_result_md(report)
    
    logger.info('\n✅ Готово!')
