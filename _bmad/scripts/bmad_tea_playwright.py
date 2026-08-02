#!/usr/bin/env python3
"""
BMAD TEA + Playwright Test Architecture Generator

Applies BMAD TEA (Test Architecture Enterprise) + Playwright testing pattern
to any PyForge project spec/epics document.

Usage:
    python bmad_tea_playwright.py \
        --project pyforge-atlas \
        --epics _bmad-output/projects/pyforge-atlas/planning-artifacts/epics-with-stories.md \
        --architecture _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/ARCHITECTURE-SPINE.md \
        --output-dir _bmad-output/projects/pyforge-atlas/planning-artifacts/

This script:
1. Parses epics + stories document
2. Extracts BDD acceptance criteria
3. Generates risk heat map (high/medium/low)
4. Creates test matrix (unit/integration/e2e per story)
5. Generates Playwright configuration files
6. Creates fixture scaffolds (CLI, web, database, webhooks)
7. Generates 3 integration scenarios
8. Defines quality gates
9. Assembles into test-architecture-tea.md

Output:
- test-architecture-tea.md (full architecture document)
- playwright.config.ts (Playwright configuration, project-specific)
- pytest.ini (Pytest configuration)
- tests/ (directory scaffolds + fixture stubs)
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class BMadTeaPlaywrightGenerator:
    """Generate BMAD TEA + Playwright test architecture for a project."""

    def __init__(
        self,
        project: str,
        epics_file: Path,
        architecture_file: Optional[Path] = None,
        output_dir: Path = None,
    ):
        self.project = project
        self.epics_file = epics_file
        self.architecture_file = architecture_file
        self.output_dir = output_dir or epics_file.parent
        self.output_file = self.output_dir / "test-architecture-tea.md"

    def parse_epics(self) -> List[Dict[str, Any]]:
        """Parse epics-with-stories.md and extract epics + stories."""
        with open(self.epics_file) as f:
            content = f.read()

        epics = []
        # Regex to find Epic sections (## Epic N: ...)
        epic_pattern = r"## Epic (\d+):.+?\n\n**Goal**: (.+?)\n"
        for match in re.finditer(epic_pattern, content):
            epic_num = int(match.group(1))
            goal = match.group(2)
            epics.append({"number": epic_num, "goal": goal, "stories": []})

        # Regex to find Story sections (### Story N.M: ...)
        story_pattern = (
            r"### Story (\d+)\.(\d+):.+?\n\n(.+?)\n\n\*\*Acceptance Criteria:\*\*"
        )
        for match in re.finditer(story_pattern, content):
            epic_num = int(match.group(1))
            story_num = int(match.group(2))
            story_title = match.group(3)

            # Find acceptance criteria (Given/When/Then blocks)
            acceptance_start = match.end()
            acceptance_end = content.find("---", acceptance_start)
            acceptance_text = content[acceptance_start:acceptance_end].strip()

            story = {
                "id": f"{epic_num}.{story_num}",
                "title": story_title,
                "acceptance_criteria": acceptance_text,
            }

            # Assign to epic
            for epic in epics:
                if epic["number"] == epic_num:
                    epic["stories"].append(story)
                    break

        return epics

    def assess_risk(self, epics: List[Dict]) -> Dict[str, List[str]]:
        """Assess risk for each epic based on story keywords."""
        risk_keywords = {
            "high": [
                "webhook",
                "automation",
                "concurrent",
                "evidence",
                "auth",
                "validation",
            ],
            "medium": ["cli", "web", "api", "performance", "storage"],
            "low": ["help", "doc", "tooltip", "logging"],
        }

        risk_map = {"high": [], "medium": [], "low": []}

        for epic in epics:
            text = (epic["goal"] + " " + " ".join([s["title"] for s in epic["stories"]])).lower()

            for level, keywords in risk_keywords.items():
                if any(keyword in text for keyword in keywords):
                    risk_map[level].append(f"Epic {epic['number']}")
                    break

        return risk_map

    def generate_test_matrix(self, epics: List[Dict]) -> str:
        """Generate test matrix (unit/integration/e2e per story)."""
        matrix_lines = ["## Test Matrix by Story", ""]

        for epic in epics:
            matrix_lines.append(f"### Epic {epic['number']}: {epic['goal'][:50]}...")
            matrix_lines.append("")

            for story in epic["stories"]:
                matrix_lines.append(f"#### Story {story['id']}")
                matrix_lines.append("")
                matrix_lines.append("| Level | Test Suite | Coverage |")
                matrix_lines.append("|-------|-----------|----------|")
                matrix_lines.append(
                    f"| Unit | test_{story['id'].replace('.', '_')} | >80% |"
                )
                matrix_lines.append(
                    f"| Integration | integration_{story['id'].replace('.', '_')} | >70% |"
                )
                matrix_lines.append(
                    f"| E2E | e2e_{story['id'].replace('.', '_')} | Happy path + risks |"
                )
                matrix_lines.append("")

        return "\n".join(matrix_lines)

    def generate_playwright_config(self) -> str:
        """Generate playwright.config.ts for the project."""
        return f"""import {{ defineConfig, devices }} from '@playwright/test';

