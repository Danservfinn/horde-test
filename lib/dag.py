"""DAG builder for test suite dependencies."""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional

from .parser import TestPlan, TestSuite


@dataclass
class DAGNode:
    """A node in the execution DAG."""
    suite: TestSuite
    dependencies: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)
    executed: bool = False
    status: Optional[str] = None


class DAGBuilder:
    """Builds and manages the execution DAG for test suites."""

    def __init__(self, plan: TestPlan):
        """Initialize with a test plan."""
        self.plan = plan
        self.nodes: dict[str, DAGNode] = {}
        self._build()

    def _build(self) -> None:
        """Build the DAG from test suites."""
        # Create nodes for all suites
        for suite in self.plan.suites:
            self.nodes[suite.name] = DAGNode(suite=suite)

        # Build dependency relationships
        for suite in self.plan.suites:
            node = self.nodes[suite.name]

            for dep_name in suite.dependencies:
                if dep_name not in self.nodes:
                    raise ValueError(
                        f"Suite '{suite.name}' depends on unknown suite '{dep_name}'"
                    )

                # Add dependency
                node.dependencies.add(dep_name)

                # Add reverse relationship
                self.nodes[dep_name].dependents.add(suite.name)

        # Detect cycles
        self._detect_cycles()

    def _detect_cycles(self) -> None:
        """Detect circular dependencies using DFS."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {name: WHITE for name in self.nodes}
        path = []

        def dfs(node_name: str) -> None:
            color[node_name] = GRAY
            path.append(node_name)

            for dep in self.nodes[node_name].dependencies:
                if color[dep] == GRAY:
                    # Found cycle
                    cycle_start = path.index(dep)
                    cycle = path[cycle_start:] + [dep]
                    raise ValueError(
                        f"Circular dependency detected: {' -> '.join(cycle)}"
                    )
                elif color[dep] == WHITE:
                    dfs(dep)

            path.pop()
            color[node_name] = BLACK

        for name in self.nodes:
            if color[name] == WHITE:
                dfs(name)

    def get_execution_order(self) -> list[list[str]]:
        """
        Get execution order as parallelizable groups.

        Returns a list of groups, where each group contains suite names
        that can be executed in parallel.
        """
        # Calculate in-degrees
        in_degree = {name: len(node.dependencies)
                     for name, node in self.nodes.items()}

        # Find initial nodes (no dependencies)
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        groups = []

        while queue:
            # All current queue items can run in parallel
            current_group = list(queue)
            groups.append(current_group)

            # Process this group
            queue = deque()
            for name in current_group:
                node = self.nodes[name]
                node.executed = True

                # Update dependents
                for dependent in node.dependents:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        # Check if all nodes were processed
        unexecuted = [name for name, node in self.nodes.items() if not node.executed]
        if unexecuted:
            raise ValueError(
                f"Could not schedule all suites. Unexecuted: {unexecuted}"
            )

        return groups

    def get_parallel_groups(self, max_parallel: int = 4) -> list[list[str]]:
        """
        Get parallel groups respecting max_parallel limit.

        Splits large groups into smaller ones if they exceed max_parallel.
        """
        groups = self.get_execution_order()
        result = []

        for group in groups:
            # Split large groups
            for i in range(0, len(group), max_parallel):
                chunk = group[i:i + max_parallel]
                result.append(chunk)

        return result

    def get_suite(self, name: str) -> Optional[TestSuite]:
        """Get a suite by name."""
        node = self.nodes.get(name)
        return node.suite if node else None

    def get_dependencies(self, name: str) -> list[str]:
        """Get dependencies for a suite."""
        node = self.nodes.get(name)
        return list(node.dependencies) if node else []

    def mark_executed(self, name: str, status: str) -> None:
        """Mark a suite as executed with status."""
        if name in self.nodes:
            self.nodes[name].executed = True
            self.nodes[name].status = status

    def is_ready(self, name: str) -> bool:
        """Check if a suite is ready to execute (all deps satisfied)."""
        node = self.nodes.get(name)
        if not node:
            return False

        return all(
            self.nodes[dep].executed
            for dep in node.dependencies
        )

    def get_ready_suites(self) -> list[str]:
        """Get all suites that are ready to execute."""
        return [
            name for name, node in self.nodes.items()
            if not node.executed and self.is_ready(name)
        ]

    def get_stats(self) -> dict:
        """Get DAG statistics."""
        total = len(self.nodes)
        executed = sum(1 for node in self.nodes.values() if node.executed)
        pending = total - executed

        return {
            "total_suites": total,
            "executed": executed,
            "pending": pending,
            "parallel_groups": len(self.get_execution_order()),
        }
