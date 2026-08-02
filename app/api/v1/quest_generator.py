"""AI Quest Generator endpoint."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tool_runner import run_tool
from app.database import get_db
from app.deps import get_current_user
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import GenerationResponse, QuestGeneratorRequest
from app.services import ai_quest_generator

router = APIRouter(prefix="/quest-generator", tags=["quest-generator"])


@router.post("", response_model=GenerationResponse)
async def generate_quest(
    body: QuestGeneratorRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await run_tool(
        request=request,
        db=db,
        user=user,
        tool=ToolType.QUEST_GENERATOR,
        input_data=body.model_dump(mode="json"),
        title=f"{body.quest_type.title()} quest: {body.setting[:60]}",
        project_id=body.project_id,
        run=lambda: ai_quest_generator.generate_quest(
            body.setting, body.quest_type, body.length, body.tone
        ),
    )
