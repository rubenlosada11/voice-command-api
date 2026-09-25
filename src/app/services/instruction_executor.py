from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from src.app.schemas.voice import InstructionPayload, TaskCreate, TaskReplace, TaskUpdate
from src.app.services import task_store
from src.app.services.instruction_resolver import InvalidInstructionError

ParamsModel = TypeVar("ParamsModel", bound=BaseModel)


def execute_instruction(instruction: InstructionPayload) -> Any:
    """Run a validated instruction with the same rules as the /tasks endpoints."""
    method = instruction.method
    if method == "GET":
        return task_store.list_tasks()
    if method == "POST":
        data = _validate(TaskCreate, instruction.params)
        return task_store.create_task(data.title, data.done)

    task_id = int(instruction.endpoint.rsplit("/", 1)[1])
    if method == "PUT":
        data = _validate(TaskReplace, instruction.params)
        return task_store.replace_task(task_id, data.title, data.done)
    if method == "PATCH":
        data = _validate(TaskUpdate, instruction.params)
        return task_store.update_task(task_id, data.title, data.done)
    if method == "DELETE":
        return task_store.delete_task(task_id)
    raise InvalidInstructionError(f"Unsupported method: {method}.")


def _validate(model: type[ParamsModel], params: dict[str, Any]) -> ParamsModel:
    try:
        return model.model_validate(params)
    except ValidationError as exc:
        raise InvalidInstructionError(
            "The language model returned invalid params for this action."
        ) from exc
