"""AI Level Designer endpoint."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limiter import rate_limit
from app.database import get_db
from app.deps import ensure_generation_quota, get_current_user
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import GenerationResponse, LevelDesignerRequest
from app.services import ai_level_designer
from app.services.generation_tracker import complete_generation, create_generation, fail_generation

router = APIRouter(prefix="/level-designer", tags=["level-designer"])


@router.post("", response_model=GenerationResponse)
async def generate_level(
    body: LevelDesignerRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await rate_limit(request)
    await ensure_generation_quota(user, db)

    gen = await create_generation(
        db,
        user,
        ToolType.LEVEL_DESIGNER,
        body.model_dump(mode="json"),
        project_id=body.project_id,
        title=body.description[:80],
    )
    try:
        output = await ai_level_designer.generate_level(
            body.description, body.width, body.height, body.style
        )
        gen = await complete_generation(db, gen, user, output)
    except Exception as exc:
        await fail_generation(db, gen, str(exc))
        await db.commit()
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(exc))

    return GenerationResponse(
        id=gen.id,
        tool=gen.tool.value,
        status=gen.status.value,
        title=gen.title,
        input_data=gen.input_data,
        output_data=gen.output_data,
        asset_urls=gen.asset_urls,
        error_message=gen.error_message,
        xp_awarded=gen.xp_awarded,
        project_id=gen.project_id,
        created_at=gen.created_at,
        completed_at=gen.completed_at,
    )
