"""AI Character Creator — always enqueued via Celery for heavy image work."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tool_runner import enqueue_tool
from app.database import get_db
from app.deps import get_current_user
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import CharacterCreatorRequest, GenerationResponse

router = APIRouter(prefix="/character-creator", tags=["character-creator"])


@router.post("", response_model=GenerationResponse)
async def create_character(
    body: CharacterCreatorRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    def enqueue(gen):
        from app.tasks.character_task import create_character_task

        task = create_character_task.delay(
            str(gen.id), body.description, body.style, body.view
        )
        gen.celery_task_id = task.id

    return await enqueue_tool(
        request=request,
        db=db,
        user=user,
        tool=ToolType.CHARACTER_CREATOR,
        input_data=body.model_dump(mode="json"),
        title=body.description[:80],
        project_id=body.project_id,
        enqueue=enqueue,
    )
