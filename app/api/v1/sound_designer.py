"""AI Sound Designer — enqueued via Celery."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tool_runner import enqueue_tool
from app.database import get_db
from app.deps import get_current_user
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import GenerationResponse, SoundDesignerRequest

router = APIRouter(prefix="/sound-designer", tags=["sound-designer"])


@router.post("", response_model=GenerationResponse)
async def generate_sound(
    body: SoundDesignerRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    def enqueue(gen):
        from app.tasks.sound_task import generate_sound_task

        task = generate_sound_task.delay(
            str(gen.id), body.description, body.kind, body.mood, body.duration_sec
        )
        gen.celery_task_id = task.id

    return await enqueue_tool(
        request=request,
        db=db,
        user=user,
        tool=ToolType.SOUND_DESIGNER,
        input_data=body.model_dump(mode="json"),
        title=f"{body.kind}: {body.description[:60]}",
        project_id=body.project_id,
        enqueue=enqueue,
    )
