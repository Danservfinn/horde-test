"""
horde-test - Comprehensive testing execution using horde-swarm.

This package provides test plan parsing, execution DAG building,
swarm dispatch, result aggregation, and report generation.
"""

__version__ = "1.0.0"
__all__ = [
    "TestPlan",
    "TestPlanParser",
    "DAGBuilder",
    "ResultAggregator",
    "ReportGenerator",
    "SuccessValidator",
]

from .parser import TestPlan, TestPlanParser
from .dag import DAGBuilder
from .aggregator import ResultAggregator
from .reports import ReportGenerator
from .validator import SuccessValidator
