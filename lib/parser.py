"""Test plan parser with schema validation."""

import json
import yaml
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field


@dataclass
class SuiteConfig:
    """Configuration for a test suite."""
    timeout: int = 300
    retries: int = 0
    parallel: bool = True
    coverage: bool = True


@dataclass
class TestSuite:
    """A test suite definition."""
    name: str
    category: str
    files: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    config: SuiteConfig = field(default_factory=SuiteConfig)


@dataclass
class CoverageTargets:
    """Coverage targets for the test plan."""
    line: float = 80.0
    branch: float = 70.0
    function: float = 90.0


@dataclass
class CoverageConfig:
    """Coverage configuration."""
    enabled: bool = True
    targets: CoverageTargets = field(default_factory=CoverageTargets)
    fail_on_missed: bool = True


@dataclass
class ExecutionConfig:
    """Execution configuration."""
    max_parallel_suites: int = 4
    fail_fast: bool = False
    continue_on_failure: bool = True
    timeout: int = 1800


@dataclass
class SuccessCriteria:
    """Success criteria for the test plan."""
    min_pass_rate: float = 95.0
    critical_suites: list[str] = field(default_factory=list)
    no_critical_failures: bool = True


@dataclass
class TestPlan:
    """Complete test plan definition."""
    plan_id: str
    version: str
    context: dict[str, Any] = field(default_factory=dict)
    scope: dict[str, Any] = field(default_factory=dict)
    suites: list[TestSuite] = field(default_factory=list)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    coverage: CoverageConfig = field(default_factory=CoverageConfig)
    success_criteria: SuccessCriteria = field(default_factory=SuccessCriteria)


class TestPlanParser:
    """Parser for test plan YAML/JSON files."""

    VALID_CATEGORIES = {
        "unit", "integration", "e2e", "performance", "security", "accessibility"
    }

    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize parser with optional schema path."""
        self.schema_path = schema_path

    def parse(self, plan_path: Path | str) -> TestPlan:
        """Parse a test plan from file."""
        plan_path = Path(plan_path)

        if not plan_path.exists():
            raise FileNotFoundError(f"Test plan not found: {plan_path}")

        content = plan_path.read_text()

        # Parse based on file extension
        if plan_path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(content)
        elif plan_path.suffix == ".json":
            data = json.loads(content)
        else:
            # Try YAML first, then JSON
            try:
                data = yaml.safe_load(content)
            except yaml.YAMLError:
                data = json.loads(content)

        return self._parse_dict(data)

    def parse_string(self, content: str, format: str = "yaml") -> TestPlan:
        """Parse a test plan from string."""
        if format == "yaml":
            data = yaml.safe_load(content)
        elif format == "json":
            data = json.loads(content)
        else:
            raise ValueError(f"Unknown format: {format}")

        return self._parse_dict(data)

    def _parse_dict(self, data: dict) -> TestPlan:
        """Parse test plan from dictionary."""
        self._validate_required(data)

        # Parse suites
        suites = []
        for suite_data in data.get("suites", []):
            suites.append(self._parse_suite(suite_data))

        # Parse nested config objects
        execution = self._parse_execution(data.get("execution", {}))
        coverage = self._parse_coverage(data.get("coverage", {}))
        success_criteria = self._parse_success_criteria(data.get("success_criteria", {}))

        return TestPlan(
            plan_id=data["plan_id"],
            version=data["version"],
            context=data.get("context", {}),
            scope=data.get("scope", {}),
            suites=suites,
            execution=execution,
            coverage=coverage,
            success_criteria=success_criteria,
        )

    def _parse_suite(self, data: dict) -> TestSuite:
        """Parse a test suite definition."""
        # Validate category
        category = data.get("category", "")
        if category not in self.VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. "
                f"Must be one of: {', '.join(self.VALID_CATEGORIES)}"
            )

        # Parse config
        config_data = data.get("config", {})
        config = SuiteConfig(
            timeout=config_data.get("timeout", 300),
            retries=config_data.get("retries", 0),
            parallel=config_data.get("parallel", True),
            coverage=config_data.get("coverage", True),
        )

        return TestSuite(
            name=data["name"],
            category=category,
            files=data.get("files", []),
            dependencies=data.get("dependencies", []),
            config=config,
        )

    def _parse_execution(self, data: dict) -> ExecutionConfig:
        """Parse execution configuration."""
        return ExecutionConfig(
            max_parallel_suites=data.get("max_parallel_suites", 4),
            fail_fast=data.get("fail_fast", False),
            continue_on_failure=data.get("continue_on_failure", True),
            timeout=data.get("timeout", 1800),
        )

    def _parse_coverage(self, data: dict) -> CoverageConfig:
        """Parse coverage configuration."""
        targets_data = data.get("targets", {})
        targets = CoverageTargets(
            line=targets_data.get("line", 80.0),
            branch=targets_data.get("branch", 70.0),
            function=targets_data.get("function", 90.0),
        )

        return CoverageConfig(
            enabled=data.get("enabled", True),
            targets=targets,
            fail_on_missed=data.get("fail_on_missed", True),
        )

    def _parse_success_criteria(self, data: dict) -> SuccessCriteria:
        """Parse success criteria."""
        return SuccessCriteria(
            min_pass_rate=data.get("min_pass_rate", 95.0),
            critical_suites=data.get("critical_suites", []),
            no_critical_failures=data.get("no_critical_failures", True),
        )

    def _validate_required(self, data: dict) -> None:
        """Validate required fields exist."""
        required = ["plan_id", "version", "suites"]
        missing = [f for f in required if f not in data]

        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        if not data.get("suites"):
            raise ValueError("At least one test suite is required")

        # Validate plan_id format
        plan_id = data.get("plan_id", "")
        if not plan_id or not plan_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                f"Invalid plan_id '{plan_id}'. Must be alphanumeric with hyphens/underscores."
            )
