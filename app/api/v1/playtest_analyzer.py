"""AI Playtest Analyzer endpoint."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tool_runner import run_tool
from app.database import get_db
from app.deps import get_current_user
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import GenerationResponse, PlaytestAnalyzerRequest
from app.services import ai_playtest_analyzer

router = APIRouter(prefix="/playtest-analyzer", tags=["playtest-analyzer"])


@router.post("", response_model=GenerationResponse)
async def analyze_playtest(
    body: PlaytestAnalyzerRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = body.to_playtest_data()
    title = f"Playtest: {data.get('game_name') or 'Game'}"
    return await run_tool(
        request=request,
        db=db,
        user=user,
        tool=ToolType.PLAYTEST_ANALYZER,
        input_data=data,
        title=title[:200],
        project_id=body.project_id,
        run=lambda: ai_playtest_analyzer.run_playtest_analysis(data, lang=body.lang),
    )
