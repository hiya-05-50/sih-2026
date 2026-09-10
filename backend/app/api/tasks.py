"""Sprint 1 – Task API endpoints.

Provides task lifecycle endpoints under ``/v1/tasks``.
Tasks are submitted, classified, routed to a model, executed,
and their routing rationale is returned for judge visibility.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.task import TaskExecution, TaskProfile, TaskSubmitRequest
from app.services.lifecycle import TaskLifecycleManager

router = APIRouter(prefix="/v1/tasks", tags=["tasks"])

# Module-level reference set by main.py at startup via ``configure()``.
_lifecycle: TaskLifecycleManager | None = None


def configure(lifecycle: TaskLifecycleManager) -> None:
    """Inject the shared TaskLifecycleManager singleton."""
    global _lifecycle  # noqa: PLW0603
    _lifecycle = lifecycle


def _get_lifecycle() -> TaskLifecycleManager:
    assert _lifecycle is not None, "tasks router not configured"
    return _lifecycle


@router.post("/", status_code=201, response_model=TaskExecution)
async def submit_task(request: TaskSubmitRequest) -> TaskExecution:
    """Submit a new task for execution through the lifecycle pipeline.

    The task will be classified, routed to the best model, executed,
    and the routing rationale will be included in the response.
    """
    profile = TaskProfile(
        task_type=request.task_type,
        description=request.description,
        input_data=request.input_data,
        priority=request.priority,
    )

    result = await _get_lifecycle().execute(profile)
    return result


@router.get("/{task_id}", response_model=TaskExecution)
def get_task(task_id: str) -> TaskExecution:
    """Get the execution details of a specific task."""
    task = _get_lifecycle().get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=404, detail=f"Task '{task_id}' not found"
        )
    return task


@router.get("/", response_model=list[TaskExecution])
def list_tasks() -> list[TaskExecution]:
    """List all task executions."""
    return _get_lifecycle().list_tasks()
