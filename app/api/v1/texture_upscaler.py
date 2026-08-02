"""AI Texture Upscaler endpoint."""

import base64

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.rate_limiter import rate_limit
from app.database import get_db
from app.deps import ensure_generation_quota, get_current_user
from app.models.generation import ToolType
from app.models.user import User
from app.schemas import GenerationResponse
from app.services import ai_texture_upscaler
from app.services.generation_tracker import complete_generation, create_generation, fail_generation

router = APIRouter(prefix="/texture-upscaler", tags=["texture-upscaler"])
settings = get_settings()


@router.post("", response_model=GenerationResponse)
async def upscale(
    request: Request,
    file: UploadFile = File(...),
    scale: int = Form(2),
    enhance: bool = Form(True),
    project_id: str | None = Form(None),
    async_mode: bool | None = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await rate_limit(request)
    await ensure_generation_quota(user, db)

    # Prefer Celery when Real-ESRGAN microservice is configured
    if async_mode is None:
        async_mode = bool(settings.REALESRGAN_URL)

    if file.content_type not in ("image/png", "image/jpeg", "image/jpg", "image/webp"):
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Only PNG/JPG/WEBP supported")

    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="File too large (max 20MB)")

    pid = None
    if project_id:
        from uuid import UUID

        pid = UUID(project_id)

    gen = await create_generation(
        db,
        user,
        ToolType.TEXTURE_UPSCALER,
        {"filename": file.filename, "scale": scale, "enhance": enhance},
        project_id=pid,
        title=f"Upscale {scale}x: {file.filename}",
    )

    if async_mode:
        from app.tasks.upscale_task import upscale_texture_task

        task = upscale_texture_task.delay(
            str(gen.id),
            base64.b64encode(data).decode(),
            file.filename or "texture.png",
            scale,
            enhance,
        )
        gen.celery_task_id = task.id
        await db.flush()
        return _to_response(gen)

    try:
        output = await ai_texture_upscaler.upscale_texture(
            data, file.filename or "texture.png", scale, enhance
        )
        gen = await complete_generation(db, gen, user, output, asset_urls=[output.get("url")])
    except Exception as exc:
        await fail_generation(db, gen, str(exc))
        await db.commit()
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(exc))

    return _to_response(gen)


def _to_response(gen) -> GenerationResponse:
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
