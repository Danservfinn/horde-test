"""Report generator for test results."""

import json
import html
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

from .aggregator import TestResults, SuiteResult, TestResult


class ReportGenerator:
    """Generate HTML, Markdown, and coverage reports."""

    def __init__(self, output_dir: Path | str):
        """Initialize with output directory."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(self, results: TestResults) -> dict[str, Path]:
        """Generate all report formats."""
        artifacts = {}

        # HTML report
        html_path = self.output_dir / "report.html"
        self.generate_html(results, html_path)
        artifacts["report_html"] = html_path

        # Markdown report
        md_path = self.output_dir / "report.md"
        self.generate_markdown(results, md_path)
        artifacts["report_markdown"] = md_path

        # Coverage JSON
        coverage_json_path = self.output_dir / "coverage.json"
        self.generate_coverage_json(results, coverage_json_path)
        artifacts["coverage_json"] = coverage_json_path

        return artifacts

    def generate_html(self, results: TestResults, output_path: Optional[Path] = None) -> str:
        """Generate HTML report."""
        if output_path is None:
            output_path = self.output_dir / "report.html"

        html_content = self._build_html(results)
        output_path.write_text(html_content)

        return str(output_path)

    def _build_html(self, results: TestResults) -> str:
        """Build HTML report content."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_class = "success" if results.success else "failure"
        status_text = "PASSED" if results.success else "FAILED"

        suites_html = []
        for suite in results.suites:
            suite_status = suite.status
            suite_class = "suite-pass" if suite_status == "passed" else "suite-fail"

            tests_html = []
            for test in suite.tests:
                test_class = f"test-{test.status}"
                tests_html.append(f"""
                    <tr class="{test_class}">
                        <td>{html.escape(test.name)}</td>
                        <td>{test.status.upper()}</td>
                        <td>{test.duration_ms}ms</td>
                        <td>{html.escape(test.message) if test.message else "-"}</td>
                    </tr>
                """)

            suites_html.append(f"""
                <div class="suite {suite_class}">
                    <h3>{html.escape(suite.name)} ({suite.category})</h3>
                    <p>Status: {suite_status.upper()} | Duration: {suite.duration_ms}ms</p>
                    {f'<p>Coverage: Line {suite.coverage.get("line", 0):.1f}%</p>' if suite.coverage else ''}
                    <table>
                        <thead>
                            <tr>
                                <th>Test</th>
                                <th>Status</th>
                                <th>Duration</th>
                                <th>Message</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(tests_html) if tests_html else '<tr><td colspan="4">No test details</td></tr>'}
                        </tbody>
                    </table>
                </div>
            """)

        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Test Report - {html.escape(results.execution_id)}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .status {{
            font-size: 24px;
            font-weight: bold;
            padding: 10px 20px;
            border-radius: 4px;
            display: inline-block;
        }}
        .success {{ background: #4caf50; color: white; }}
        .failure {{ background: #f44336; color: white; }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .summary-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary-card h4 {{
            margin: 0 0 10px 0;
            color: #666;
        }}
        .summary-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        .suite {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .suite-pass {{ border-left: 4px solid #4caf50; }}
        .suite-fail {{ border-left: 4px solid #f44336; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            text-align: left;
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f5f5f5;
            font-weight: 600;
        }}
        .test-pass {{ color: #4caf50; }}
        .test-fail {{ color: #f44336; }}
        .test-skipped {{ color: #ff9800; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Test Report</h1>
        <div class="status {status_class}">{status_text}</div>
        <p>Execution ID: {html.escape(results.execution_id)}</p>
        <p>Timestamp: {timestamp}</p>
        <p>Duration: {results.duration_ms}ms</p>
        <p>Message: {html.escape(results.message)}</p>
    </div>

    <div class="summary">
        <div class="summary-card">
            <h4>Total Suites</h4>
            <div class="value">{results.summary.total_suites}</div>
        </div>
        <div class="summary-card">
            <h4>Passed Suites</h4>
            <div class="value" style="color: #4caf50;">{results.summary.passed_suites}</div>
        </div>
        <div class="summary-card">
            <h4>Failed Suites</h4>
            <div class="value" style="color: #f44336;">{results.summary.failed_suites}</div>
        </div>
        <div class="summary-card">
            <h4>Pass Rate</h4>
            <div class="value">{results.summary.pass_rate:.1f}%</div>
        </div>
    </div>

    <h2>Test Suites</h2>
    {''.join(suites_html) if suites_html else '<p>No test suites executed</p>'}
</body>
</html>
"""

    def generate_markdown(self, results: TestResults, output_path: Optional[Path] = None) -> str:
        """Generate Markdown report."""
        if output_path is None:
            output_path = self.output_dir / "report.md"

        status_emoji = "✅" if results.success else "❌"
        lines = [
            "# Test Report",
            "",
            f"{status_emoji} **{results.message}**",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Suites | {results.summary.total_suites} |",
            f"| Passed Suites | {results.summary.passed_suites} |",
            f"| Failed Suites | {results.summary.failed_suites} |",
            f"| Total Tests | {results.summary.total_tests} |",
            f"| Passed Tests | {results.summary.passed_tests} |",
            f"| Failed Tests | {results.summary.failed_tests} |",
            f"| Skipped Tests | {results.summary.skipped_tests} |",
            f"| Pass Rate | {results.summary.pass_rate:.1f}% |",
            "",
        ]

        if results.coverage.line > 0:
            lines.extend([
                "## Coverage",
                "",
                "| Type | Coverage |",
                "|------|----------|",
                f"| Line | {results.coverage.line:.1f}% |",
                f"| Branch | {results.coverage.branch:.1f}% |",
                f"| Function | {results.coverage.function:.1f}% |",
                "",
            ])

        lines.extend([
            "## Test Suites",
            "",
        ])

        for suite in results.suites:
            status = "✅" if suite.status == "passed" else "❌"
            lines.extend([
                f"### {status} {suite.name} ({suite.category})",
                "",
                f"- **Status**: {suite.status}",
                f"- **Duration**: {suite.duration_ms}ms",
            ])

            if suite.coverage:
                lines.append(f"- **Coverage**: Line {suite.coverage.get('line', 0):.1f}%")

            if suite.tests:
                lines.extend([
                    "",
                    "| Test | Status | Duration |",
                    "|------|--------|----------|",
                ])
                for test in suite.tests:
                    emoji = "✅" if test.status == "passed" else "❌" if test.status == "failed" else "⏭️"
                    lines.append(f"| {test.name} | {emoji} {test.status} | {test.duration_ms}ms |")

            lines.append("")

        content = "\n".join(lines)
        output_path.write_text(content)

        return str(output_path)

    def generate_coverage_json(self, results: TestResults, output_path: Optional[Path] = None) -> str:
        """Generate coverage JSON."""
        if output_path is None:
            output_path = self.output_dir / "coverage.json"

        data = {
            "execution_id": results.execution_id,
            "timestamp": results.timestamp,
            "overall": {
                "line": results.coverage.line,
                "branch": results.coverage.branch,
                "function": results.coverage.function,
            },
            "by_file": [
                {
                    "file": fc.file,
                    "line": fc.line,
                    "branch": fc.branch,
                    "function": fc.function,
                }
                for fc in results.coverage_by_file
            ],
            "meets_targets": results.meets_targets,
        }

        output_path.write_text(json.dumps(data, indent=2))

        return str(output_path)
