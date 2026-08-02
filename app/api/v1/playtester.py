"""AI Playtester endpoint."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tool_runner import run_tool
from app.database import get_db
from app.deps import get_current_user
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import GenerationResponse, PlaytesterRequest
from app.services import ai_playtester

router = APIRouter(prefix="/playtester", tags=["playtester"])


@router.post("", response_model=GenerationResponse)
async def run_playtest(
    body: PlaytesterRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await run_tool(
        request=request,
        db=db,
        user=user,
        tool=ToolType.PLAYTESTER,
        input_data=body.model_dump(mode="json"),
        title=f"Playtest ({body.focus})",
        project_id=body.project_id,
        run=lambda: ai_playtester.run_playtest(body.game_description, body.scenarios, body.focus),
    )
