"""Result aggregator for collecting and merging test results."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    status: str  # passed, failed, skipped, error
    duration_ms: int = 0
    message: str = ""
    stack_trace: str = ""


@dataclass
class SuiteResult:
    """Result of a test suite execution."""
    name: str
    category: str
    status: str  # passed, failed, error, skipped
    duration_ms: int = 0
    tests: list[TestResult] = field(default_factory=list)
    coverage: dict[str, float] = field(default_factory=dict)
    artifacts: list[dict[str, str]] = field(default_factory=list)
    error_message: str = ""


@dataclass
class CoverageSummary:
    """Coverage summary statistics."""
    line: float = 0.0
    branch: float = 0.0
    function: float = 0.0


@dataclass
class FileCoverage:
    """Coverage for a single file."""
    file: str
    line: float = 0.0
    branch: float = 0.0
    function: float = 0.0


@dataclass
class ExecutionSummary:
    """Summary of test execution."""
    total_suites: int = 0
    passed_suites: int = 0
    failed_suites: int = 0
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    pass_rate: float = 0.0


@dataclass
class TestResults:
    """Complete test execution results."""
    execution_id: str = ""
    timestamp: str = ""
    duration_ms: int = 0
    summary: ExecutionSummary = field(default_factory=ExecutionSummary)
    suites: list[SuiteResult] = field(default_factory=list)
    coverage: CoverageSummary = field(default_factory=CoverageSummary)
    coverage_by_file: list[FileCoverage] = field(default_factory=list)
    meets_targets: bool = False
    artifacts: dict[str, str] = field(default_factory=dict)
    success: bool = False
    message: str = ""


class ResultAggregator:
    """Aggregates results from multiple test agents."""

    def __init__(self):
        """Initialize the aggregator."""
        self.suite_results: list[SuiteResult] = []
        self.errors: list[str] = []

    def add_suite_result(self, result: SuiteResult) -> None:
        """Add a suite result."""
        self.suite_results.append(result)

    def add_error(self, suite_name: str, error: str) -> None:
        """Add an error for a suite that failed to execute."""
        self.errors.append(f"{suite_name}: {error}")
        # Create a failed suite result
        self.suite_results.append(SuiteResult(
            name=suite_name,
            category="unknown",
            status="error",
            error_message=error
        ))

    def calculate_summary(self) -> ExecutionSummary:
        """Calculate execution summary statistics."""
        summary = ExecutionSummary()
        summary.total_suites = len(self.suite_results)
        summary.passed_suites = sum(
            1 for r in self.suite_results if r.status == "passed"
        )
        summary.failed_suites = sum(
            1 for r in self.suite_results if r.status in ("failed", "error")
        )

        for suite in self.suite_results:
            summary.total_tests += len(suite.tests)
            summary.passed_tests += sum(
                1 for t in suite.tests if t.status == "passed"
            )
            summary.failed_tests += sum(
                1 for t in suite.tests if t.status == "failed"
            )
            summary.skipped_tests += sum(
                1 for t in suite.tests if t.status == "skipped"
            )

        if summary.total_tests > 0:
            summary.pass_rate = (
                summary.passed_tests / summary.total_tests * 100
            )

        return summary

    def merge_coverage(self) -> CoverageSummary:
        """Merge coverage from all suites."""
        if not self.suite_results:
            return CoverageSummary()

        # Collect coverage from all suites that have it
        coverages = [
            s.coverage for s in self.suite_results
            if s.coverage
        ]

        if not coverages:
            return CoverageSummary()

        # Calculate weighted average by number of tests
        total_tests = sum(len(s.tests) for s in self.suite_results if s.coverage)
        if total_tests == 0:
            return CoverageSummary()

        weighted_line = 0.0
        weighted_branch = 0.0
        weighted_function = 0.0

        for suite in self.suite_results:
            if suite.coverage:
                weight = len(suite.tests) / total_tests
                weighted_line += suite.coverage.get("line", 0) * weight
                weighted_branch += suite.coverage.get("branch", 0) * weight
                weighted_function += suite.coverage.get("function", 0) * weight

        return CoverageSummary(
            line=round(weighted_line, 2),
            branch=round(weighted_branch, 2),
            function=round(weighted_function, 2)
        )

    def get_coverage_by_file(self) -> list[FileCoverage]:
        """Get coverage broken down by file."""
        # This would be populated from detailed coverage data
        # For now, return empty list
        return []

    def build_results(
        self,
        execution_id: str,
        timestamp: str,
        duration_ms: int
    ) -> TestResults:
        """Build complete test results."""
        summary = self.calculate_summary()
        coverage = self.merge_coverage()

        # Determine overall success
        success = (
            summary.failed_suites == 0 and
            summary.pass_rate >= 95.0 and
            not self.errors
        )

        # Build message
        if success:
            message = f"All tests passed ({summary.passed_tests}/{summary.total_tests})"
        else:
            message = f"Tests failed: {summary.failed_tests} failed, {summary.skipped_tests} skipped"
            if self.errors:
                message += f", {len(self.errors)} execution errors"

        return TestResults(
            execution_id=execution_id,
            timestamp=timestamp,
            duration_ms=duration_ms,
            summary=summary,
            suites=self.suite_results,
            coverage=coverage,
            coverage_by_file=self.get_coverage_by_file(),
            success=success,
            message=message
        )

    def get_failed_tests(self) -> list[tuple[str, str, str]]:
        """Get list of failed tests with suite name and message."""
        failed = []
        for suite in self.suite_results:
            for test in suite.tests:
                if test.status == "failed":
                    failed.append((suite.name, test.name, test.message))
        return failed

    def get_slow_tests(self, threshold_ms: int = 1000) -> list[tuple[str, str, int]]:
        """Get tests that took longer than threshold."""
        slow = []
        for suite in self.suite_results:
            for test in suite.tests:
                if test.duration_ms > threshold_ms:
                    slow.append((suite.name, test.name, test.duration_ms))
        return sorted(slow, key=lambda x: x[2], reverse=True)

    def to_dict(self) -> dict[str, Any]:
        """Convert results to dictionary."""
        results = self.build_results("", "", 0)
        return {
            "execution_id": results.execution_id,
            "timestamp": results.timestamp,
            "duration_ms": results.duration_ms,
            "summary": {
                "total_suites": results.summary.total_suites,
                "passed_suites": results.summary.passed_suites,
                "failed_suites": results.summary.failed_suites,
                "total_tests": results.summary.total_tests,
                "passed_tests": results.summary.passed_tests,
                "failed_tests": results.summary.failed_tests,
                "skipped_tests": results.summary.skipped_tests,
                "pass_rate": results.summary.pass_rate,
            },
            "suites": [
                {
                    "name": s.name,
                    "category": s.category,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "tests": [
                        {
                            "name": t.name,
                            "status": t.status,
                            "duration_ms": t.duration_ms,
                            "message": t.message,
                        }
                        for t in s.tests
                    ],
                    "coverage": s.coverage,
                }
                for s in results.suites
            ],
            "coverage": {
                "line": results.coverage.line,
                "branch": results.coverage.branch,
                "function": results.coverage.function,
            },
            "meets_targets": results.meets_targets,
            "success": results.success,
            "message": results.message,
        }
