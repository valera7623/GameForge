"""AI Game Balancer endpoint."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tool_runner import run_tool
from app.database import get_db
from app.deps import get_current_user
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import GameBalancerRequest, GenerationResponse
from app.services import ai_game_balancer

router = APIRouter(prefix="/game-balancer", tags=["game-balancer"])


@router.post("", response_model=GenerationResponse)
async def analyze_balance(
    body: GameBalancerRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    game_data = body.to_game_data()
    title = f"Balance: {game_data.get('game_name') or 'Game'}"
    return await run_tool(
        request=request,
        db=db,
        user=user,
        tool=ToolType.GAME_BALANCER,
        input_data=game_data,
        title=title[:200],
        project_id=body.project_id,
        run=lambda: ai_game_balancer.run_balance_analysis(game_data),
    )
