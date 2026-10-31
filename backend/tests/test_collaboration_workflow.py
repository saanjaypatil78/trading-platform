"""Tests for collaboration task frontmatter and sequential workflow rules."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")

import pytest
from pydantic import ValidationError

from backend.services.collaboration.workflow import (
    TaskFrontmatter,
    TaskPriority,
    TaskStatus,
    TaskTransitionError,
    validate_dependency_graph,
    validate_transition,
)


def test_task_frontmatter_accepts_valid_task():
    task = TaskFrontmatter(
        id="TASK-002",
        title="Shared Markdown collaboration",
        status=TaskStatus.READY,
        priority=TaskPriority.P0,
        depends_on=["TASK-001"],
        acceptance_criteria=["Two authenticated editors converge"],
    )
    assert task.status == TaskStatus.READY


@pytest.mark.parametrize(
    "payload",
    [
        {"id": "TASK-1", "title": "Self dependency", "depends_on": ["TASK-1"]},
        {"id": "TASK-1", "title": "Duplicate dependency", "depends_on": ["TASK-0", "TASK-0"]},
        {"id": "TASK-1", "title": "Invalid status", "status": "DONE"},
        {"id": "TASK-1", "title": "Unexpected field", "is_admin": True},
    ],
)
def test_invalid_frontmatter_is_rejected(payload):
    with pytest.raises(ValidationError):
        TaskFrontmatter.model_validate(payload)


def test_backlog_cannot_skip_directly_to_running():
    with pytest.raises(TaskTransitionError):
        validate_transition(TaskStatus.BACKLOG, TaskStatus.RUNNING)


def test_task_cannot_run_before_dependencies_complete():
    with pytest.raises(TaskTransitionError):
        validate_transition(
            TaskStatus.READY,
            TaskStatus.RUNNING,
            dependency_statuses=[TaskStatus.REVIEW],
        )


def test_blocked_task_can_return_to_ready_after_dependencies_complete():
    validate_transition(
        TaskStatus.BLOCKED,
        TaskStatus.READY,
        dependency_statuses=[TaskStatus.COMPLETE],
    )


def test_complete_requires_evidence_and_authorised_reviewer():
    with pytest.raises(TaskTransitionError):
        validate_transition(
            TaskStatus.REVIEW,
            TaskStatus.COMPLETE,
            acceptance_evidence=["CI run passed"],
            reviewer_authorized=False,
        )
    with pytest.raises(TaskTransitionError):
        validate_transition(
            TaskStatus.REVIEW,
            TaskStatus.COMPLETE,
            acceptance_evidence=[],
            reviewer_authorized=True,
        )
    validate_transition(
        TaskStatus.REVIEW,
        TaskStatus.COMPLETE,
        acceptance_evidence=["CI run passed"],
        reviewer_authorized=True,
    )


def test_dependency_cycle_and_missing_reference_are_rejected():
    with pytest.raises(TaskTransitionError):
        validate_dependency_graph({"A": ["B"], "B": ["A"]})
    with pytest.raises(TaskTransitionError):
        validate_dependency_graph({"A": ["UNKNOWN"]})


def test_acyclic_dependency_graph_is_accepted():
    validate_dependency_graph({"A": [], "B": ["A"], "C": ["A", "B"]})
