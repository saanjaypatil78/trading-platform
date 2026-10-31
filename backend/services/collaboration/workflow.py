"""Pure task workflow validation for the shared Markdown workspace.

Persistence and append-only audit storage are implemented by later collaboration
infrastructure work; this module only validates proposed state transitions.
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TaskStatus(str, Enum):
    BACKLOG = "BACKLOG"
    READY = "READY"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    REVIEW = "REVIEW"
    COMPLETE = "COMPLETE"


class TaskPriority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class TaskFrontmatter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    title: str = Field(min_length=1, max_length=200)
    status: TaskStatus = TaskStatus.BACKLOG
    priority: TaskPriority = TaskPriority.P2
    depends_on: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    owner_id: str | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_dependencies(self):
        if self.id in self.depends_on:
            raise ValueError("A task cannot depend on itself")
        if len(self.depends_on) != len(set(self.depends_on)):
            raise ValueError("Dependency IDs must be unique")
        if any(not item.strip() for item in self.depends_on):
            raise ValueError("Dependency IDs cannot be blank")
        for field_name, value in (("created_at", self.created_at), ("updated_at", self.updated_at)):
            if value.tzinfo is None or value.utcoffset() != timedelta(0):
                raise ValueError(f"{field_name} must be timezone-aware UTC")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
        return self


_ALLOWED_TRANSITIONS = {
    TaskStatus.BACKLOG: {TaskStatus.READY, TaskStatus.BLOCKED},
    TaskStatus.READY: {TaskStatus.RUNNING, TaskStatus.BLOCKED},
    TaskStatus.RUNNING: {TaskStatus.REVIEW, TaskStatus.BLOCKED},
    TaskStatus.BLOCKED: {TaskStatus.READY},
    TaskStatus.REVIEW: {TaskStatus.RUNNING, TaskStatus.COMPLETE},
    TaskStatus.COMPLETE: set(),
}


class TaskTransitionError(ValueError):
    """Raised when a task state transition violates workflow policy."""


def validate_transition(
    current: TaskStatus,
    target: TaskStatus,
    dependency_statuses: Sequence[TaskStatus] = (),
    acceptance_evidence: Sequence[str] = (),
    reviewer_authorized: bool = False,
) -> None:
    """Validate a proposed transition without mutating persisted state."""
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise TaskTransitionError(f"Transition {current.value} -> {target.value} is not allowed")

    if target in (TaskStatus.READY, TaskStatus.RUNNING):
        incomplete = [status for status in dependency_statuses if status != TaskStatus.COMPLETE]
        if incomplete:
            raise TaskTransitionError("All dependencies must be COMPLETE before READY/RUNNING")

    if target == TaskStatus.COMPLETE:
        if not acceptance_evidence or any(not item.strip() for item in acceptance_evidence):
            raise TaskTransitionError("COMPLETE requires non-empty acceptance evidence")
        if not reviewer_authorized:
            raise TaskTransitionError("COMPLETE requires an authorised reviewer")


def validate_dependency_graph(graph: Mapping[str, Sequence[str]]) -> None:
    """Reject missing dependency IDs and cycles in a workspace task graph."""
    task_ids = set(graph)
    for task_id, dependencies in graph.items():
        if task_id in dependencies:
            raise TaskTransitionError(f"Task {task_id} cannot depend on itself")
        missing = set(dependencies) - task_ids
        if missing:
            raise TaskTransitionError(
                f"Task {task_id} references unknown dependencies: {sorted(missing)}"
            )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise TaskTransitionError("Dependency cycle detected")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency_id in graph[task_id]:
            visit(dependency_id)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in task_ids:
        visit(task_id)
