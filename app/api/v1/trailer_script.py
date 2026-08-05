"""AI Trailer Script endpoint."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tool_runner import run_tool
from app.database import get_db
from app.deps import get_current_user
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import GenerationResponse, TrailerScriptRequest
from app.services import ai_trailer_script

router = APIRouter(prefix="/trailer-script", tags=["trailer-script"])


@router.post("", response_model=GenerationResponse)
async def generate_trailer_script(
    body: TrailerScriptRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = body.to_game_data()
    title = f"Trailer: {data.get('game_name') or 'Game'}"
    return await run_tool(
        request=request,
        db=db,
        user=user,
        tool=ToolType.TRAILER_SCRIPT,
        input_data=data,
        title=title[:200],
        project_id=body.project_id,
        run=lambda: ai_trailer_script.run_trailer_script(data),
    )
