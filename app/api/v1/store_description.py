"""AI Store Description endpoint."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tool_runner import run_tool
from app.database import get_db
from app.deps import get_current_user
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import GenerationResponse, StoreDescriptionRequest
from app.services import ai_store_description

router = APIRouter(prefix="/store-description", tags=["store-description"])


@router.post("", response_model=GenerationResponse)
async def generate_store_description(
    body: StoreDescriptionRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = body.to_game_data()
    title = f"Store: {payload.get('game_name') or 'Game'} ({payload.get('target_platform')})"
    return await run_tool(
        request=request,
        db=db,
        user=user,
        tool=ToolType.STORE_DESCRIPTION,
        input_data=payload,
        title=title[:200],
        project_id=body.project_id,
        run=lambda: ai_store_description.run_store_description(payload),
    )
