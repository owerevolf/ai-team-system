"""
Real-World Repository Testing (P19) — Phase 8

Test scenarios and fixtures for testing the system against
real-world repository patterns: broken repos, abandoned projects,
startup codebases, legacy apps, chaotic architectures.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class TestScenario:
    """A test scenario for real-world repository testing."""
    scenario_id: str
    name: str
    description: str
    category: str              # broken | legacy | startup | chaotic | abandoned
    setup_files: dict[str, str] = field(default_factory=dict)  # filename -> content
    expected_issues: list[str] = field(default_factory=list)
    difficulty: str = "medium"  # easy | medium | hard

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "file_count": len(self.setup_files),
            "expected_issues": self.expected_issues,
            "difficulty": self.difficulty,
        }


# ---------------------------------------------------------------------------
# Built-in test scenarios
# ---------------------------------------------------------------------------

BUILTIN_SCENARIOS: dict[str, TestScenario] = {
    "broken-imports": TestScenario(
        scenario_id="broken-imports",
        name="Broken Imports",
        description="A project with multiple broken import statements",
        category="broken",
        expected_issues=["broken_imports"],
        difficulty="easy",
        setup_files={
            "main.py": "import os\nimport nonexistent_lib\nfrom missing_module import something\n\ndef main():\n    pass\n",
            "app.py": "from utils import helper\nimport another_missing\n",
            "utils.py": "def helper():\n    return True\n",
        },
    ),
    "circular-deps": TestScenario(
        scenario_id="circular-deps",
        name="Circular Dependencies",
        description="A project with circular import dependencies",
        category="broken",
        expected_issues=["circular_dependencies"],
        difficulty="medium",
        setup_files={
            "models.py": "from views import render\n\ndef get_data():\n    return render()\n",
            "views.py": "from models import get_data\n\ndef render():\n    return get_data()\n",
            "main.py": "from models import get_data\nfrom views import render\n",
        },
    ),
    "legacy-python2": TestScenario(
        scenario_id="legacy-python2",
        name="Legacy Python 2 Code",
        description="A project with Python 2 patterns that need updating",
        category="legacy",
        expected_issues=["deprecated_patterns"],
        difficulty="medium",
        setup_files={
            "main.py": "print 'Hello World'\nx = xrange(10)\nname = unicode('test')\nif d.has_key('key'):\n    pass\n",
            "utils.py": "def process(items):\n    for k, v in items.iteritems():\n        print k, v\n",
        },
    ),
    "missing-deps": TestScenario(
        scenario_id="missing-deps",
        name="Missing Dependencies",
        description="A project with requirements.txt referencing unavailable packages",
        category="broken",
        expected_issues=["missing_dependencies"],
        difficulty="easy",
        setup_files={
            "main.py": "import requests\nimport flask\nimport nonexistent_package_xyz\n",
            "requirements.txt": "requests>=2.28\nflask>=2.0\nnonexistent-package-xyz>=1.0\nanother-missing-pkg>=2.0\n",
        },
    ),
    "chaotic-structure": TestScenario(
        scenario_id="chaotic-structure",
        name="Chaotic Project Structure",
        description="A project with no clear structure, mixed concerns, and scattered files",
        category="chaotic",
        expected_issues=["high_complexity", "no_tests"],
        difficulty="hard",
        setup_files={
            "main.py": "import os, sys, json, re\n\ndef everything():\n    # This function does everything\n    data = json.loads('{}')\n    files = os.listdir('.')\n    for f in files:\n        if re.match(r'.*\\.py$', f):\n            exec(open(f).read())\n    return data\n",
            "helper.py": "from main import everything\n\ndef helper():\n    return everything()\n",
            "utils.py": "from helper import helper\nfrom main import everything\n\ndef util():\n    return helper() + everything()\n",
            "config.py": "DB_HOST = 'localhost'\nDB_PORT = 5432\nSECRET_KEY = 'hardcoded-secret'\nAPI_KEY = 'sk-12345'\n",
            "test.py": "# TODO: write tests\n",
        },
    ),
    "startup-mvp": TestScenario(
        scenario_id="startup-mvp",
        name="Startup MVP Codebase",
        description="A typical startup MVP: working but messy, with tech debt",
        category="startup",
        expected_issues=["deprecated_patterns", "missing_tests"],
        difficulty="medium",
        setup_files={
            "app.py": "from flask import Flask\nimport requests\nimport json\n\napp = Flask(__name__)\n\n@app.route('/')\ndef index():\n    return 'Hello'\n\n@app.route('/api/data')\ndef get_data():\n    r = requests.get('https://api.example.com/data')\n    return json.dumps(r.json())\n",
            "models.py": "import sqlite3\n\ndef get_db():\n    return sqlite3.connect('data.db')\n\ndef query(sql):\n    db = get_db()\n    return db.execute(sql).fetchall()\n",
            "requirements.txt": "flask>=2.0\nrequests>=2.28\n",
            "README.md": "# Startup MVP\n\nThis is our MVP. It works but needs cleanup.\n",
        },
    ),
    "abandoned-project": TestScenario(
        scenario_id="abandoned-project",
        name="Abandoned Project",
        description="An old project with outdated dependencies and no maintenance",
        category="abandoned",
        expected_issues=["deprecated_patterns", "missing_dependencies"],
        difficulty="hard",
        setup_files={
            "main.py": "import urllib2\nimport SimpleHTTPServer\nimport cPickle\n\ndef fetch(url):\n    return urllib2.urlopen(url).read()\n",
            "requirements.txt": "Django==1.11.29\ncelery==3.1.25\nredis==2.10.6\n",
            "setup.py": "from distutils.core import setup\nsetup(name='old-project', version='0.1')\n",
            ".python-version": "2.7.18\n",
        },
    ),
}


class RealWorldTestRunner:
    """
    Runs test scenarios against workspace modules.

    Usage:
        runner = RealWorldTestRunner()
        result = runner.run_scenario("broken-imports")
        report = runner.generate_report()
    """

    def __init__(self) -> None:
        self._scenarios: dict[str, TestScenario] = dict(BUILTIN_SCENARIOS)
        self._results: list[dict[str, Any]] = []

    def get_scenario(self, scenario_id: str) -> Optional[TestScenario]:
        """Get a test scenario by ID."""
        return self._scenarios.get(scenario_id)

    def list_scenarios(
        self, category: Optional[str] = None, difficulty: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """List available test scenarios."""
        results = list(self._scenarios.values())
        if category:
            results = [s for s in results if s.category == category]
        if difficulty:
            results = [s for s in results if s.difficulty == difficulty]
        return [s.to_dict() for s in results]

    def setup_scenario(self, scenario_id: str, target_dir: Optional[str] = None) -> str:
        """
        Set up a test scenario in a directory.

        Args:
            scenario_id: The scenario to set up.
            target_dir: Target directory (created if doesn't exist). If None, uses a temp dir.

        Returns:
            Path to the scenario directory.
        """
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            raise ValueError(f"Unknown scenario: {scenario_id}")

        if target_dir is None:
            target_dir = tempfile.mkdtemp(prefix=f"ai-test-{scenario_id}-")

        os.makedirs(target_dir, exist_ok=True)

        for filename, content in scenario.setup_files.items():
            filepath = Path(target_dir) / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")

        return target_dir

    def run_scenario(self, scenario_id: str) -> dict[str, Any]:
        """
        Run a test scenario and return results.

        Sets up the scenario, runs analysis modules, and checks if
        expected issues are detected.
        """
        from core.project_manager.workspace.repo_repair import RepoRepair
        from core.project_manager.workspace.project_understanding import ProjectUnderstanding

        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            return {"error": f"Unknown scenario: {scenario_id}"}

        # Setup
        project_dir = self.setup_scenario(scenario_id)

        try:
            # Run analysis
            repair = RepoRepair(project_dir)
            understanding = ProjectUnderstanding()

            broken_imports = repair.find_broken_imports()
            circular_deps = repair.find_circular_dependencies()
            deprecated = repair.find_deprecated_patterns()
            missing_deps = repair.find_missing_dependencies()
            snapshot = understanding.analyze(project_dir)

            # Check expected issues
            detected_issues: list[str] = []
            if broken_imports:
                detected_issues.append("broken_imports")
            if circular_deps:
                detected_issues.append("circular_dependencies")
            if deprecated:
                detected_issues.append("deprecated_patterns")
            if missing_deps:
                detected_issues.append("missing_dependencies")

            # Check results
            found_expected = []
            missed_expected = []
            for expected in scenario.expected_issues:
                if expected in detected_issues:
                    found_expected.append(expected)
                else:
                    missed_expected.append(expected)

            result = {
                "scenario_id": scenario_id,
                "scenario_name": scenario.name,
                "project_dir": project_dir,
                "detected_issues": detected_issues,
                "expected_issues": scenario.expected_issues,
                "found_expected": found_expected,
                "missed_expected": missed_expected,
                "success": len(missed_expected) == 0,
                "details": {
                    "broken_imports_count": len(broken_imports),
                    "circular_deps_count": len(circular_deps),
                    "deprecated_patterns_count": len(deprecated),
                    "missing_deps_count": len(missing_deps),
                    "detected_language": snapshot.language,
                    "detected_frameworks": snapshot.frameworks,
                },
            }

            self._results.append(result)
            return result

        except Exception as e:
            result = {
                "scenario_id": scenario_id,
                "scenario_name": scenario.name,
                "error": str(e),
                "success": False,
            }
            self._results.append(result)
            return result

    def run_all_scenarios(self) -> list[dict[str, Any]]:
        """Run all test scenarios."""
        results = []
        for scenario_id in self._scenarios:
            result = self.run_scenario(scenario_id)
            results.append(result)
        return results

    def generate_report(self) -> dict[str, Any]:
        """Generate a summary report of all test results."""
        if not self._results:
            return {"message": "No test results yet. Run scenarios first."}

        total = len(self._results)
        passed = sum(1 for r in self._results if r.get("success"))
        failed = total - passed

        return {
            "total_scenarios": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed}/{total}",
            "results": self._results,
        }
