from fastapi import APIRouter

from src.app.schemas.voice import InstructionPayload, InstructionRequest
from src.app.services.instruction_resolver import resolve_instruction

router = APIRouter(tags=["instruction"])


@router.post("/instruction", response_model=InstructionPayload)
async def route_instruction(payload: InstructionRequest) -> InstructionPayload:
    return await resolve_instruction(payload.transcription)
