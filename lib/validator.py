"""Success criteria validator for test results."""

from dataclasses import dataclass, field
from typing import Optional

from .parser import CoverageTargets, SuccessCriteria
from .aggregator import TestResults, ExecutionSummary, CoverageSummary


@dataclass
class ValidationResult:
    """Result of success criteria validation."""
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class SuccessValidator:
    """Validates test results against success criteria."""

    def __init__(self, criteria: SuccessCriteria, coverage_targets: Optional[CoverageTargets] = None):
        """Initialize with success criteria."""
        self.criteria = criteria
        self.coverage_targets = coverage_targets

    def validate(self, results: TestResults) -> ValidationResult:
        """Validate test results against all criteria."""
        checks = {}
        failures = []
        warnings = []

        # Check 1: Pass rate
        pass_rate_ok = self._check_pass_rate(results.summary)
        checks["pass_rate"] = pass_rate_ok
        if not pass_rate_ok:
            failures.append(
                f"Pass rate {results.summary.pass_rate:.1f}% below minimum "
                f"{self.criteria.min_pass_rate:.1f}%"
            )

        # Check 2: Critical suites
        critical_ok = self._check_critical_suites(results)
        checks["critical_suites"] = critical_ok
        if not critical_ok:
            failed_critical = self._get_failed_critical_suites(results)
            failures.append(f"Critical suites failed: {', '.join(failed_critical)}")

        # Check 3: No critical failures
        if self.criteria.no_critical_failures:
            no_critical_failures = self._check_no_critical_failures(results)
            checks["no_critical_failures"] = no_critical_failures
            if not no_critical_failures:
                failures.append("Critical test failures detected")

        # Check 4: Coverage targets (if enabled)
        if self.coverage_targets:
            coverage_ok = self._check_coverage(results.coverage)
            checks["coverage"] = coverage_ok
            if not coverage_ok:
                coverage_failures = self._get_coverage_failures(results.coverage)
                failures.extend(coverage_failures)
        else:
            checks["coverage"] = True  # Not checked

        # Warnings for slow tests
        slow_tests = self._get_slow_test_warning(results)
        if slow_tests:
            warnings.append(slow_tests)

        # Overall result
        passed = all(checks.values())

        return ValidationResult(
            passed=passed,
            checks=checks,
            failures=failures,
            warnings=warnings
        )

    def _check_pass_rate(self, summary: ExecutionSummary) -> bool:
        """Check if pass rate meets minimum."""
        return summary.pass_rate >= self.criteria.min_pass_rate

    def _check_critical_suites(self, results: TestResults) -> bool:
        """Check if all critical suites passed."""
        if not self.criteria.critical_suites:
            return True

        suite_status = {s.name: s.status for s in results.suites}

        for critical in self.criteria.critical_suites:
            if critical not in suite_status:
                return False  # Critical suite not found
            if suite_status[critical] != "passed":
                return False

        return True

    def _get_failed_critical_suites(self, results: TestResults) -> list[str]:
        """Get list of failed critical suites."""
        failed = []
        suite_status = {s.name: s.status for s in results.suites}

        for critical in self.criteria.critical_suites:
            if critical in suite_status and suite_status[critical] != "passed":
                failed.append(critical)
            elif critical not in suite_status:
                failed.append(f"{critical} (not found)")

        return failed

    def _check_no_critical_failures(self, results: TestResults) -> bool:
        """Check for critical test failures (e.g., security)."""
        # Security tests are always critical
        for suite in results.suites:
            if suite.category == "security" and suite.status != "passed":
                return False

        return True

    def _check_coverage(self, coverage: CoverageSummary) -> bool:
        """Check if coverage meets targets."""
        if not self.coverage_targets:
            return True

        return (
            coverage.line >= self.coverage_targets.line and
            coverage.branch >= self.coverage_targets.branch and
            coverage.function >= self.coverage_targets.function
        )

    def _get_coverage_failures(self, coverage: CoverageSummary) -> list[str]:
        """Get specific coverage failures."""
        failures = []

        if self.coverage_targets:
            if coverage.line < self.coverage_targets.line:
                failures.append(
                    f"Line coverage {coverage.line:.1f}% below target "
                    f"{self.coverage_targets.line:.1f}%"
                )
            if coverage.branch < self.coverage_targets.branch:
                failures.append(
                    f"Branch coverage {coverage.branch:.1f}% below target "
                    f"{self.coverage_targets.branch:.1f}%"
                )
            if coverage.function < self.coverage_targets.function:
                failures.append(
                    f"Function coverage {coverage.function:.1f}% below target "
                    f"{self.coverage_targets.function:.1f}%"
                )

        return failures

    def _get_slow_test_warning(self, results: TestResults) -> Optional[str]:
        """Generate warning for slow tests."""
        slow_threshold_ms = 5000  # 5 seconds
        slow_tests = []

        for suite in results.suites:
            for test in suite.tests:
                if test.duration_ms > slow_threshold_ms:
                    slow_tests.append((suite.name, test.name, test.duration_ms))

        if slow_tests:
            # Sort by duration (slowest first)
            slow_tests.sort(key=lambda x: x[2], reverse=True)
            top_slow = slow_tests[:3]  # Top 3

            test_strs = [
                f"{s}.{t} ({d/1000:.1f}s)"
                for s, t, d in top_slow
            ]
            return f"Slow tests detected: {', '.join(test_strs)}"

        return None

    def generate_report(self, results: TestResults, validation: ValidationResult) -> str:
        """Generate a human-readable validation report."""
        lines = [
            "=" * 60,
            "SUCCESS CRITERIA VALIDATION",
            "=" * 60,
            "",
            f"Overall: {'✅ PASSED' if validation.passed else '❌ FAILED'}",
            "",
            "Checks:",
        ]

        for check, passed in validation.checks.items():
            status = "✅" if passed else "❌"
            lines.append(f"  {status} {check}")

        if validation.failures:
            lines.extend([
                "",
                "Failures:",
            ])
            for failure in validation.failures:
                lines.append(f"  ❌ {failure}")

        if validation.warnings:
            lines.extend([
                "",
                "Warnings:",
            ])
            for warning in validation.warnings:
                lines.append(f"  ⚠️  {warning}")

        lines.extend([
            "",
            "Summary:",
            f"  Suites: {results.summary.passed_suites}/{results.summary.total_suites} passed",
            f"  Tests: {results.summary.passed_tests}/{results.summary.total_tests} passed",
            f"  Pass Rate: {results.summary.pass_rate:.1f}%",
        ])

        if results.coverage.line > 0:
            lines.extend([
                "",
                "Coverage:",
                f"  Line: {results.coverage.line:.1f}%",
                f"  Branch: {results.coverage.branch:.1f}%",
                f"  Function: {results.coverage.function:.1f}%",
            ])

        lines.append("=" * 60)

        return "\n".join(lines)
