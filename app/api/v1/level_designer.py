"""AI Level Designer endpoint."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tool_runner import run_tool
from app.database import get_db
from app.deps import get_current_user
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import GenerationResponse, LevelDesignerRequest
from app.services import ai_level_designer

router = APIRouter(prefix="/level-designer", tags=["level-designer"])


@router.post("", response_model=GenerationResponse)
async def generate_level(
    body: LevelDesignerRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await run_tool(
        request=request,
        db=db,
        user=user,
        tool=ToolType.LEVEL_DESIGNER,
        input_data=body.model_dump(mode="json"),
        title=body.description[:80],
        project_id=body.project_id,
        run=lambda: ai_level_designer.generate_level(
            body.description, body.width, body.height, body.style
        ),
    )
