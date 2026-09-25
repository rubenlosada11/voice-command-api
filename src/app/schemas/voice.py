from typing import Annotated, Any

from pydantic import BaseModel, Field, StringConstraints

NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TaskCreate(BaseModel):
    title: NonBlankStr
    done: bool = False


class TaskReplace(BaseModel):
    title: NonBlankStr
    done: bool


class TaskUpdate(BaseModel):
    title: NonBlankStr | None = None
    done: bool | None = None


class Task(BaseModel):
    id: int
    title: str
    done: bool


class InstructionRequest(BaseModel):
    transcription: NonBlankStr


class InstructionPayload(BaseModel):
    endpoint: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


class TranscribeFlowResponse(BaseModel):
    transcription: str = Field(..., min_length=1)
    instruction: InstructionPayload
    result: Any
