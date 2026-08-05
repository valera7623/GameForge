"""AI Level Analyzer endpoints."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tool_runner import run_tool
from app.database import get_db
from app.deps import get_current_user
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import GenerationResponse, LevelAnalyzerCompareRequest, LevelAnalyzerRequest
from app.services import ai_level_analyzer

router = APIRouter(prefix="/level-analyzer", tags=["level-analyzer"])


@router.post("", response_model=GenerationResponse)
async def analyze_level(
    body: LevelAnalyzerRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    level_data = body.to_level_data()
    title = f"Level: {level_data.get('level_name') or 'Map'}"
    return await run_tool(
        request=request,
        db=db,
        user=user,
        tool=ToolType.LEVEL_ANALYZER,
        input_data=level_data,
        title=title[:200],
        project_id=body.project_id,
        run=lambda: ai_level_analyzer.run_level_analysis(level_data, lang=body.lang),
    )


@router.post("/compare")
async def compare_levels(
    body: LevelAnalyzerCompareRequest,
    user: User = Depends(get_current_user),
):
    """Compare two level payloads (no generation quota — pure analysis)."""
    _ = user
    return ai_level_analyzer.compare_levels(body.level_a, body.level_b, lang=body.lang)
