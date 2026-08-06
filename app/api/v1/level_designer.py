"""AI Level Designer endpoint."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tool_runner import generation_to_response, run_tool
from app.database import get_db
from app.deps import get_current_user
from app.models.generation import Generation, ToolType
from app.models.user import User
from app.schemas import GenerationResponse, LevelDesignerRequest, LevelDesignerSaveRequest
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
            body.description,
            body.width,
            body.height,
            body.style,
            body.difficulty,
        ),
    )


@router.put("/{generation_id}", response_model=GenerationResponse)
async def save_level(
    generation_id: UUID,
    body: LevelDesignerSaveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save edited map JSON onto an existing level_designer generation (no quota)."""
    result = await db.execute(
        select(Generation).where(
            Generation.id == generation_id,
            Generation.user_id == user.id,
            Generation.tool == ToolType.LEVEL_DESIGNER,
        )
    )
    gen = result.scalar_one_or_none()
    if not gen:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Level not found")

    data = body.output_data or {}
    if not isinstance(data.get("tiles"), list):
        raise HTTPException(status_code=400, detail="output_data.tiles is required")

    gen.output_data = data
    if body.project_id is not None:
        gen.project_id = body.project_id
    if body.title:
        gen.title = body.title[:200]
    elif isinstance(data.get("name"), str) and data["name"].strip():
        gen.title = data["name"].strip()[:200]

    await db.flush()
    await db.refresh(gen)
    return generation_to_response(gen)
