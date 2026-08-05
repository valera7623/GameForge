"""AI Review Analyzer endpoint."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tool_runner import run_tool
from app.database import get_db
from app.deps import get_current_user
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import GenerationResponse, ReviewAnalyzerRequest
from app.services import ai_review_analyzer

router = APIRouter(prefix="/review-analyzer", tags=["review-analyzer"])


@router.post("", response_model=GenerationResponse)
async def analyze_reviews(
    body: ReviewAnalyzerRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = body.to_payload()
    title = f"Reviews: {data.get('game_name') or 'Game'}"
    return await run_tool(
        request=request,
        db=db,
        user=user,
        tool=ToolType.REVIEW_ANALYZER,
        input_data=data,
        title=title[:200],
        project_id=body.project_id,
        run=lambda: ai_review_analyzer.run_review_analysis(data, lang=body.lang),
    )