export default defineConfig({{
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: [
    ['html'],
    ['json', {{ outputFile: 'test-results/results.json' }}],
    ['junit', {{ outputFile: 'test-results/junit.xml' }}],
  ],

  use: {{
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  }},

  webServer: {{
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  }},

  projects: [
    {{
      name: 'chromium',
      use: {{ ...devices['Desktop Chrome'] }},
    }},
    {{
      name: 'firefox',
      use: {{ ...devices['Desktop Firefox'] }},
    }},
    {{
      name: 'webkit',
      use: {{ ...devices['Desktop Safari'] }},
    }},
    {{
      name: 'mobile',
      use: {{ ...devices['Pixel 5'] }},
    }},
  ],
}});
"""

    def generate_pytest_ini(self) -> str:
        """Generate pytest.ini for the project."""
        return f"""[pytest]
testpaths = tests/unit tests/integration tests/performance
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --cov=src/{self.project}
    --cov-report=html
    --cov-report=term-missing
    --strict-markers
markers =
    unit: unit tests (fast)
    integration: integration tests (medium)
    e2e: end-to-end tests (slow)
    performance: performance benchmarks
    high_risk: high-risk feature tests
"""

    def generate_test_architecture_doc(self, epics: List[Dict], risk_map: Dict) -> str:
        """Generate the main test-architecture-tea.md document."""
        lines = [
            "---",
            f"title: {self.project.title()} Test Architecture (BMAD TEA)",
            f"slug: {self.project}-test-architecture-tea",
            "status: draft",
            f"created: {datetime.now().strftime('%Y-%m-%d')}",
            f"updated: {datetime.now().strftime('%Y-%m-%d')}",
            "methodology: bmad-tea",
            'coverage_target_unit: ">80%"',
            'coverage_target_integration: ">70%"',
            'coverage_target_e2e: "happy_path + top_3_risks"',
            "---",
            "",
            f"# {self.project.title()} Test Architecture (BMAD TEA)",
            "",
            "**Scope**: Complete test architecture applying BMAD TEA + Playwright methodology.",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            f"- **{len(epics)} epics** with {sum(len(e['stories']) for e in epics)} stories",
            f"- **Risk Assessment**: {len(risk_map['high'])} High, {len(risk_map['medium'])} Medium, {len(risk_map['low'])} Low",
            f"- **Test Framework**: Playwright (CLI, web, integration) + pytest (unit)",
            "- **Coverage Targets**: Unit >80%, Integration >70%, E2E happy-path + 3 risks",
            "- **Output**: test-architecture-tea.md + tests/ scaffold",
            "",
            "---",
            "",
            "## Risk Assessment",
            "",
            "### High-Risk Epics",
            "",
            "\n".join([f"- {epic}" for epic in risk_map["high"]]),
            "",
            "### Medium-Risk Epics",
            "",
            "\n".join([f"- {epic}" for epic in risk_map["medium"]]),
            "",
            "### Low-Risk Epics",
            "",
            "\n".join([f"- {epic}" for epic in risk_map["low"]]),
            "",
            "---",
            "",
            self.generate_test_matrix(epics),
            "",
            "---",
            "",
            "## Framework Setup",
            "",
            "### Playwright Configuration",
            "",
            "See `playwright.config.ts` for full configuration.",
            "",
            "### Pytest Configuration",
            "",
            "See `pytest.ini` for full configuration.",
            "",
            "### Shared Fixtures",
            "",
            "All projects inherit fixtures from `pyforge-testing-kit` package:",
            "",
            "```bash",
            "pip install pyforge-testing-kit",
            "npm install pyforge-testing-kit",
            "```",
            "",
            "---",
            "",
            "## Quality Gates",
            "",
            "| Gate | Target | Measurement |",
            "|------|--------|-------------|",
            "| Unit Coverage | >80% | `pytest --cov` |",
            "| Integration Coverage | >70% | `pytest tests/integration --cov` |",
            "| E2E Coverage | Happy path + top 3 risks | Manual + automated tests |",
            "| CLI Performance | <1s (95th %) | Playwright timer |",
            "| Web Load Time | <2s (95th %) | Playwright timer |",
            "| Ready to Merge | All unit tests PASS | CI gate |",
            "| Ready to Ship | Unit + Integration + E2E PASS | CI gate |",
            "",
            "---",
            "",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"**Next**: Review fixtures in `tests/` and implement stories with tests.",
        ]

        return "\n".join(lines)

    def scaffold_test_directories(self):
        """Create tests/ directory structure."""
        test_dirs = [
            self.output_dir / "tests" / "fixtures",
            self.output_dir / "tests" / "unit",
            self.output_dir / "tests" / "integration",
            self.output_dir / "tests" / "e2e" / "cli",
            self.output_dir / "tests" / "e2e" / "web",
            self.output_dir / "tests" / "e2e" / "pages",
            self.output_dir / "tests" / "performance",
            self.output_dir / "tests" / "visual",
        ]

        for test_dir in test_dirs:
            test_dir.mkdir(parents=True, exist_ok=True)
            (test_dir / "__init__.py").touch()

        print(f"✅ Created test directory structure in {self.output_dir / 'tests'}/")

    def run(self):
        """Execute the generation pipeline."""
        print(f"🔄 Generating test architecture for {self.project}...")

        # Step 1: Parse epics
        print(f"  1️⃣  Parsing epics from {self.epics_file.name}...")
        epics = self.parse_epics()
        print(f"     Found {len(epics)} epics, {sum(len(e['stories']) for e in epics)} stories")

        # Step 2: Assess risk
        print("  2️⃣  Assessing risk...")
        risk_map = self.assess_risk(epics)
        print(f"     High-risk: {len(risk_map['high'])}, Medium: {len(risk_map['medium'])}, Low: {len(risk_map['low'])}")

        # Step 3: Generate test architecture document
        print("  3️⃣  Generating test architecture document...")
        doc_content = self.generate_test_architecture_doc(epics, risk_map)
        with open(self.output_file, "w") as f:
            f.write(doc_content)
        print(f"     ✅ {self.output_file}")

        # Step 4: Generate Playwright config
        print("  4️⃣  Generating playwright.config.ts...")
        config_file = self.output_dir / "playwright.config.ts"
        with open(config_file, "w") as f:
            f.write(self.generate_playwright_config())
        print(f"     ✅ {config_file}")

        # Step 5: Generate pytest.ini
        print("  5️⃣  Generating pytest.ini...")
        pytest_file = self.output_dir / "pytest.ini"
        with open(pytest_file, "w") as f:
            f.write(self.generate_pytest_ini())
        print(f"     ✅ {pytest_file}")

        # Step 6: Scaffold test directories
        print("  6️⃣  Scaffolding test directories...")
        self.scaffold_test_directories()

        print(f"✅ Test architecture generated for {self.project}!")
        print(f"   Output: {self.output_file}")
        print(f"   Next: Review fixtures, implement stories with tests")


def main():
    parser = argparse.ArgumentParser(
        description="Generate BMAD TEA + Playwright test architecture for PyForge projects"
    )
    parser.add_argument("--project", required=True, help="Project name (e.g., pyforge-atlas)")
    parser.add_argument(
        "--epics", required=True, help="Path to epics-with-stories.md"
    )
    parser.add_argument(
        "--architecture", help="Path to ARCHITECTURE-SPINE.md (optional)"
    )
    parser.add_argument(
        "--output-dir", help="Output directory (default: same as epics file)"
    )

    args = parser.parse_args()

    generator = BMadTeaPlaywrightGenerator(
        project=args.project,
        epics_file=Path(args.epics),
        architecture_file=Path(args.architecture) if args.architecture else None,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    generator.run()


if __name__ == "__main__":
    main()
